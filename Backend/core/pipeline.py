"""Service layer: the only thing a frontend or API needs to call."""
from pathlib import Path

from config import settings
from core import analysis, generation, ingestion, storage
from core.llm import LLMError
from core.rag.retriever import Retriever
from core.schemas import Angle, CaseStudy, LinkedInDraft, ProjectProfile, SourceDocument


class WorkflowError(ValueError):
    pass


def import_project(
    repo_url: str | None = None,
    pasted_readme: str | None = None,
    owner_user_id: str | None = None,
) -> str:
    if repo_url:
        docs = ingestion.from_github(repo_url)
    elif pasted_readme:
        docs = ingestion.from_pasted_markdown(pasted_readme)
    else:
        raise ingestion.IngestionError("Provide a GitHub URL or project/work notes.")
    if repo_url:
        name = repo_url.rstrip("/").split("/")[-1]
    else:
        headings = [
            line.strip().lstrip("#").strip()
            for line in pasted_readme.splitlines()
            if line.lstrip().startswith("#") and line.lstrip("#").strip()
        ]
        name = headings[0][:100] if headings else "Work sample"
    return storage.create_project(
        name,
        repo_url,
        docs[0].commit_sha,
        [d.model_dump() for d in docs],
        owner_user_id=owner_user_id,
    )


def import_local_project(path: str | Path) -> str:
    """Import a local project for trusted, in-process callers only."""
    docs = ingestion.from_local_path(path)
    name = Path(path).expanduser().name
    return storage.create_project(name, None, None, [d.model_dump() for d in docs])


def _load(project_id: str) -> tuple[dict, list[SourceDocument], Retriever]:
    p = storage.get_project(project_id)
    if not p:
        raise KeyError("Project not found")
    docs = [SourceDocument(**d) for d in p["documents"]]
    index = storage.ensure_project_index(project_id)
    if index is None:
        raise KeyError("Project not found")
    chunks = storage.get_project_chunks(project_id)
    if chunks is None:
        raise KeyError("Project not found")
    return p, docs, Retriever(chunks=chunks or [])


def search_project(project_id: str, query: str, limit: int | None = None) -> list[dict]:
    _, _, retriever = _load(project_id)
    return [
        {
            "chunk_id": hit.chunk.chunk_id,
            "source_id": hit.chunk.source_id,
            "path": hit.chunk.path,
            "start_line": hit.chunk.start_line,
            "end_line": hit.chunk.end_line,
            "heading": hit.chunk.heading,
            "source_url": hit.chunk.source_url,
            "text": hit.chunk.text,
            "score": hit.score,
        }
        for hit in retriever.search(query, k=limit)
    ]


def run_analysis(project_id: str) -> ProjectProfile:
    project, docs, retriever = _load(project_id)
    profile = analysis.analyze_project(docs, retriever, project_name=project["name"])
    storage.save_profile(project_id, profile.model_dump())
    return profile


def run_linkedin(project_id: str, angle: str, user_context: str = "", post_format: str = "standard"):
    p, docs, retriever = _load(project_id)
    if not p["profile"]:
        raise WorkflowError("Analyze this project before generating content.")
    profile = ProjectProfile(**p["profile"])
    draft = generation.generate_linkedin_draft(  # type: ignore[arg-type]
        profile, retriever, docs, angle, user_context, post_format
    )
    storage.save_artifact(project_id, f"linkedin:{angle}", draft.model_dump())
    return draft


def run_community_post(project_id: str, style: str = "show_and_tell", user_context: str = ""):
    p, docs, retriever = _load(project_id)
    if not p["profile"]:
        raise WorkflowError("Analyze this project before generating content.")
    post = generation.generate_community_post(
        ProjectProfile(**p["profile"]), retriever, docs, style, user_context
    )
    storage.save_artifact(project_id, "community_post", post.model_dump())
    return post


