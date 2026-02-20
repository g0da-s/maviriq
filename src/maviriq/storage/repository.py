import hashlib
import logging
from datetime import datetime, timedelta, timezone

from maviriq.models.schemas import (
    CompetitorResearchOutput,
    GraveyardResearchOutput,
    MarketIntelligenceOutput,
    PainDiscoveryOutput,
    SynthesisOutput,
    ValidationListItem,
    ValidationRun,
    ValidationStatus,
    ViabilityOutput,
)
from maviriq.storage import DatabaseError
from maviriq.supabase_client import get_supabase

logger = logging.getLogger(__name__)


class ValidationRepository:
    async def create(self, run: ValidationRun) -> None:
        sb = await get_supabase()
        try:
            await (
                sb.table("validation_runs")
                .insert(
                    {
                        "id": run.id,
                        "user_id": run.user_id,
                        "idea": run.idea,
                        "status": run.status.value,
                        "current_agent": run.current_agent,
                        "started_at": run.started_at.isoformat()
                        if run.started_at
                        else None,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                .execute()
            )
        except Exception as e:
            logger.exception("Failed to create validation run %s", run.id)
            raise DatabaseError(str(e)) from e

    async def update(self, run: ValidationRun) -> None:
        sb = await get_supabase()
        try:
            await (
                sb.table("validation_runs")
                .update(
                    {
                        "status": run.status.value,
                        "current_agent": run.current_agent,
                        "started_at": run.started_at.isoformat()
                        if run.started_at
                        else None,
                        "completed_at": run.completed_at.isoformat()
                        if run.completed_at
                        else None,
                        "error": run.error,
                        "pain_discovery_output": run.pain_discovery.model_dump()
                        if run.pain_discovery
                        else None,
                        "competitor_research_output": run.competitor_research.model_dump()
                        if run.competitor_research
                        else None,
                        "market_intelligence_output": run.market_intelligence.model_dump()
                        if run.market_intelligence
                        else None,
                        "graveyard_research_output": run.graveyard_research.model_dump()
                        if run.graveyard_research
                        else None,
                        "viability_output": run.viability.model_dump()
                        if run.viability
                        else None,
                        "synthesis_output": run.synthesis.model_dump()
                        if run.synthesis
                        else None,
                        "total_cost_cents": run.total_cost_cents,
                    }
                )
                .eq("id", run.id)
                .execute()
            )
        except Exception as e:
            logger.exception("Failed to update validation run %s", run.id)
            raise DatabaseError(str(e)) from e

    async def get(self, run_id: str) -> ValidationRun | None:
        sb = await get_supabase()
        try:
            result = (
                await sb.table("validation_runs")
                .select("*")
                .eq("id", run_id)
                .maybe_single()
                .execute()
            )
        except Exception as e:
            logger.exception("Failed to get validation run %s", run_id)
            raise DatabaseError(str(e)) from e
        if result is None or not result.data:
            return None
        return self._row_to_run(result.data)

    async def get_for_user(self, run_id: str, user_id: str) -> ValidationRun | None:
        """Fetch a validation run, enforcing ownership at the DB level."""
        sb = await get_supabase()
        try:
            result = await (
                sb.table("validation_runs")
                .select("*")
                .eq("id", run_id)
                .eq("user_id", user_id)
                .maybe_single()
                .execute()
            )
        except Exception as e:
            logger.exception("Failed to get validation run %s for user", run_id)
            raise DatabaseError(str(e)) from e
        if result is None or not result.data:
            return None
        return self._row_to_run(result.data)

    async def count_completed(self) -> int:
        sb = await get_supabase()
        try:
            result = (
                await sb.table("validation_runs")
                .select("id", count="exact")
                .eq("status", "completed")
                .execute()
            )
            return result.count or 0
        except Exception as e:
            logger.exception("Failed to count completed validations")
            return 0

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
        try:
            result = (
                await query.order("created_at", desc=True)
                .range(offset, offset + per_page - 1)
                .execute()
            )
        except Exception as e:
            logger.exception("Failed to list validation runs")
            raise DatabaseError(str(e)) from e

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

    async def delete_for_user(self, run_id: str, user_id: str) -> bool:
        """Delete a validation run, enforcing ownership at the DB level."""
        sb = await get_supabase()
        try:
            result = await (
                sb.table("validation_runs")
                .delete()
                .eq("id", run_id)
                .eq("user_id", user_id)
                .execute()
            )
        except Exception as e:
            logger.exception("Failed to delete validation run %s for user", run_id)
            raise DatabaseError(str(e)) from e
        return len(result.data) > 0

    async def fail_orphaned_runs(self) -> int:
        """Mark any 'running' or 'pending' runs as failed (e.g. after server restart)."""
        sb = await get_supabase()
        try:
            result = await (
                sb.table("validation_runs")
                .update(
                    {
                        "status": "failed",
                        "error": "Server restarted while validation was in progress",
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                .in_("status", ["running", "pending"])
                .execute()
            )
            count = len(result.data) if result.data else 0
            if count:
                logger.info("Marked %d orphaned validation run(s) as failed", count)
            return count
        except Exception as e:
            logger.exception("Failed to clean up orphaned runs")
            raise DatabaseError(str(e)) from e

    def _row_to_run(self, row: dict) -> ValidationRun:
        return ValidationRun(
            id=row["id"],
            idea=row["idea"],
            status=ValidationStatus(row["status"]),
            current_agent=row.get("current_agent", 0),
            started_at=datetime.fromisoformat(row["started_at"])
            if row.get("started_at")
            else None,
            completed_at=datetime.fromisoformat(row["completed_at"])
            if row.get("completed_at")
            else None,
            error=row.get("error"),
            pain_discovery=PainDiscoveryOutput.model_validate(
                row["pain_discovery_output"]
            )
            if row.get("pain_discovery_output")
            else None,
            competitor_research=CompetitorResearchOutput.model_validate(
                row["competitor_research_output"]
            )
            if row.get("competitor_research_output")
            else None,
            market_intelligence=MarketIntelligenceOutput.model_validate(
                row["market_intelligence_output"]
            )
            if row.get("market_intelligence_output")
            else None,
            graveyard_research=GraveyardResearchOutput.model_validate(
                row["graveyard_research_output"]
            )
            if row.get("graveyard_research_output")
            else None,
            viability=ViabilityOutput.model_validate(row["viability_output"])
            if row.get("viability_output")
            else None,
            synthesis=SynthesisOutput.model_validate(row["synthesis_output"])
            if row.get("synthesis_output")
            else None,
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
        try:
            result = await (
                sb.table("search_cache")
                .select("response")
                .eq("query_hash", key)
                .gt("expires_at", now)
                .limit(1)
                .execute()
            )
        except Exception:
            logger.warning(
                "Search cache read failed for query hash %s", key[:12], exc_info=True
            )
            return None
        if result is None or not result.data:
            return None
        return result.data[0]["response"]

    async def set(
        self, query: str, source: str, response: dict, ttl_seconds: int = 86400
    ) -> None:
        key = self._hash(query, source)
        expires = (
            datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        ).strftime("%Y-%m-%dT%H:%M:%S")
        sb = await get_supabase()
        try:
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
        except Exception:
            logger.warning(
                "Search cache write failed for query hash %s", key[:12], exc_info=True
            )

    def _hash(self, query: str, source: str) -> str:
        return hashlib.sha256(f"{source}:{query}".encode()).hexdigest()
