
import traceback
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import get_settings
from models.schemas import UploadedFileInfo
from database.db import init_db, save_session_files, get_session_files, save_report, get_report
from agents.graph import run_pipeline

settings = get_settings()

app = FastAPI(title=settings.APP_NAME, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(settings.SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)
init_db()


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Any uncaught error anywhere in the app returns clean JSON instead
    of a bare 500 with no message — and always logs the full traceback
    server-side so it's debuggable from the terminal."""
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"{type(exc).__name__}: {exc}"},
    )


@app.on_event("startup")
def seed_knowledge_base_if_empty():
    """Auto-ingest the bundled medical knowledge base (Blood/Imaging/Drug
    RAG collections) on first boot so a fresh deployment works out of the
    box without a manual ingest step."""
    try:
        from rag.vector_store import DOMAIN_COLLECTIONS, collection_count
        from rag.ingest import ingest_knowledge_base
        if any(collection_count(d) == 0 for d in DOMAIN_COLLECTIONS):
            ingest_knowledge_base()
    except Exception as e:
        print(f"[startup] Knowledge base seeding skipped/failed: {e}")


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}


@app.post("/api/sessions/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(400, "No files uploaded.")

    session_id = str(uuid.uuid4())
    session_dir = Path(settings.UPLOAD_DIR) / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    stored: list[UploadedFileInfo] = []
    for f in files:
        size = 0
        file_id = str(uuid.uuid4())
        dest = session_dir / f"{file_id}_{f.filename}"
        with open(dest, "wb") as out:
            while chunk := await f.read(1024 * 1024):
                size += len(chunk)
                if size > settings.MAX_UPLOAD_MB * 1024 * 1024:
                    out.close()
                    dest.unlink(missing_ok=True)
                    raise HTTPException(413, f"{f.filename} exceeds {settings.MAX_UPLOAD_MB}MB limit.")
                out.write(chunk)

        stored.append(UploadedFileInfo(
            file_id=file_id,
            original_name=f.filename,
            stored_path=str(dest),
            kind="unknown",
        ))

    save_session_files(session_id, [f.model_dump(mode="json") for f in stored])

    return {
        "session_id": session_id,
        "files": [f.model_dump(mode="json") for f in stored],
    }


@app.post("/api/sessions/{session_id}/analyze")
def analyze_session(session_id: str):
    files_data = get_session_files(session_id)
    if not files_data:
        raise HTTPException(404, "Session not found. Upload files first.")

    uploaded = [UploadedFileInfo(**f) for f in files_data]

    final_state = run_pipeline(session_id, uploaded)
    summary = final_state["summary"]

    # Merge Blood Agent + Drug Agent output into one "pdf_results" list —
    # both share the same result shape (PDFAgentResult) and the frontend
    # renders them together (lab values table + medicine list).
    pdf_results = final_state["blood_results"] + final_state["drug_results"]

    response = {
        "summary": summary.model_dump(mode="json"),
        "pdf_results": [r.model_dump(mode="json") for r in pdf_results],
        "image_results": [r.model_dump(mode="json") for r in final_state["image_results"]],
        "trace": final_state["trace"],
        "plan_notes": final_state["plan_notes"],
        "knowledge_graph": final_state["knowledge_graph"].model_dump(mode="json") if final_state["knowledge_graph"] else None,
    }
    save_report(session_id, response)
    return response


@app.get("/api/sessions/{session_id}/report")
def get_session_report(session_id: str):
    report = get_report(session_id)
    if not report:
        raise HTTPException(404, "No report found for this session yet.")
    return report


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True)
