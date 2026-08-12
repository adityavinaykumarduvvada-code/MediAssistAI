"""
Medical Knowledge Graph
------------------------
Builds a lightweight entity/relationship graph connecting the Digital
Twin's extracted entities (lab values, medicines, imaging findings) to
the reference material that grounds them (Blood/Imaging/Drug RAG).

This is a simplified stand-in for a full medical knowledge graph (e.g.
a persisted Neo4j graph over UMLS/SNOMED-CT) — it's built fresh per
request as plain node/edge lists rather than a queryable graph
database. It's structured so a real graph DB could be swapped in later
without changing the Clinical Reasoning Agent that consumes it: this
function is the only thing that would need to change.

No LLM calls happen here — retrieval + graph assembly are deterministic,
so this step can't fail on an API/network issue.
"""
from models.schemas import DigitalTwin, KnowledgeGraphContext, RetrievedChunk
from agents.blood_agent import ground_blood_findings
from agents.drug_agent import ground_drug_findings
from agents.imaging_agent import ground_imaging_findings


def build_knowledge_graph(twin: DigitalTwin, blood_results, drug_results, imaging_results) -> KnowledgeGraphContext:
    nodes, edges = [], []

    # Entity nodes straight from the Digital Twin
    for lv in twin.lab_values:
        nodes.append({"id": f"lab:{lv.name}", "type": "lab", "label": f"{lv.name} = {lv.value} {lv.unit or ''}".strip()})
    for m in twin.medicines:
        nodes.append({"id": f"drug:{m}", "type": "drug", "label": m})
    for f in twin.imaging_findings:
        nodes.append({"id": f"finding:{f}", "type": "imaging_finding", "label": f})

    # Retrieve grounding chunks per domain (best-effort — a retrieval
    # failure in one domain shouldn't take down the whole graph).
    reference_chunks: list[RetrievedChunk] = []
    domain_calls = [
        ("blood", ground_blood_findings, blood_results),
        ("drug", ground_drug_findings, drug_results),
        ("imaging", ground_imaging_findings, imaging_results),
    ]
    for domain, fn, results in domain_calls:
        try:
            chunks = fn(results) if results else []
        except Exception:
            chunks = []
        for c in chunks:
            reference_chunks.append(RetrievedChunk(**c))
            ref_id = f"ref:{domain}:{c['source']}"
            if not any(n["id"] == ref_id for n in nodes):
                nodes.append({"id": ref_id, "type": "reference", "label": c["source"]})
            # Connect every entity node in this domain to the reference.
            entity_prefix = {"blood": "lab:", "drug": "drug:", "imaging": "finding:"}[domain]
            for n in nodes:
                if n["id"].startswith(entity_prefix):
                    edges.append({"source": n["id"], "target": ref_id, "relation": "grounded_by"})

    return KnowledgeGraphContext(nodes=nodes, edges=edges, reference_chunks=reference_chunks)
