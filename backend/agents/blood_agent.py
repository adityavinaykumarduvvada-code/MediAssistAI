"""
Blood Agent
-----------
Extracts text from blood/lab reports — PDF via PyMuPDF, or a
photographed/screenshotted report via vision OCR — structures it into
lab values + key findings via the LLM, then grounds each extracted
value against the Blood RAG collection (CBC reference ranges, anemia
patterns, etc.) so downstream reasoning has real citations.
"""
import json
import traceback
from pathlib import Path
import fitz  # PyMuPDF

from models.schemas import UploadedFileInfo, PDFAgentResult, ExtractedLabValue
from core.llm_client import complete_text, ocr_document_image
from rag.retriever import retrieve_for_topics

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

STRUCTURE_SYSTEM = """You are a meticulous medical document parser
specialized in blood/lab reports. You extract structured data from
OCR'd report text and respond with STRICT JSON ONLY — no markdown
fences, no commentary. If a field is not present, use an empty list.
Never invent lab values that are not in the text."""

STRUCTURE_PROMPT_TEMPLATE = """Extract information from this blood/lab report text.

Return JSON matching exactly this shape:
{{
  "lab_values": [{{"name": str, "value": str, "unit": str|null, "reference_range": str|null, "flag": "low"|"normal"|"high"|"unknown"}}],
  "key_findings": [str, ...]
}}

Document text:
---
{text}
---
JSON:"""


def _extract_pdf_text(path: str) -> str:
    doc = fitz.open(path)
    text_parts = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(text_parts).strip()


def _get_document_text(file: UploadedFileInfo) -> str:
    """Text extraction that works whether the report arrived as a PDF
    (fast, local PyMuPDF) or as a photographed/screenshotted image
    (vision OCR)."""
    ext = Path(file.stored_path).suffix.lower()
    if ext in IMAGE_EXTS:
        return ocr_document_image(file.stored_path)
    return _extract_pdf_text(file.stored_path)


def _safe_json_parse(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start:end + 1])
        raise


def run_blood_agent(file: UploadedFileInfo) -> PDFAgentResult:
    try:
        text = _get_document_text(file)
    except Exception as e:
        traceback.print_exc()
        return PDFAgentResult(
            file_id=file.file_id, document_type=file.kind,
            raw_text_excerpt="", key_findings=[f"Could not read this file: {e}"],
        )
    excerpt = text[:6000]

    if not excerpt.strip():
        return PDFAgentResult(
            file_id=file.file_id, document_type=file.kind,
            raw_text_excerpt="", key_findings=["Could not extract readable text from this file."],
        )

    try:
        raw = complete_text(system=STRUCTURE_SYSTEM, prompt=STRUCTURE_PROMPT_TEMPLATE.format(text=excerpt), max_tokens=1500)
        parsed = _safe_json_parse(raw)
    except Exception as e:
        traceback.print_exc()
        parsed = {"lab_values": [], "key_findings": [f"Automatic structuring failed for this file: {e}"]}

    lab_values = [ExtractedLabValue(**lv) for lv in parsed.get("lab_values", [])]

    return PDFAgentResult(
        file_id=file.file_id,
        document_type=file.kind,
        raw_text_excerpt=excerpt[:1500],
        lab_values=lab_values,
        medicines=[],
        key_findings=parsed.get("key_findings", []),
    )


def ground_blood_findings(results: list[PDFAgentResult]) -> list[dict]:
    """Retrieve Blood RAG context for every extracted lab value/finding —
    used by the Knowledge Graph builder downstream."""
    topics = []
    for r in results:
        topics += [lv.name for lv in r.lab_values]
        topics += r.key_findings
    return retrieve_for_topics("blood", topics, top_k_each=2) if topics else []
