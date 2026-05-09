from __future__ import annotations

from app.catalog import Catalog
from app.models import CatalogItem, ChatResponse, Intent, NeedState
from app.recommendation_guard import (
    MAX_RECOMMENDATIONS,
    bind_recommendations_to_catalog,
    catalog_rows_to_recommendations,
)
from app.retrieval import find_by_name_fuzzy, rank


def _should_end_conversation(state: NeedState, response: ChatResponse) -> bool:
    if state.intent == Intent.refuse:
        return False
    if state.intent == Intent.compare:
        return False
    if (
        state.intent == Intent.clarify
        and state.user_signaled_done
        and state.prior_assistant_substantive
    ):
        return True
    if state.intent == Intent.clarify:
        return False
    if state.intent in (Intent.recommend, Intent.refine):
        if not response.recommendations:
            return False
        return bool(state.user_signaled_done and state.prior_assistant_substantive)
    return False


def respond(catalog: Catalog, state: NeedState) -> ChatResponse:
    out: ChatResponse

    if state.intent == Intent.refuse:
        out = ChatResponse(
            reply=(
                "I can only help with selecting SHL assessments from the SHL catalog. "
                "If you share the role and what you need to measure (skills, cognitive ability, personality), "
                "I can recommend suitable SHL assessments."
            ),
            recommendations=[],
            end_of_conversation=False,
        )
        return out.model_copy(update={"end_of_conversation": _should_end_conversation(state, out)})

    if catalog.is_empty:
        out = ChatResponse(
            reply=(
                "I’m set up to recommend SHL assessments, but the local catalog is empty. "
                "Please generate `data/catalog.json` (e.g., run the catalog scrape script) and restart the service."
            ),
            recommendations=[],
            end_of_conversation=False,
        )
        return out.model_copy(update={"end_of_conversation": _should_end_conversation(state, out)})

    if state.intent == Intent.compare:
        a = find_by_name_fuzzy(catalog, state.comparison_targets[0]) if state.comparison_targets else None
        b = find_by_name_fuzzy(catalog, state.comparison_targets[1]) if len(state.comparison_targets) > 1 else None

        if not a or not b:
            out = ChatResponse(
                reply=(
                    "I can compare two SHL assessments using the catalog, but I couldn’t uniquely match both names. "
                    "Please provide the exact assessment names (or paste the SHL catalog URLs)."
                ),
                recommendations=[],
                end_of_conversation=False,
            )
            return out.model_copy(update={"end_of_conversation": _should_end_conversation(state, out)})

        def fmt(i: CatalogItem) -> str:
            bits: list[str] = [f"**{i.name}** ({i.test_type})"]
            if i.duration_minutes is not None:
                bits.append(f"Duration: ~{i.duration_minutes} minutes")
            if i.languages:
                bits.append(f"Languages: {', '.join(i.languages[:8])}")
            if i.job_levels:
                bits.append(f"Job levels: {', '.join(i.job_levels[:8])}")
            if i.remote_testing is not None:
                bits.append(f"Remote testing: {'Yes' if i.remote_testing else 'No/Not listed'}")
            if i.description:
                bits.append(f"Description: {i.description[:400].strip()}")
            bits.append(f"URL: {str(i.url)}")
            return "\n".join(bits)

        out = ChatResponse(
            reply=f"Here’s a catalog-based comparison:\n\n{fmt(a)}\n\n---\n\n{fmt(b)}",
            recommendations=[],
            end_of_conversation=False,
        )
        return out.model_copy(update={"end_of_conversation": _should_end_conversation(state, out)})

    if state.intent == Intent.clarify:
        if not state.role_title and not state.skills:
            q = "What role or skill area are you hiring for (e.g., software engineer, sales, customer service)?"
        else:
            q = "Should I focus only on job skills/knowledge, or also include cognitive ability and/or personality fit?"
        out = ChatResponse(reply=q, recommendations=[], end_of_conversation=False)
        return out.model_copy(update={"end_of_conversation": _should_end_conversation(state, out)})

    ranked = rank(catalog, state, top_k=MAX_RECOMMENDATIONS)
    rows = [s.item for s in ranked]
    recs = catalog_rows_to_recommendations(rows)
    recs = bind_recommendations_to_catalog(catalog, recs)

    if not recs:
        out = ChatResponse(
            reply=(
                "I couldn’t build a confident shortlist from the SHL catalog for that request yet. "
                "Share the role, key skills to measure, and any constraints (duration, remote, language)."
            ),
            recommendations=[],
            end_of_conversation=False,
        )
        return out.model_copy(update={"end_of_conversation": _should_end_conversation(state, out)})

    need_bits: list[str] = []
    if state.role_title:
        need_bits.append(state.role_title)
    if state.seniority:
        need_bits.append(state.seniority)
    if state.skills:
        need_bits.append("skills: " + ", ".join(state.skills[:6]))
    if state.max_duration_minutes is not None:
        need_bits.append(f"≤{state.max_duration_minutes} min")

    prefix = "Updated shortlist" if state.intent == Intent.refine else "Shortlist"
    summary = ", ".join([b for b in need_bits if b]) or "your role requirements"

    reply = (
        f"{prefix} for {summary}. "
        f"Here are {len(recs)} SHL assessments from the catalog that best match."
    )

    out = ChatResponse(reply=reply, recommendations=recs, end_of_conversation=False)
    return out.model_copy(update={"end_of_conversation": _should_end_conversation(state, out)})
