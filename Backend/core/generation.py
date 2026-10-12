import json

from core.analysis import load_prompt
from core.evidence import draft_statements, verify_claims
from core.llm import LLMError, complete_json
from core.rag.retriever import Retriever
from core.schemas import (
    Angle, CaseStudy, CommunityPost, LinkedInDraft, ProjectProfile, SourceDocument,
)

ANGLES: dict[str, tuple[str, str]] = {
    "technical_lesson": ("technical lesson: how something works or an insight learned", "how it works architecture implementation"),
    "engineering_decision": ("engineering decision: a documented design choice, alternatives and trade-offs", "design decision trade-off why chose instead"),
    "personal_reflection": ("personal reflection: what the developer learned or struggled with (needs USER CONTEXT)", "challenges limitations lessons"),
}

POST_FORMATS: dict[str, str] = {
    "standard": "",
    "concise": "Length: keep the whole post under about 600 characters; one idea only.\n",
    "technical_walkthrough": "Lead with the engineering detail and walk through how it works step by step; assume a technical reader.\n",
    "project_update": "Frame the post as a project update: what exists now, what was done, and one lesson, without claiming outcomes the sources do not state.\n",
}

COMMUNITY_STYLES: dict[str, str] = {
    "show_and_tell": "Show & tell: introduce what the project is and the most interesting documented detail.",
    "devlog": "Devlog: a short build-log entry about what was built or changed and how it works.",
    "til": "TIL: a single concrete technical takeaway from the work, stated plainly.",
    "ask": "Ask the community: describe the documented approach briefly and end with one open, specific question for other developers.",
}

CASE_SECTIONS = ["summary", "problem", "architecture", "implementation", "challenges", "results", "limitations", "future_work"]


_ANGLE_FINDINGS: dict[str, set[str]] = {
    "technical_lesson": {"summary", "problem", "technology", "architecture", "result"},
    "engineering_decision": {"decision"},
    "personal_reflection": {"summary", "problem", "technology", "architecture", "decision", "result"},
}


def _finding_evidence(profile: ProjectProfile, allowed_kinds: set[str]) -> str:
    findings = [
        finding for finding in profile.findings
        if finding.status == "supported" and finding.kind in allowed_kinds
    ]
    parts = []
    for finding in findings:
        evidence_parts = []
        for source in finding.evidence:
            line_range = (
                f":{source.start_line}-{source.end_line}"
                if source.start_line is not None and source.end_line is not None
                else ""
            )
            evidence_parts.append(
                f"Source: {source.path}{line_range}\n"
                f"Excerpt: {source.excerpt.strip()}"
            )
        if evidence_parts:
            parts.append(
                f"Validated finding: {finding.text}\n"
                + "\n".join(evidence_parts)
            )
    return "\n\n---\n\n".join(parts)


def _generation_evidence(profile: ProjectProfile, retriever: Retriever, angle: Angle) -> str:
    if not profile.findings:
        return ""
    return _finding_evidence(profile, _ANGLE_FINDINGS[angle])


def _case_study_evidence(profile: ProjectProfile, retriever: Retriever) -> str:
    if not profile.findings:
        return ""
    return _finding_evidence(profile, {
        "summary", "problem", "technology", "architecture", "decision",
        "challenge", "result", "limitation",
    })


