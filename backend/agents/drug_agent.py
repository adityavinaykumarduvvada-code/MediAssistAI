"""
Drug Agent
----------
Extracts medicines from prescriptions — PDF via PyMuPDF, or a
photographed/screenshotted prescription via vision OCR — then grounds
each medicine name against the Drug RAG collection so the Clinical
Reasoning Agent can explain them accurately.
"""
import json
import traceback
from pathlib import Path
import fitz  # PyMuPDF

from models.schemas import UploadedFileInfo, PDFAgentResult
from core.llm_client import complete_text, ocr_document_image
from rag.retriever import retrieve_for_topics

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

STRUCTURE_SYSTEM = """You are a meticulous medical document parser
specialized in prescriptions. You extract structured data from OCR'd
prescription text and respond with STRICT JSON ONLY — no markdown
fences, no commentary. Never invent medicines that are not in the text."""

STRUCTURE_PROMPT_TEMPLATE = """Extract information from this prescription text.

Return JSON matching exactly this shape:
{{
  "medicines": [str, ...],          // medicine names, dose/frequency included if present e.g. "Amoxicillin 500mg twice daily"
  "key_findings": [str, ...]        // any other clinically relevant notes (diagnosis mentioned, instructions, etc.)
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


def run_drug_agent(file: UploadedFileInfo) -> PDFAgentResult:
    try:
        text = _get_document_text(file)
    except Exception as e:
        traceback.print_exc()
        return PDFAgentResult(
            file_id=file.file_id, document_type=file.kind,
            raw_text_excerpt="", key_findings=[f"Could not read this prescription: {e}"],
        )
    excerpt = text[:6000]

    if not excerpt.strip():
        return PDFAgentResult(
            file_id=file.file_id, document_type=file.kind,
            raw_text_excerpt="", key_findings=["Could not extract readable text from this prescription."],
        )

    try:
        raw = complete_text(system=STRUCTURE_SYSTEM, prompt=STRUCTURE_PROMPT_TEMPLATE.format(text=excerpt), max_tokens=1000)
        parsed = _safe_json_parse(raw)
    except Exception as e:
        traceback.print_exc()
        parsed = {"medicines": [], "key_findings": [f"Automatic structuring failed for this prescription: {e}"]}

    return PDFAgentResult(
        file_id=file.file_id,
        document_type=file.kind,
        raw_text_excerpt=excerpt[:1500],
        lab_values=[],
        medicines=parsed.get("medicines", []),
        key_findings=parsed.get("key_findings", []),
    )


def ground_drug_findings(results: list[PDFAgentResult]) -> list[dict]:
    """Retrieve Drug RAG context for every extracted medicine — used by
    the Knowledge Graph builder downstream."""
    topics = []
    for r in results:
        topics += r.medicines
    return retrieve_for_topics("drug", topics, top_k_each=2) if topics else []