def _build_case_study(profile, retriever, docs, user_context, progress=None, base=15, span=80):
    """Chunked (section by section) by default; CASE_STUDY_CHUNKED=0 for big hosted models."""
    if settings.case_study_chunked:
        return generation.generate_case_study_chunked(
            profile, retriever, docs, user_context, progress, base, span
        )
    if progress:
        progress(int(base), "Writing case study")
    return generation.generate_case_study(profile, retriever, docs, user_context)


def run_case_study(project_id: str, user_context: str = "", progress=None) -> CaseStudy:
    p, docs, retriever = _load(project_id)
    if not p["profile"]:
        raise WorkflowError("Analyze this project before generating content.")
    cs = _build_case_study(ProjectProfile(**p["profile"]), retriever, docs, user_context, progress)
    storage.save_artifact(project_id, "case_study", cs.model_dump())
    return cs


def run_case_study_section(project_id: str, section: str, user_context: str = "") -> CaseStudy:
    """Regenerate one section of the saved case study and save it as the new generated version."""
    p, docs, retriever = _load(project_id)
    if not p["profile"]:
        raise WorkflowError("Analyze this project before generating content.")
    artifact = storage.get_project_artifact(project_id, "case_study")
    if artifact is None:
        raise WorkflowError("Generate the case study before regenerating a section.")
    current = CaseStudy.model_validate(artifact["current"])
    try:
        updated = generation.regenerate_case_study_section(
            current, section, ProjectProfile(**p["profile"]), retriever, docs, user_context
        )
    except ValueError as exc:
        raise WorkflowError(str(exc)) from exc
    storage.save_artifact(project_id, "case_study", updated.model_dump(), edited=artifact["edited"] is not None)
    return updated


def run_workflow(
    project_id: str,
    linkedin_angles: list[Angle],
    include_case_study: bool = False,
    user_context: str = "",
    reanalyze: bool = True,
    progress=None,
    post_format: str = "standard",
) -> dict:
    """`progress(percent, step_label)` is called between steps (used by background jobs)."""
    def tick(percent: int, label: str) -> None:
        if progress:
            progress(percent, label)

    steps = len(linkedin_angles) + (1 if include_case_study else 0)
    span = 70 / max(steps, 1)
    done = 0
    tick(5, "Reading project sources")
    if reanalyze:
        tick(10, "Analyzing project")
        profile = run_analysis(project_id)
    else:
        project, _, _ = _load(project_id)
        if not project["profile"]:
            raise WorkflowError("Analyze this project before running generation without reanalysis.")
        profile = ProjectProfile(**project["profile"])

    _, docs, retriever = _load(project_id)
    outputs: dict[str, dict] = {"linkedin": {}}
    tick(25, "Project profile ready")
    for angle in linkedin_angles:
        tick(int(25 + span * done), f"Writing {angle.replace('_', ' ')} post")
        try:
            draft: LinkedInDraft = generation.generate_linkedin_draft(
                profile, retriever, docs, angle, user_context, post_format
            )
            storage.save_artifact(
                project_id, f"linkedin:{angle}", draft.model_dump()
            )
            outputs["linkedin"][angle] = {
                "status": "generated",
                "artifact": draft.model_dump(),
            }
        except LLMError as exc:
            outputs["linkedin"][angle] = {
                "status": "failed",
                "error": str(exc),
            }
        done += 1

    if include_case_study:
        tick(int(25 + span * done), "Writing case study")
        try:
            case_study = _build_case_study(
                profile, retriever, docs, user_context, progress, 25 + span * done, span
            )
            storage.save_artifact(
                project_id, "case_study", case_study.model_dump()
            )
            outputs["case_study"] = {
                "status": "generated",
                "artifact": case_study.model_dump(),
            }
        except LLMError as exc:
            outputs["case_study"] = {
                "status": "failed",
                "error": str(exc),
            }

    tick(98, "Finishing up")
    return {
        "project_id": project_id,
        "analysis": profile.model_dump(),
        "outputs": outputs,
    }
