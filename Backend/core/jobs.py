"""Background AI jobs: run slow model work off the request thread with progress.

A job is a row in `ai_jobs`. A small thread pool executes it and writes progress
(0-100 plus a human-readable step) so the UI can poll `GET /jobs/{id}`.
Single-process by design; for multiple servers move the pool to a real queue.
"""
import json
import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from config import settings
from core import dev_ai, pipeline, storage
from core.ingestion import IngestionError
from core.llm import LLMError

log = logging.getLogger(__name__)

PROJECT_KINDS = {"analyze", "linkedin", "case_study", "case_study_section", "community_post", "workflow"}
TEXT_KINDS = {"improve_post", "suggest_tags", "summarize_thread"}
KINDS = PROJECT_KINDS | TEXT_KINDS
ACTIVE = ("queued", "running")


class JobError(ValueError):
    """Bad request for a job (maps to 409/422)."""


class JobLimitError(JobError):
    """Too many jobs (maps to 429)."""


class JobCancelled(Exception):
    pass


_executor: ThreadPoolExecutor | None = None
_executor_lock = threading.Lock()


def _pool() -> ThreadPoolExecutor:
    global _executor
    with _executor_lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(
                max_workers=max(1, settings.ai_workers), thread_name_prefix="ai-job"
            )
        return _executor


def shutdown() -> None:
    global _executor
    with _executor_lock:
        if _executor is not None:
            _executor.shutdown(wait=False, cancel_futures=True)
            _executor = None


def recover_interrupted() -> int:
    """Jobs left queued/running by a crash or restart can never finish; fail them."""
    with storage.conn() as c:
        cursor = c.execute(
            """UPDATE ai_jobs SET status='failed',error='The server restarted before this job finished.',
            finished_at=? WHERE status IN ('queued','running')""",
            (storage._now(),),
        )
    return cursor.rowcount