def generate_linkedin_draft(profile: ProjectProfile, retriever: Retriever, docs: list[SourceDocument],
                            angle: Angle, user_context: str = "",
                            post_format: str = "standard") -> LinkedInDraft:
    if angle == "personal_reflection" and not user_context.strip():
        return LinkedInDraft(
            angle=angle,
            hook="",
            insight="",
            body="",
            takeaway="",
            needs_user_input=(
                "What personal experience or lesson from working on this project would you like to share?"
            ),
        )

    desc, query = ANGLES[angle]
    evidence_context = _generation_evidence(profile, retriever, angle)
    if not evidence_context.strip():
        raise LLMError(f"No source-backed findings are available for post angle: {angle}")
    prompt = load_prompt("linkedin_posts").substitute(
        angle=angle, angle_description=desc, profile=profile.name,
        context=evidence_context, user_context=user_context or "(none)",
        format_instruction=POST_FORMATS.get(post_format, ""),
    )
    draft = complete_json(prompt, LinkedInDraft)
    if not draft.body.strip():
        draft = complete_json(
            f"""Your previous post draft did not include a post body. Write a
complete post for {desc}, with a distinct hook and a non-empty body of at least
two concise sentences. Use the strongest supported project details and do not
infer a motivation, benefit, limitation, comparison, or personal experience.
For engineering decisions, describe an observable implementation choice without
inventing its rationale. Include factual sentences in claims.
Use strings for angle, hook, insight, body, and takeaway; use null or a string for
question and needs_user_input; claims must be an array of strings. Set angle to {angle}.
Do not use placeholder values.

PROJECT NAME: {profile.name}
EVIDENCE:
{evidence_context}

USER CONTEXT:
{user_context or "(none)"}""",
            LinkedInDraft,
        )
    if not draft.body.strip():
        raise LLMError(f"Model returned an incomplete post draft for angle: {angle}")

    draft.angle = angle
    if angle != "personal_reflection":
        draft.needs_user_input = None

    draft.claims = draft_statements(
        (draft.hook, draft.insight, draft.body, draft.takeaway, draft.question or ""),
        draft.claims,
    )
    _verify_linkedin_draft(draft, retriever, docs)
    if draft.review_status != "preliminary_support":
        correction = (
            f"{prompt}\n\nRevise the draft: the previous draft included statements not "
            "supported by the validated findings. Use only the listed findings, write "
            "one or two concise factual sentences, and do not mention evidence, citations, "
            "validation, absent information, or conclusions not explicitly stated."
        )
        draft = complete_json(correction, LinkedInDraft)
        draft.angle = angle
        draft.needs_user_input = None if angle != "personal_reflection" else draft.needs_user_input
        if not draft.body.strip():
            raise LLMError(f"Model returned an incomplete post draft for angle: {angle}")
        draft.claims = draft_statements(
            (draft.hook, draft.insight, draft.body, draft.takeaway, draft.question or ""),
            draft.claims,
        )
        _verify_linkedin_draft(draft, retriever, docs)
    return draft


def _verify_linkedin_draft(draft: LinkedInDraft, retriever: Retriever, docs: list[SourceDocument]) -> None:
    draft.verified_claims = verify_claims(draft.claims, retriever, docs)
    draft.review_status = (
        "preliminary_support"
        if draft.verified_claims and all(claim.status == "supported" for claim in draft.verified_claims)
        else "needs_review"
    )


def generate_all_drafts(profile, retriever, docs, user_context: str = "") -> dict[str, LinkedInDraft | str]:
    """One failure must not discard the others: errors come back as strings."""
    out: dict[str, LinkedInDraft | str] = {}
    for angle in ANGLES:
        try:
            out[angle] = generate_linkedin_draft(profile, retriever, docs, angle, user_context)  # type: ignore[arg-type]
        except Exception as e:  # noqa: BLE001
            out[angle] = f"error: {e}"
    return out


def generate_case_study(profile: ProjectProfile, retriever: Retriever, docs: list[SourceDocument],
                        user_context: str = "") -> CaseStudy:
    evidence_context = _case_study_evidence(profile, retriever)
    if not evidence_context.strip():
        raise LLMError("No source-backed findings are available for case-study generation.")
    safe_profile = profile.model_copy(update={
        "findings": [finding for finding in profile.findings if finding.status == "supported"],
        "unknowns": [],
    })
    prompt = load_prompt("case_study").substitute(
        profile=safe_profile.model_dump_json(indent=2), context=evidence_context,
        user_context=user_context or "(none)", section_rule="",
    )
    cs = complete_json(prompt, CaseStudy)
    if not cs.summary.strip():
        cs = complete_json(
            f"""{prompt}

Your previous draft had no executive summary. Write a complete, concise case
study from the supported findings and excerpts above. Give the work a readable
story, populate each section that has direct support, keep unsupported sections
empty, and list factual sentences in claims. Do not return placeholder text.""",
            CaseStudy,
        )
    if not cs.summary.strip():
        raise LLMError("Model returned an incomplete case study without a summary.")
    cs.claims = draft_statements(
        (cs.summary, cs.problem, cs.architecture, cs.implementation,
         cs.challenges, cs.results, cs.limitations, cs.future_work),
        cs.claims,
    )
    _verify_case_study(cs, retriever, docs)
    if cs.review_status != "preliminary_support":
        correction = (
            f"{prompt}\n\nRevise the case study: remove every statement not directly "
            "supported by a validated finding. Leave unsupported sections empty. Do not "
            "claim that information, results, features, limitations, or plans are absent "
            "or undocumented. Do not mention citations, validation, or evidence in the prose."
        )
        cs = complete_json(correction, CaseStudy)
        cs.claims = draft_statements(
            (cs.summary, cs.problem, cs.architecture, cs.implementation,
             cs.challenges, cs.results, cs.limitations, cs.future_work),
            cs.claims,
        )
        _verify_case_study(cs, retriever, docs)
    cs.claims = draft_statements(
        (cs.summary, cs.problem, cs.architecture, cs.implementation,
         cs.challenges, cs.results, cs.limitations, cs.future_work),
        [],
    )
    _verify_case_study(cs, retriever, docs)
    return cs


