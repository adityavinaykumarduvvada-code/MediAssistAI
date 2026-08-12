from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime


FileKind = Literal["blood_report", "xray", "mri_ct", "prescription", "unknown"]


class UploadedFileInfo(BaseModel):
    file_id: str
    original_name: str
    stored_path: str
    kind: FileKind


class PlannerOutput(BaseModel):
    """Output of the Agentic Orchestrator: every uploaded file routed to
    the domain agent responsible for it."""
    files: list[UploadedFileInfo]
    blood_files: list[UploadedFileInfo]      # -> Blood Agent
    image_files: list[UploadedFileInfo]      # -> Imaging Agent
    drug_files: list[UploadedFileInfo]       # -> Drug Agent
    plan_notes: str


class ExtractedLabValue(BaseModel):
    name: str
    value: str
    unit: str | None = None
    reference_range: str | None = None
    flag: Literal["low", "normal", "high", "unknown"] = "unknown"


class PDFAgentResult(BaseModel):
    """Shared result shape for both the Blood Agent and the Drug Agent —
    they extract different fields (lab values vs. medicines) from the
    same kind of source (a text-bearing PDF), so one schema covers both."""
    file_id: str
    document_type: FileKind
    raw_text_excerpt: str
    lab_values: list[ExtractedLabValue] = Field(default_factory=list)
    medicines: list[str] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)


class ImageAgentResult(BaseModel):
    file_id: str
    modality: str
    observations: list[str]
    possible_findings: list[str]
    confidence_note: str


class RetrievedChunk(BaseModel):
    domain: str
    source: str
    text: str
    score: float


class DigitalTwin(BaseModel):
    """A structured, in-session snapshot of everything extracted about
    the patient so far — the single object every downstream reasoning
    step reads from, instead of re-deriving it from raw agent output."""
    session_id: str
    lab_values: list[ExtractedLabValue] = Field(default_factory=list)
    medicines: list[str] = Field(default_factory=list)
    imaging_modalities: list[str] = Field(default_factory=list)
    imaging_findings: list[str] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)


class KnowledgeGraphContext(BaseModel):
    """Lightweight relational context linking extracted entities (labs,
    medicines, imaging findings) to the reference material that grounds
    them. This is a simplified stand-in for a full medical knowledge
    graph (e.g. a Neo4j UMLS/SNOMED graph) — entity/edge lists rather
    than a persisted graph database — but it is built and consumed the
    same way a real graph layer would be, so it's a drop-in point to
    swap in a real graph DB later without touching the agents around it."""
    nodes: list[dict] = Field(default_factory=list)       # {id, type, label}
    edges: list[dict] = Field(default_factory=list)       # {source, target, relation}
    reference_chunks: list[RetrievedChunk] = Field(default_factory=list)


class CaseSummary(BaseModel):
    """Final, patient-facing explainable response — the output of the
    Clinical Reasoning Agent after the Safety/Verification Agent has
    reviewed it."""
    session_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    possible_conditions: list[str]
    evidence: list[str]
    medicine_explanations: list[str]
    follow_up_questions: list[str]
    references: list[str]
    plain_language_summary: str
    safety_notes: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "MediAssist AI is an educational tool, not a medical diagnosis. "
        "Always confirm findings with a licensed physician."
    )


class AgentTrace(BaseModel):
    agent: str
    status: Literal["started", "completed", "error"]
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
