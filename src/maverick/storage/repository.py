import hashlib
from datetime import datetime, timedelta, timezone

from maverick.models.schemas import (
    CompetitorResearchOutput,
    PainDiscoveryOutput,
    SynthesisOutput,
    ValidationListItem,
    ValidationRun,
    ValidationStatus,
    ViabilityOutput,
)
from maverick.supabase_client import get_supabase


class ValidationRepository:
    async def create(self, run: ValidationRun) -> None:
        sb = await get_supabase()
        await (
            sb.table("validation_runs")
            .insert(
                {
                    "id": run.id,
                    "user_id": run.user_id,
                    "idea": run.idea,
                    "status": run.status.value,
                    "current_agent": run.current_agent,
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .execute()
        )

    async def update(self, run: ValidationRun) -> None:
        sb = await get_supabase()
        await (
            sb.table("validation_runs")
            .update(
                {
                    "status": run.status.value,
                    "current_agent": run.current_agent,
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                    "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                    "error": run.error,
                    "pain_discovery_output": run.pain_discovery.model_dump() if run.pain_discovery else None,
                    "competitor_research_output": run.competitor_research.model_dump() if run.competitor_research else None,
                    "viability_output": run.viability.model_dump() if run.viability else None,
                    "synthesis_output": run.synthesis.model_dump() if run.synthesis else None,
                    "total_cost_cents": run.total_cost_cents,
                }
            )
            .eq("id", run.id)
            .execute()
        )

    async def get(self, run_id: str) -> ValidationRun | None:
        sb = await get_supabase()
        result = await sb.table("validation_runs").select("*").eq("id", run_id).maybe_single().execute()
        if result is None or not result.data:
            return None
        return self._row_to_run(result.data)

    async def list(
        self, page: int = 1, per_page: int = 20, user_id: str | None = None
    ) -> tuple[list[ValidationListItem], int]:
        sb = await get_supabase()
        query = sb.table("validation_runs").select(
            "id, idea, status, synthesis_output, created_at", count="exact"
        )
        if user_id:
            query = query.eq("user_id", user_id)

        offset = (page - 1) * per_page
        result = await query.order("created_at", desc=True).range(offset, offset + per_page - 1).execute()

        total = result.count or 0
        items = []
        for row in result.data:
            verdict = None
            confidence = None
            if row.get("synthesis_output"):
                synthesis = SynthesisOutput.model_validate(row["synthesis_output"])
                verdict = synthesis.verdict
                confidence = synthesis.confidence
            items.append(
                ValidationListItem(
                    id=row["id"],
                    idea=row["idea"],
                    status=ValidationStatus(row["status"]),
                    verdict=verdict,
                    confidence=confidence,
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )
        return items, total

    async def delete(self, run_id: str) -> bool:
        sb = await get_supabase()
        result = await sb.table("validation_runs").delete().eq("id", run_id).execute()
        return len(result.data) > 0

    def _row_to_run(self, row: dict) -> ValidationRun:
        return ValidationRun(
            id=row["id"],
            idea=row["idea"],
            status=ValidationStatus(row["status"]),
            current_agent=row.get("current_agent", 0),
            started_at=datetime.fromisoformat(row["started_at"]) if row.get("started_at") else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row.get("completed_at") else None,
            error=row.get("error"),
            pain_discovery=PainDiscoveryOutput.model_validate(row["pain_discovery_output"]) if row.get("pain_discovery_output") else None,
            competitor_research=CompetitorResearchOutput.model_validate(row["competitor_research_output"]) if row.get("competitor_research_output") else None,
            viability=ViabilityOutput.model_validate(row["viability_output"]) if row.get("viability_output") else None,
            synthesis=SynthesisOutput.model_validate(row["synthesis_output"]) if row.get("synthesis_output") else None,
            total_cost_cents=row.get("total_cost_cents", 0),
            user_id=row.get("user_id"),
        )


class SearchCacheRepository:
    def _utcnow_iso(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    async def get(self, query: str, source: str) -> dict | None:
        key = self._hash(query, source)
        now = self._utcnow_iso()
        sb = await get_supabase()
        result = await (
            sb.table("search_cache")
            .select("response")
            .eq("query_hash", key)
            .gt("expires_at", now)
            .maybe_single()
            .execute()
        )
        if result is None or not result.data:
            return None
        return result.data["response"]

    async def set(self, query: str, source: str, response: dict, ttl_seconds: int = 86400) -> None:
        key = self._hash(query, source)
        expires = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        sb = await get_supabase()
        await (
            sb.table("search_cache")
            .upsert(
                {
                    "query_hash": key,
                    "source": source,
                    "query": query,
                    "response": response,
                    "expires_at": expires,
                },
                on_conflict="query_hash",
            )
            .execute()
        )

    async def cleanup_expired(self) -> int:
        now = self._utcnow_iso()
        sb = await get_supabase()
        result = await sb.table("search_cache").delete().lte("expires_at", now).execute()
        return len(result.data)

    def _hash(self, query: str, source: str) -> str:
        return hashlib.sha256(f"{source}:{query}".encode()).hexdigest()
