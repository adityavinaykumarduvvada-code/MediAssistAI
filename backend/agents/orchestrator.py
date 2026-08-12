"""
Agentic Orchestrator (formerly "Planner Agent")
------------------------------------------------
Looks at every file the patient uploaded, classifies it, and routes it
to exactly one domain agent:
    blood_report (PDF or photographed report)   -> Blood Agent
    prescription (PDF or photographed report)   -> Drug Agent
    xray / mri_ct (actual scan image)           -> Imaging Agent

Classification order:
  1. Filename keywords (fast, free, no API call).
  2. For images with no keyword match: content-based vision
     classification — a screenshot or camera photo (e.g.
     "IMG_2041.png") has no useful filename, so we ask the vision model
     whether it's actually a document (report/prescription) or a real
     scan image, and route accordingly. This is what prevents a
     photographed blood report from being sent to the Imaging Agent's
     X-ray-reading prompt.
  3. For PDFs with no keyword match: a lightweight text-only LLM guess
     (unchanged from before).
"""
from pathlib import Path

from models.schemas import UploadedFileInfo, PlannerOutput, FileKind
from core.llm_client import complete_text, classify_image_content

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".dcm"}
PDF_EXTS = {".pdf"}

KEYWORDS = {
    "blood_report": ["blood", "cbc", "hemoglobin", "hematology", "lab report", "pathology"],
    "xray": ["xray", "x-ray", "chest", "cxr"],
    "mri_ct": ["mri", "ct scan", "ct-scan", "scan", "radiology"],
    "prescription": ["prescription", "rx", "medicine", "doctor note"],
}


def _classify_by_name(name: str) -> FileKind | None:
    lower = name.lower()
    for kind, words in KEYWORDS.items():
        if any(w in lower for w in words):
            return kind  # type: ignore
    return None  # no keyword match — caller decides the fallback strategy


def _classify_pdf_with_llm(name: str) -> FileKind:
    prompt = (
        "Classify this medical file name into exactly one label: "
        "blood_report, xray, mri_ct, prescription, or unknown.\n"
        f"Filename: {name}\nRespond with only the label."
    )
    try:
        label = complete_text(
            system="You classify medical document filenames. Respond with a single lowercase label only.",
            prompt=prompt,
            max_tokens=10,
        ).strip().lower()
    except Exception:
        return "unknown"
    return label if label in KEYWORDS or label == "unknown" else "unknown"


def _classify_image_with_vision(path: str) -> FileKind:
    """Look at the actual image content to tell a photographed document
    (report/prescription) apart from a real scan image."""
    content_kind = classify_image_content(path)
    return {
        "blood_report": "blood_report",
        "prescription": "prescription",
        "scan": "xray",
    }.get(content_kind, "xray")  # unknown content defaults to "xray" (old safe default)


def plan(uploaded: list[UploadedFileInfo]) -> PlannerOutput:
    for f in uploaded:
        ext = Path(f.stored_path).suffix.lower()
        kind = _classify_by_name(f.original_name)

        if kind is None:
            if ext in IMAGE_EXTS:
                kind = _classify_image_with_vision(f.stored_path)
            elif ext in PDF_EXTS:
                kind = _classify_pdf_with_llm(f.original_name)
                if kind == "unknown":
                    kind = "blood_report"  # bare PDF default, refined later by Blood Agent
            else:
                kind = "unknown"

        f.kind = kind

    # Route by kind *and* file type:
    #   - blood_report as PDF or photo -> Blood Agent (text/OCR extraction)
    #   - mri_ct as a PDF (a written report) -> Blood Agent (text extraction)
    #   - mri_ct or xray as an image (an actual scan) -> Imaging Agent
    #   - prescription as PDF or photo -> Drug Agent
    is_pdf = lambda f: Path(f.stored_path).suffix.lower() in PDF_EXTS
    is_image = lambda f: Path(f.stored_path).suffix.lower() in IMAGE_EXTS

    blood_files = [
        f for f in uploaded
        if f.kind == "blood_report" or (f.kind == "mri_ct" and is_pdf(f))
    ]
    drug_files = [f for f in uploaded if f.kind == "prescription"]
    image_files = [
        f for f in uploaded
        if f.kind in ("xray", "mri_ct") and is_image(f)
    ]

    notes = (
        f"Detected {len(blood_files)} blood/lab report(s) for the Blood Agent, "
        f"{len(drug_files)} prescription(s) for the Drug Agent, and "
        f"{len(image_files)} scan image(s) for the Imaging Agent."
    )

    return PlannerOutput(
        files=uploaded,
        blood_files=blood_files,
        image_files=image_files,
        drug_files=drug_files,
        plan_notes=notes,
    )