def _row(row) -> dict:
    return {
        "job_id": row["job_id"],
        "kind": row["kind"],
        "project_id": row["project_id"],
        "status": row["status"],
        "progress": row["progress"],
        "step": row["step"],
        "result": json.loads(row["result_json"]) if row["result_json"] else None,
        "error": row["error"],
        "created_at": row["created_at"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
    }


def create_job(user_id: str, kind: str, params: dict, project_id: str | None = None) -> dict:
    if kind not in KINDS:
        raise JobError(f"Unknown job kind: {kind}")
    if (kind in PROJECT_KINDS) != bool(project_id):
        raise JobError(
            "This job needs a project_id." if kind in PROJECT_KINDS
            else "This job does not take a project_id."
        )
    day_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    job_id = uuid.uuid4().hex
    with storage.conn() as c:
        c.execute("BEGIN IMMEDIATE")
        active = c.execute(
            "SELECT COUNT(*) FROM ai_jobs WHERE user_id=? AND status IN ('queued','running')",
            (user_id,),
        ).fetchone()[0]
        if active >= settings.ai_max_active_jobs_per_user:
            raise JobError("You already have AI jobs running. Wait for one to finish.")
        if project_id and c.execute(
            "SELECT 1 FROM ai_jobs WHERE project_id=? AND status IN ('queued','running')",
            (project_id,),
        ).fetchone():
            raise JobError("An AI job is already running for this project.")
        today = c.execute(
            "SELECT COUNT(*) FROM ai_jobs WHERE user_id=? AND created_at>=?",
            (user_id, day_start.isoformat()),
        ).fetchone()[0]
        if today >= settings.ai_daily_job_limit:
            raise JobLimitError("Daily AI job limit reached. Try again tomorrow.")
        c.execute(
            """INSERT INTO ai_jobs(job_id,user_id,project_id,kind,params_json,status,
            progress,step,created_at) VALUES(?,?,?,?,?,'queued',0,'Queued',?)""",
            (job_id, user_id, project_id, kind, json.dumps(params), storage._now()),
        )
    _pool().submit(_run, job_id)
    return get_job(user_id, job_id)


def get_job(user_id: str, job_id: str) -> dict:
    with storage.conn() as c:
        row = c.execute(
            "SELECT * FROM ai_jobs WHERE job_id=? AND user_id=?", (job_id, user_id)
        ).fetchone()
    if row is None:
        raise KeyError("Job not found.")
    return _row(row)


def list_jobs(
    user_id: str, project_id: str | None = None, active_only: bool = False, limit: int = 20
) -> list[dict]:
    sql = "SELECT * FROM ai_jobs WHERE user_id=?"
    args: list = [user_id]
    if project_id:
        sql += " AND project_id=?"
        args.append(project_id)
    if active_only:
        sql += " AND status IN ('queued','running')"
    sql += " ORDER BY created_at DESC,job_id DESC LIMIT ?"
    args.append(limit)
    with storage.conn() as c:
        return [_row(r) for r in c.execute(sql, args)]


def cancel_job(user_id: str, job_id: str) -> dict:
    """Queued jobs stop immediately; running jobs stop at the next progress checkpoint."""
    with storage.conn() as c:
        row = c.execute(
            "SELECT status FROM ai_jobs WHERE job_id=? AND user_id=?", (job_id, user_id)
        ).fetchone()
        if row is None:
            raise KeyError("Job not found.")
        if row["status"] in ACTIVE:
            c.execute(
                """UPDATE ai_jobs SET status='cancelled',step='Cancelled',finished_at=?
                WHERE job_id=?""",
                (storage._now(), job_id),
            )
    return get_job(user_id, job_id)


class _Reporter:
    def __init__(self, job_id: str):
        self.job_id = job_id

    def __call__(self, percent: int, step: str) -> None:
        with storage.conn() as c:
            row = c.execute("SELECT status FROM ai_jobs WHERE job_id=?", (self.job_id,)).fetchone()
            if row is None or row["status"] == "cancelled":
                raise JobCancelled()
            c.execute(
                "UPDATE ai_jobs SET progress=?,step=? WHERE job_id=?",
                (max(0, min(99, percent)), step, self.job_id),
            )


def _execute(kind: str, user_id: str, project_id: str | None, p: dict, report: _Reporter) -> dict:
    if kind == "analyze":
        report(10, "Analyzing project")
        return {"analysis": pipeline.run_analysis(project_id).model_dump()}
    if kind == "linkedin":
        report(15, "Writing post")
        draft = pipeline.run_linkedin(
            project_id, p["angle"], p.get("user_context", ""), p.get("post_format", "standard")
        )
        return {"artifact_type": f"linkedin:{p['angle']}", "artifact": draft.model_dump()}
    if kind == "case_study":
        report(5, "Preparing case study")
        return {"artifact_type": "case_study",
                "artifact": pipeline.run_case_study(project_id, p.get("user_context", ""), progress=report).model_dump()}
    if kind == "case_study_section":
        report(20, f"Rewriting {p['section'].replace('_', ' ')}")
        return {"artifact_type": "case_study",
                "artifact": pipeline.run_case_study_section(
                    project_id, p["section"], p.get("user_context", "")).model_dump()}
    if kind == "community_post":
        report(15, "Writing community post")
        post = pipeline.run_community_post(
            project_id, p.get("style", "show_and_tell"), p.get("user_context", "")
        )
        return {"artifact_type": "community_post", "artifact": post.model_dump()}
    if kind == "workflow":
        return pipeline.run_workflow(
            project_id, p.get("angles", []), p.get("include_case_study", False),
            p.get("user_context", ""), p.get("reanalyze", True),
            progress=report, post_format=p.get("post_format", "standard"),
        )
    if kind == "improve_post":
        report(20, "Improving your draft")
        return dev_ai.improve_post(p["text"], p.get("goal", "clarity"))
    if kind == "suggest_tags":
        report(20, "Finding tags")
        return dev_ai.suggest_tags(p["text"])
    if kind == "summarize_thread":
        report(20, "Reading the discussion")
        return dev_ai.summarize_thread(p["post_id"], user_id)
    raise JobError(f"Unknown job kind: {kind}")


def _finish(job_id: str, status: str, result: dict | None = None, error: str | None = None) -> None:
    with storage.conn() as c:
        # Never overwrite a cancellation that landed while the work was finishing.
        c.execute(
            """UPDATE ai_jobs SET status=?,progress=?,step=?,result_json=?,error=?,finished_at=?
            WHERE job_id=? AND status!='cancelled'""",
            (status, 100 if status == "succeeded" else 0, "Done" if status == "succeeded" else "Failed",
             json.dumps(result) if result is not None else None, error, storage._now(), job_id),
        )


def _run(job_id: str) -> None:
    try:
        with storage.conn() as c:
            row = c.execute("SELECT * FROM ai_jobs WHERE job_id=?", (job_id,)).fetchone()
            if row is None or row["status"] != "queued":
                return  # cancelled while waiting in the queue
            c.execute(
                "UPDATE ai_jobs SET status='running',started_at=?,step='Starting' WHERE job_id=?",
                (storage._now(), job_id),
            )
        params = json.loads(row["params_json"])
        result = _execute(row["kind"], row["user_id"], row["project_id"], params, _Reporter(job_id))
        _finish(job_id, "succeeded", result)
    except JobCancelled:
        log.info("AI job %s cancelled", job_id)
    except (LLMError, IngestionError, pipeline.WorkflowError, KeyError, ValueError) as exc:
        _finish(job_id, "failed", error=str(exc).strip("'\"") or "The AI job failed.")
    except Exception:  # noqa: BLE001 - never leave a job stuck in 'running'
        log.exception("AI job %s crashed", job_id)
        _finish(job_id, "failed", error="The AI job failed unexpectedly. Please try again.")
