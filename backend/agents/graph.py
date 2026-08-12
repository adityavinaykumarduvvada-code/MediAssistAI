"""
LangGraph orchestration.

    User / Doctor
         |
         v
  Multimodal Input (PDF / image upload)
         |
         v
  Agentic Orchestrator          (classify + route each file)
         |
   ------+-------+-------
   |             |       |
   v             v       v
Blood Agent  Imaging   Drug Agent      (parallel, each grounded in its
   |         Agent        |             own RAG collection)
   ------+-------+-------
              |
              v
     Patient Digital Twin        (deterministic merge, no LLM call)
              |
              v
     Medical Knowledge Graph     (entity/reference graph + retrieval,
              |                   no LLM call)
              v
     Clinical Reasoning Agent    (LLM: possible conditions + evidence)
              |
              v
     Safety / Verification Agent (rule-based guardrails, no LLM call)
              |
              v
     Explainable Response + Evidence  ->  Final Report

IMPORTANT LangGraph pattern: when multiple nodes (blood_agent,
imaging_agent, drug_agent) run in the same parallel step, each node
must return ONLY the state keys it actually updates — never the whole
state object — or LangGraph raises InvalidUpdateError because every
parallel branch would be writing conflicting values to every shared key
in the same step. Keys that legitimately receive writes from multiple
branches (the trace log) use an `Annotated[..., operator.add]` reducer
so the writes merge instead of colliding.

Every node is also wrapped defensively: a failure in one branch is
logged to the trace and degrades gracefully rather than raising an
uncaught exception that would 500 the whole request.
"""
import operator
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END

from models.schemas import (
    UploadedFileInfo, PDFAgentResult, ImageAgentResult, CaseSummary,
    PlannerOutput, DigitalTwin, KnowledgeGraphContext,
)
from agents.orchestrator import plan
from agents.blood_agent import run_blood_agent
from agents.drug_agent import run_drug_agent
from agents.imaging_agent import run_imaging_agent
from agents.digital_twin import build_digital_twin
from agents.knowledge_graph import build_knowledge_graph
from agents.clinical_reasoning_agent import run_clinical_reasoning_agent
from agents.safety_agent import run_safety_agent


class GraphState(TypedDict):
    session_id: str
    uploaded: list[UploadedFileInfo]
    plan_notes: str
    planner_output: PlannerOutput | None
    blood_results: list[PDFAgentResult]
    drug_results: list[PDFAgentResult]
    image_results: list[ImageAgentResult]
    twin: DigitalTwin | None
    knowledge_graph: KnowledgeGraphContext | None
    summary: CaseSummary | None
    # Multiple nodes append to this in the same parallel step, so it
    # needs a reducer (operator.add concatenates lists) rather than the
    # default last-value-wins channel.
    trace: Annotated[list[dict], operator.add]


def _trace_entry(agent: str, status: str, message: str) -> dict:
    return {"agent": agent, "status": status, "message": message}


def orchestrator_node(state: GraphState) -> dict:
    try:
        result = plan(state["uploaded"])
        return {
            "plan_notes": result.plan_notes,
            "planner_output": result,
            "trace": [
                _trace_entry("Agentic Orchestrator", "started", "Classifying uploaded files..."),
                _trace_entry("Agentic Orchestrator", "completed", result.plan_notes),
            ],
        }
    except Exception as e:
        # Fall back to routing nothing anywhere rather than crashing —
        # downstream nodes handle empty file lists gracefully.
        empty_plan = PlannerOutput(files=state["uploaded"], blood_files=[], image_files=[], drug_files=[],
                                    plan_notes=f"Orchestrator failed: {e}")
        return {
            "plan_notes": empty_plan.plan_notes,
            "planner_output": empty_plan,
            "trace": [_trace_entry("Agentic Orchestrator", "error", str(e))],
        }


def blood_node(state: GraphState) -> dict:
    planner_output = state["planner_output"]
    files = planner_output.blood_files if planner_output else []
    trace = [_trace_entry("Blood Agent", "started", f"Reading {len(files)} blood/lab report(s)...")]

    results = []
    for f in files:
        try:
            results.append(run_blood_agent(f))
        except Exception as e:
            trace.append(_trace_entry("Blood Agent", "error", f"Failed on {f.original_name}: {e}"))

    trace.append(_trace_entry("Blood Agent", "completed", f"Structured {len(results)} report(s)."))
    return {"blood_results": results, "trace": trace}


def drug_node(state: GraphState) -> dict:
    planner_output = state["planner_output"]
    files = planner_output.drug_files if planner_output else []
    trace = [_trace_entry("Drug Agent", "started", f"Reading {len(files)} prescription(s)...")]

    results = []
    for f in files:
        try:
            results.append(run_drug_agent(f))
        except Exception as e:
            trace.append(_trace_entry("Drug Agent", "error", f"Failed on {f.original_name}: {e}"))

    trace.append(_trace_entry("Drug Agent", "completed", f"Structured {len(results)} prescription(s)."))
    return {"drug_results": results, "trace": trace}