def _verify_case_study(cs: CaseStudy, retriever: Retriever, docs: list[SourceDocument]) -> None:
    cs.verified_claims = verify_claims(cs.claims, retriever, docs)
    cs.review_status = (
        "preliminary_support"
        if cs.verified_claims and all(claim.status == "supported" for claim in cs.verified_claims)
        else "needs_review"
    )


def regenerate_section(cs: CaseStudy, section: str, profile: ProjectProfile, retriever: Retriever,
                       docs: list[SourceDocument], user_context: str = "") -> CaseStudy:
    if section not in CASE_SECTIONS:
        raise ValueError(f"Unknown section: {section}")
    fresh = generate_case_study(profile, retriever, docs, user_context)
    data = json.loads(cs.model_dump_json())
    data[section] = getattr(fresh, section)
    return CaseStudy.model_validate(data)


def generate_community_post(profile: ProjectProfile, retriever: Retriever, docs: list[SourceDocument],
                            style: str = "show_and_tell", user_context: str = "") -> CommunityPost:
    """A Markdown post for the developer feed, claim-checked like every other artifact."""
    from core.social import MAX_POST_CHARS, SocialError, normalize_tags

    if style not in COMMUNITY_STYLES:
        raise LLMError(f"Unknown community post style: {style}")
    evidence_context = _case_study_evidence(profile, retriever)
    if not evidence_context.strip():
        raise LLMError("No source-backed findings are available for a community post.")
    prompt = load_prompt("community_post").substitute(
        style_description=COMMUNITY_STYLES[style], profile=profile.name,
        context=evidence_context, user_context=user_context or "(none)",
    )

    def build(text: str) -> CommunityPost:
        post = complete_json(text, CommunityPost)
        if not post.body.strip():
            raise LLMError("Model returned an empty community post.")
        post.body = post.body.strip()[:MAX_POST_CHARS]
        post.needs_user_input = None
        try:
            post.tags = normalize_tags(post.tags[:5], 5)
        except SocialError:  # keep only the well-formed ones rather than failing the run
            good = []
            for tag in post.tags:
                try:
                    good += normalize_tags([tag], 1)
                except SocialError:
                    continue
            post.tags = list(dict.fromkeys(good))[:5]
        post.claims = draft_statements((post.body,), post.claims)
        post.verified_claims = verify_claims(post.claims, retriever, docs)
        post.review_status = (
            "preliminary_support"
            if post.verified_claims and all(c.status == "supported" for c in post.verified_claims)
            else "needs_review"
        )
        return post

    post = build(prompt)
    if post.review_status != "preliminary_support":
        weak = [c.text for c in post.verified_claims if c.status != "supported"][:5]
        post = build(
            f"{prompt}\n\nRevise the post: these statements were not supported by the findings "
            f"and must be removed or rewritten using only the findings: {weak}. Keep the same "
            "Markdown style and do not mention evidence or validation."
        )
    return post


# --------------------------------------------------------------- chunked case study
# A 7B local model cannot reliably fill a nine-field JSON object in one go. Instead
# each section gets a small, focused prompt with only the material it needs, is
# verified on its own, and can fail or be regenerated without touching the rest.

from core.schemas import SectionDraft, TitledSectionDraft  # noqa: E402

