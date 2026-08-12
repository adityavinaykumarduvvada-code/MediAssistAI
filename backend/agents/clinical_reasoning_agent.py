"""
Clinical Reasoning Agent
--------------------------
Reads the Patient Digital Twin + Medical Knowledge Graph context and
produces a draft explanation: possible conditions, supporting evidence,
medicine explanations, and follow-up questions. This draft is NOT the
final output — it still passes through the Safety/Verification Agent,
which is what actually enforces the non-diagnostic, hedged-language
rules before anything reaches the patient.
"""
import json
import traceback

from models.schemas import DigitalTwin, KnowledgeGraphContext, CaseSummary
from core.llm_client import complete_text

REASONING_SYSTEM = """You are the Clinical Reasoning Agent inside a
patient-education system. You translate structured clinical data into
warm, plain, non-alarming language a non-medical person can understand.
You NEVER assert a definitive diagnosis — you describe possibilities
and the evidence behind them, grounded ONLY in the data and reference
context provided. You always end by encouraging the patient to discuss
results with their doctor. Respond with STRICT JSON only, no markdown
fences."""

REASONING_PROMPT_TEMPLATE = """PATIENT DIGITAL TWIN (structured extraction from all uploaded documents):
{twin}

MEDICAL KNOWLEDGE GRAPH — reference material actually retrieved and linked to the twin's entities (cite these as references, do not invent others):
{kg_context}

Using ONLY the information above, produce JSON in exactly this shape:
{{
  "plain_language_summary": str,       // 3-5 sentences, warm and clear, no jargon
  "possible_conditions": [str, ...],   // hedged possibilities, not a diagnosis
  "evidence": [str, ...],              // which extracted values/observations support each possibility
  "medicine_explanations": [str, ...], // what each medicine is generally for, in plain language
  "follow_up_questions": [str, ...],   // specific, useful questions the patient should ask their doctor
  "references": [str, ...]             // names of the reference sources actually used, exactly as given above
}}

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


def _fallback_summary(session_id: str, twin: DigitalTwin, kg: KnowledgeGraphContext) -> CaseSummary:
    return CaseSummary(
        session_id=session_id,
        possible_conditions=[],
        evidence=[],
        medicine_explanations=[],
        follow_up_questions=["Can you help me interpret these results together?"],
        references=list({c.source for c in kg.reference_chunks}),
        plain_language_summary=(
            "We couldn't fully process this case automatically. Please review the "
            "extracted data below and consult your doctor for a full interpretation."
        ),
    )


def run_clinical_reasoning_agent(session_id: str, twin: DigitalTwin, kg: KnowledgeGraphContext) -> CaseSummary:
    kg_context_text = "\n\n".join(f"[{c.source}] {c.text}" for c in kg.reference_chunks) or "No specific reference matched."

    prompt = REASONING_PROMPT_TEMPLATE.format(
        twin=twin.model_dump_json(indent=2),
        kg_context=kg_context_text,
    )

    try:
        raw = complete_text(system=REASONING_SYSTEM, prompt=prompt, max_tokens=2000, temperature=0.3)
        parsed = _safe_json_parse(raw)
    except Exception:
        traceback.print_exc()
        return _fallback_summary(session_id, twin, kg)

    return CaseSummary(
        session_id=session_id,
        possible_conditions=parsed.get("possible_conditions", []),
        evidence=parsed.get("evidence", []),
        medicine_explanations=parsed.get("medicine_explanations", []),
        follow_up_questions=parsed.get("follow_up_questions", []),
        references=parsed.get("references", []) or list({c.source for c in kg.reference_chunks}),
        plain_language_summary=parsed.get("plain_language_summary", ""),
    )