def imaging_node(state: GraphState) -> dict:
    planner_output = state["planner_output"]
    files = planner_output.image_files if planner_output else []
    trace = [_trace_entry("Imaging Agent", "started", f"Analyzing {len(files)} scan image(s)...")]

    results = []
    for f in files:
        try:
            results.append(run_imaging_agent(f))
        except Exception as e:
            trace.append(_trace_entry("Imaging Agent", "error", f"Failed on {f.original_name}: {e}"))

    trace.append(_trace_entry("Imaging Agent", "completed", f"Analyzed {len(results)} image(s)."))
    return {"image_results": results, "trace": trace}


def digital_twin_node(state: GraphState) -> dict:
    try:
        twin = build_digital_twin(state["session_id"], state["blood_results"], state["drug_results"], state["image_results"])
        return {"twin": twin, "trace": [_trace_entry("Patient Digital Twin", "completed", "Merged all extracted data into one patient snapshot.")]}
    except Exception as e:
        empty_twin = DigitalTwin(session_id=state["session_id"])
        return {"twin": empty_twin, "trace": [_trace_entry("Patient Digital Twin", "error", str(e))]}


def knowledge_graph_node(state: GraphState) -> dict:
    try:
        kg = build_knowledge_graph(state["twin"], state["blood_results"], state["drug_results"], state["image_results"])
        msg = f"Linked {len(kg.nodes)} entities to {len(kg.reference_chunks)} reference passages."
        return {"knowledge_graph": kg, "trace": [_trace_entry("Medical Knowledge Graph", "completed", msg)]}
    except Exception as e:
        empty_kg = KnowledgeGraphContext()
        return {"knowledge_graph": empty_kg, "trace": [_trace_entry("Medical Knowledge Graph", "error", str(e))]}


def clinical_reasoning_node(state: GraphState) -> dict:
    trace = [_trace_entry("Clinical Reasoning Agent", "started", "Reasoning over the digital twin + knowledge graph...")]
    try:
        summary = run_clinical_reasoning_agent(state["session_id"], state["twin"], state["knowledge_graph"])
        trace.append(_trace_entry("Clinical Reasoning Agent", "completed", "Draft explanation ready."))
    except Exception as e:
        summary = CaseSummary(
            session_id=state["session_id"], possible_conditions=[], evidence=[],
            medicine_explanations=[], follow_up_questions=[], references=[],
            plain_language_summary="We hit an error reasoning over your case. Please review the extracted data and consult your doctor.",
        )
        trace.append(_trace_entry("Clinical Reasoning Agent", "error", str(e)))
    return {"summary": summary, "trace": trace}


def safety_node(state: GraphState) -> dict:
    try:
        verified = run_safety_agent(state["summary"], state["knowledge_graph"])
        trace = [_trace_entry("Safety / Verification Agent", "completed", "Report verified — hedged language, checked references.")]
    except Exception as e:
        verified = state["summary"]
        trace = [_trace_entry("Safety / Verification Agent", "error", str(e))]
    return {"summary": verified, "trace": trace}


def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("blood_agent", blood_node)
    graph.add_node("drug_agent", drug_node)
    graph.add_node("imaging_agent", imaging_node)
    graph.add_node("digital_twin_builder", digital_twin_node)
    graph.add_node("knowledge_graph_builder", knowledge_graph_node)
    graph.add_node("clinical_reasoning_agent", clinical_reasoning_node)
    graph.add_node("safety_agent", safety_node)

    graph.set_entry_point("orchestrator")
    # fan-out: three domain agents run off the orchestrator
    graph.add_edge("orchestrator", "blood_agent")
    graph.add_edge("orchestrator", "drug_agent")
    graph.add_edge("orchestrator", "imaging_agent")
    # fan-in: digital twin waits for all three
    graph.add_edge("blood_agent", "digital_twin_builder")
    graph.add_edge("drug_agent", "digital_twin_builder")
    graph.add_edge("imaging_agent", "digital_twin_builder")
    # linear chain from here
    graph.add_edge("digital_twin_builder", "knowledge_graph_builder")
    graph.add_edge("knowledge_graph_builder", "clinical_reasoning_agent")
    graph.add_edge("clinical_reasoning_agent", "safety_agent")
    graph.add_edge("safety_agent", END)

    return graph.compile()


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_pipeline(session_id: str, uploaded: list[UploadedFileInfo]) -> GraphState:
    initial: GraphState = {
        "session_id": session_id,
        "uploaded": uploaded,
        "plan_notes": "",
        "planner_output": None,
        "blood_results": [],
        "drug_results": [],
        "image_results": [],
        "twin": None,
        "knowledge_graph": None,
        "summary": None,
        "trace": [],
    }
    graph = get_graph()
    final_state = graph.invoke(initial)
    return final_state