_SECTION_SPECS: dict[str, dict] = {
    "problem": {
        "title": "Problem",
        "goal": "What problem or need the project addresses, as the material states it.",
        "length": "1-3 sentences (20-70 words)",
        "kinds": {"problem", "summary"},
        "query": "problem motivation goal why purpose users need",
    },
    "architecture": {
        "title": "Architecture",
        "goal": "How the system is structured: its main components and how they relate.",
        "length": "2-5 sentences (50-130 words)",
        "kinds": {"architecture", "technology"},
        "query": "architecture components design structure modules layers data flow",
    },
    "implementation": {
        "title": "Implementation",
        "goal": "Notable implementation details and engineering decisions, naming concrete technologies.",
        "length": "2-5 sentences (50-130 words)",
        "kinds": {"technology", "architecture", "decision"},
        "query": "implementation how it works api endpoints database framework library algorithm",
    },
    "challenges": {
        "title": "Challenges",
        "goal": "Difficulties, trade-offs or problems the material says were met and how they were handled.",
        "length": "1-4 sentences (30-100 words)",
        "kinds": {"challenge", "decision"},
        "query": "challenges difficulties issues trade-off bug workaround lessons learned",
        "extra": "Only describe a challenge that the material explicitly names. Otherwise leave it empty.",
    },
    "results": {
        "title": "Results",
        "goal": "Outcomes the material actually reports (behavior delivered, tests, measurements).",
        "length": "1-4 sentences (30-100 words)",
        "kinds": {"result"},
        "query": "results metrics performance accuracy benchmark tests outcome tested",
        "extra": "Never state a number that is not in the material. Otherwise leave it empty.",
    },
    "limitations": {
        "title": "Limitations",
        "goal": "Known limitations or caveats the material states.",
        "length": "1-3 sentences (20-80 words)",
        "kinds": {"limitation", "challenge"},
        "query": "limitations known issues caveats not supported todo missing",
        "extra": "Only state limitations that are written in the material. Do not criticise the project.",
    },
    "future_work": {
        "title": "Future work",
        "goal": "Plans, roadmap items or TODOs the material states.",
        "length": "1-3 sentences (20-80 words)",
        "kinds": {"limitation", "challenge"},
        "query": "future work roadmap planned todo next steps ideas upcoming",
        "extra": "Only include plans written in the material. Never suggest improvements yourself.",
    },
}
_SUMMARY_SPEC = {
    "title": "Summary",
    "goal": "A readable overview: what the project is, what stands out technically, and what it does. Also give the case study a short, specific title (3-8 words).",
    "length": "2-3 sentences (40-90 words)",
    "kinds": {"summary", "problem", "technology", "architecture", "result"},
    "query": "what is this project purpose overview features",
}
SECTION_WRITE_ORDER = list(_SECTION_SPECS) + ["summary"]  # summary last: it summarises the rest
_FINDINGS_BUDGET = 2500
_EXCERPT_BUDGET = 4200


def _cap_blocks(text: str, budget: int, sep: str = "\n\n---\n\n") -> str:
    out, used = [], 0
    for block in text.split(sep):
        if not block.strip():
            continue
        if used + len(block) > budget and out:
            break
        out.append(block[:budget])
        used += len(block)
    return sep.join(out)


def _section_material(profile: ProjectProfile, retriever: Retriever, spec: dict) -> tuple[str, str]:
    findings = _cap_blocks(_finding_evidence(profile, spec["kinds"]), _FINDINGS_BUDGET)
    blocks, used = [], 0
    for hit in retriever.search(spec["query"], k=4):
        c = hit.chunk
        text = c.text.strip()[:1000]
        if used + len(text) > _EXCERPT_BUDGET:
            break
        blocks.append(f"[{c.path}:{c.start_line}-{c.end_line}]\n{text}")
        used += len(text)
    return findings, "\n\n---\n\n".join(blocks)


def _written_context(written: dict[str, str]) -> str:
    parts = [f"{name}: {text[:260]}" for name, text in written.items() if text.strip()]
    return "\n".join(parts)[:1400] or "(nothing yet)"


def _verify_section(name: str, text: str, claims: list[str], retriever: Retriever,
                    docs: list[SourceDocument]) -> list:
    statements = draft_statements((text,), claims)
    verified = verify_claims(statements, retriever, docs)
    for claim in verified:
        claim.section = name
    return verified


def _all_supported(verified: list) -> bool:
    return bool(verified) and all(c.status == "supported" for c in verified)


