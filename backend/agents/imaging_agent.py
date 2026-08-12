"""
Imaging Agent
-------------
Sends X-ray / MRI / CT images to a vision-capable LLM with a carefully
scoped prompt: describe visual observations in plain language and list
*possible* (never definitive) findings, always flagging that this is
not a radiologist's read. Findings are then grounded against the
Imaging RAG collection. In production, swap/augment with a dedicated
medical imaging model (e.g. a fine-tuned Florence-2 / Qwen2.5-VL) for
higher clinical fidelity — the interface below (`run_imaging_agent`) is
model-agnostic.
"""
import json
import traceback

from models.schemas import UploadedFileInfo, ImageAgentResult
from core.llm_client import analyze_image
from rag.retriever import retrieve_for_topics

VISION_SYSTEM = """You are a cautious radiology-education assistant helping
a patient understand a scan image in plain language. You are NOT a
diagnostic device and must never state a confirmed diagnosis. Describe
only what is visually plausible, use hedged language ("may suggest",
"could be consistent with"), and always recommend confirmation by a
licensed radiologist/physician. Respond with STRICT JSON only."""

VISION_PROMPT = """Look at this medical scan image (likely an X-ray, MRI, or CT slice).

Return JSON exactly in this shape:
{
  "modality": str,                // e.g. "Chest X-ray", "Brain MRI", "unclear"
  "observations": [str, ...],     // plain visual observations (opacity, alignment, symmetry, etc.)
  "possible_findings": [str, ...],// hedged, non-diagnostic possibilities a doctor might investigate
  "confidence_note": str          // 1-2 sentences on the limits of this AI read
}

JSON:"""


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


def run_imaging_agent(file: UploadedFileInfo) -> ImageAgentResult:
    try:
        raw = analyze_image(file.stored_path, system=VISION_SYSTEM, prompt=VISION_PROMPT)
        parsed = _safe_json_parse(raw)
    except Exception as e:
        traceback.print_exc()
        parsed = {
            "modality": "unclear",
            "observations": [],
            "possible_findings": [],
            "confidence_note": f"Automatic image analysis failed ({e}); please retry or consult a radiologist.",
        }

    return ImageAgentResult(
        file_id=file.file_id,
        modality=parsed.get("modality", "unclear"),
        observations=parsed.get("observations", []),
        possible_findings=parsed.get("possible_findings", []),
        confidence_note=parsed.get("confidence_note", ""),
    )


def ground_imaging_findings(results: list[ImageAgentResult]) -> list[dict]:
    """Retrieve Imaging RAG context for every possible finding — used by
    the Knowledge Graph builder downstream."""
    topics = []
    for r in results:
        topics += r.possible_findings
        if r.modality and r.modality.lower() != "unclear":
            topics.append(r.modality)
    return retrieve_for_topics("imaging", topics, top_k_each=2) if topics else []
