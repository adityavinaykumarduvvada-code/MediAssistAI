"""
Patient Digital Twin
---------------------
Deterministic merge step (no LLM call, so it can't fail on network/API
issues) that folds every domain agent's output into one structured
snapshot of the patient's case. Every downstream reasoning step reads
from this single object instead of re-deriving it from three separate
result lists.
"""
from models.schemas import PDFAgentResult, ImageAgentResult, DigitalTwin


def build_digital_twin(session_id: str, blood_results: list[PDFAgentResult],
                        drug_results: list[PDFAgentResult],
                        imaging_results: list[ImageAgentResult]) -> DigitalTwin:
    lab_values = [lv for r in blood_results for lv in r.lab_values]
    medicines = [m for r in drug_results for m in r.medicines]
    key_findings = [f for r in blood_results for f in r.key_findings]
    key_findings += [f for r in drug_results for f in r.key_findings]

    imaging_modalities = [r.modality for r in imaging_results if r.modality and r.modality.lower() != "unclear"]
    imaging_findings = [f for r in imaging_results for f in r.possible_findings]

    return DigitalTwin(
        session_id=session_id,
        lab_values=lab_values,
        medicines=medicines,
        imaging_modalities=imaging_modalities,
        imaging_findings=imaging_findings,
        key_findings=key_findings,
    )