def write_case_study_section(
    name: str,
    profile: ProjectProfile,
    retriever: Retriever,
    docs: list[SourceDocument],
    written: dict[str, str],
    user_context: str = "",
) -> tuple[str, list, str, str]:
    """Write and verify one section. Returns (text, verified_claims, status, title)."""
    spec = _SUMMARY_SPEC if name == "summary" else _SECTION_SPECS[name]
    findings, excerpts = _section_material(profile, retriever, spec)
    if not findings.strip() and not excerpts.strip():
        return "", [], "skipped", ""
    titled = name == "summary"
    shape = (
        '"title": "...", "text": "...", "claims": ["..."]' if titled
        else '"text": "...", "claims": ["..."]'
    )
    prompt = load_prompt("case_study_section").substitute(
        section_title=spec["title"], section_goal=spec["goal"], length_hint=spec["length"],
        extra_rule=spec.get("extra", ""), json_shape=shape, project_name=profile.name,
        findings=findings or "(none)", excerpts=excerpts or "(none)",
        written=_written_context(written), user_context=user_context or "(none)",
    )
    model_cls = TitledSectionDraft if titled else SectionDraft
    draft = complete_json(prompt, model_cls)
    text = draft.text.strip()
    title = getattr(draft, "title", "").strip()
    if not text:
        return "", [], "skipped", title
    verified = _verify_section(name, text, draft.claims, retriever, docs)
    if not _all_supported(verified):
        weak = [c.text for c in verified if c.status != "supported"][:4]
        try:
            retry = complete_json(
                f"{prompt}\n\nRevise: these statements are not supported by the material and must be "
                f"removed or rewritten using only what it says: {weak}. Keep the rest.",
                model_cls,
            )
        except LLMError:
            retry = None
        if retry and retry.text.strip():
            retry_verified = _verify_section(name, retry.text.strip(), retry.claims, retriever, docs)
            weak_now = sum(c.status != "supported" for c in verified)
            if retry_verified and sum(c.status != "supported" for c in retry_verified) <= weak_now:
                text, verified = retry.text.strip(), retry_verified
                title = getattr(retry, "title", "").strip() or title
    return text, verified, ("supported" if _all_supported(verified) else "needs_review"), title


def generate_case_study_chunked(
    profile: ProjectProfile,
    retriever: Retriever,
    docs: list[SourceDocument],
    user_context: str = "",
    progress=None,
    base: float = 15,
    span: float = 80,
) -> CaseStudy:
    """Write the case study one section at a time.

    `progress(percent, label)` is called before each section (it may raise to cancel).
    A section that fails or has no support is left empty and reported in
    `section_status`; only if every section fails does the whole run fail.
    """
    texts: dict[str, str] = {}
    claims: list = []
    status: dict[str, str] = {}
    title = ""
    last_error: LLMError | None = None
    total = len(SECTION_WRITE_ORDER)
    for index, name in enumerate(SECTION_WRITE_ORDER):
        if progress:
            label = (_SUMMARY_SPEC if name == "summary" else _SECTION_SPECS[name])["title"]
            progress(int(base + span * index / total), f"Writing {label.lower()} ({index + 1} of {total})")
        try:
            text, verified, state, sec_title = write_case_study_section(
                name, profile, retriever, docs, texts, user_context
            )
        except LLMError as exc:
            last_error, text, verified, state, sec_title = exc, "", [], "failed", ""
        texts[name] = text
        claims.extend(verified)
        status[name] = state
        if name == "summary" and sec_title:
            title = sec_title
    if all(state == "failed" for state in status.values()) and last_error:
        raise last_error
    if not any(texts.values()):
        raise LLMError("No source-backed findings are available for case-study generation.")
    cs = CaseStudy(
        title=title or f"{profile.name}: case study",
        summary=texts.get("summary", ""),
        problem=texts.get("problem", ""),
        architecture=texts.get("architecture", ""),
        implementation=texts.get("implementation", ""),
        challenges=texts.get("challenges", ""),
        results=texts.get("results", ""),
        limitations=texts.get("limitations", ""),
        future_work=texts.get("future_work", ""),
        claims=[c.text for c in claims],
        verified_claims=claims,
        section_status=status,
    )
    cs.review_status = "preliminary_support" if _all_supported(claims) else "needs_review"
    return cs


def regenerate_case_study_section(
    cs: CaseStudy, section: str, profile: ProjectProfile, retriever: Retriever,
    docs: list[SourceDocument], user_context: str = "",
) -> CaseStudy:
    """Rewrite one section (and its claims), leaving every other section untouched."""
    if section == "title" or section not in CASE_SECTIONS:
        raise ValueError(f"Unknown section: {section}")
    written = {name: getattr(cs, name) for name in CASE_SECTIONS if name != section}
    text, verified, state, title = write_case_study_section(
        section, profile, retriever, docs, written, user_context
    )
    data = json.loads(cs.model_dump_json())
    data[section] = text
    if section == "summary" and title:
        data["title"] = title
    kept = [c for c in cs.verified_claims if c.section != section]
    data["verified_claims"] = [c.model_dump() for c in [*kept, *verified]]
    data["claims"] = [c["text"] for c in data["verified_claims"]]
    data["section_status"] = {**cs.section_status, section: state}
    out = CaseStudy.model_validate(data)
    out.review_status = (
        "preliminary_support" if _all_supported(out.verified_claims) else "needs_review"
    )
    return out
