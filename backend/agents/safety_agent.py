"""
Safety / Verification Agent
------------------------------
The last gate before anything reaches the patient. Deliberately
rule-based rather than another LLM call — a safety layer that could
itself fail on an API error would defeat the point of having one. It:

  1. Strips/softens any language that reads like a confirmed diagnosis
     rather than a hedged possibility.
  2. Filters "references" down to sources that were actually retrieved
     by the Knowledge Graph — never lets the model cite something it
     didn't actually see.
  3. Guarantees there's always at least one follow-up question and the
     disclaimer is present.
  4. Records what it changed in `safety_notes`, for transparency.
"""
import re

from models.schemas import CaseSummary, KnowledgeGraphContext

# Phrases that overstate certainty — a patient-facing tool should never
# use these even if the model slips into them.
OVERCLAIM_PATTERNS = [
    (re.compile(r"\byou (have|are diagnosed with|definitely have)\b", re.I), "you may want to discuss whether you have"),
    (re.compile(r"\bconfirmed diagnosis\b", re.I), "a possibility to discuss with your doctor"),
    (re.compile(r"\bthis (is|means you have)\b", re.I), "this could suggest"),
    (re.compile(r"\bdefinitely\b", re.I), "possibly"),
    (re.compile(r"\bcertainly\b", re.I), "possibly"),
]

DEFAULT_FOLLOW_UP = "Can you walk me through what these results mean for me specifically?"


def _soften(text: str) -> tuple[str, bool]:
    changed = False
    for pattern, replacement in OVERCLAIM_PATTERNS:
        new_text, n = pattern.subn(replacement, text)
        if n > 0:
            changed = True
            text = new_text
    return text, changed


def run_safety_agent(summary: CaseSummary, kg: KnowledgeGraphContext) -> CaseSummary:
    notes: list[str] = []

    # 1. Soften overclaiming language wherever it appears.
    softened_conditions, edits = [], False
    for c in summary.possible_conditions:
        new_c, changed = _soften(c)
        softened_conditions.append(new_c)
        edits = edits or changed
    summary.possible_conditions = softened_conditions

    new_summary_text, summary_changed = _soften(summary.plain_language_summary)
    summary.plain_language_summary = new_summary_text
    edits = edits or summary_changed

    if edits:
        notes.append("Softened language that read as a confirmed diagnosis into a hedged possibility.")

    # 2. Only allow references that were actually retrieved.
    known_sources = {c.source for c in kg.reference_chunks}
    if known_sources:
        filtered = [r for r in summary.references if r in known_sources]
        if len(filtered) != len(summary.references):
            notes.append("Removed one or more cited references that weren't part of the retrieved evidence.")
        summary.references = filtered or list(known_sources)

    # 3. Guarantee at least one follow-up question.
    if not summary.follow_up_questions:
        summary.follow_up_questions = [DEFAULT_FOLLOW_UP]
        notes.append("Added a default follow-up question since none were generated.")

    # 4. Disclaimer always present (schema default already guarantees this,
    #    this is a defensive re-assert in case it was ever overwritten).
    if not summary.disclaimer:
        summary.disclaimer = (
            "MediAssist AI is an educational tool, not a medical diagnosis. "
            "Always confirm findings with a licensed physician."
        )
        notes.append("Restored the missing disclaimer.")

    summary.safety_notes = notes
    return summary
