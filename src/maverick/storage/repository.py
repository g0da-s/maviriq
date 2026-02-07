import hashlib
import json
from datetime import datetime, timedelta, timezone

import aiosqlite

from maverick.models.schemas import (
    CompetitorResearchOutput,
    PainDiscoveryOutput,
    SynthesisOutput,
    ValidationListItem,
    ValidationRun,
    ValidationStatus,
    ViabilityOutput,
)
from maverick.storage.database import get_db


class ValidationRepository:
    async def create(self, run: ValidationRun) -> None:
        db = await get_db()
        try:
            await db.execute(
                """INSERT INTO validation_runs
                   (id, idea, status, current_agent, started_at, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    run.id,
                    run.idea,
                    run.status.value,
                    run.current_agent,
                    run.started_at.isoformat() if run.started_at else None,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            await db.commit()
        finally:
            await db.close()

    async def update(self, run: ValidationRun) -> None:
        db = await get_db()
        try:
            await db.execute(
                """UPDATE validation_runs SET
                   status = ?, current_agent = ?, started_at = ?,
                   completed_at = ?, error = ?,
                   pain_discovery_output = ?,
                   competitor_research_output = ?,
                   viability_output = ?,
                   synthesis_output = ?,
                   total_cost_cents = ?
                   WHERE id = ?""",
                (
                    run.status.value,
                    run.current_agent,
                    run.started_at.isoformat() if run.started_at else None,
                    run.completed_at.isoformat() if run.completed_at else None,
                    run.error,
                    run.pain_discovery.model_dump_json() if run.pain_discovery else None,
                    run.competitor_research.model_dump_json() if run.competitor_research else None,
                    run.viability.model_dump_json() if run.viability else None,
                    run.synthesis.model_dump_json() if run.synthesis else None,
                    run.total_cost_cents,
                    run.id,
                ),
            )
            await db.commit()
        finally:
            await db.close()

    async def get(self, run_id: str) -> ValidationRun | None:
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT * FROM validation_runs WHERE id = ?", (run_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return self._row_to_run(row)
        finally:
            await db.close()

    async def list(self, page: int = 1, per_page: int = 20) -> tuple[list[ValidationListItem], int]:
        db = await get_db()
        try:
            cursor = await db.execute("SELECT COUNT(*) FROM validation_runs")
            total_row = await cursor.fetchone()
            total = total_row[0] if total_row else 0

            offset = (page - 1) * per_page
            cursor = await db.execute(
                """SELECT id, idea, status, synthesis_output, created_at
                   FROM validation_runs
                   ORDER BY created_at DESC
                   LIMIT ? OFFSET ?""",
                (per_page, offset),
            )
            rows = await cursor.fetchall()

            items = []
            for row in rows:
                verdict = None
                confidence = None
                if row["synthesis_output"]:
                    synthesis = SynthesisOutput.model_validate_json(row["synthesis_output"])
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
        finally:
            await db.close()

    async def delete(self, run_id: str) -> bool:
        db = await get_db()
        try:
            cursor = await db.execute(
                "DELETE FROM validation_runs WHERE id = ?", (run_id,)
            )
            await db.commit()
            return cursor.rowcount > 0
        finally:
            await db.close()

    def _row_to_run(self, row: aiosqlite.Row) -> ValidationRun:
        return ValidationRun(
            id=row["id"],
            idea=row["idea"],
            status=ValidationStatus(row["status"]),
            current_agent=row["current_agent"],
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            error=row["error"],
            pain_discovery=PainDiscoveryOutput.model_validate_json(row["pain_discovery_output"]) if row["pain_discovery_output"] else None,
            competitor_research=CompetitorResearchOutput.model_validate_json(row["competitor_research_output"]) if row["competitor_research_output"] else None,
            viability=ViabilityOutput.model_validate_json(row["viability_output"]) if row["viability_output"] else None,
            synthesis=SynthesisOutput.model_validate_json(row["synthesis_output"]) if row["synthesis_output"] else None,
            total_cost_cents=row["total_cost_cents"],
        )


class SearchCacheRepository:
    def _utcnow_iso(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    async def get(self, query: str, source: str) -> dict | None:
        key = self._hash(query, source)
        now = self._utcnow_iso()
        db = await get_db()
        try:
            cursor = await db.execute(
                """SELECT response FROM search_cache
                   WHERE query_hash = ? AND expires_at > ?""",
                (key, now),
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return json.loads(row["response"])
        finally:
            await db.close()

    async def set(self, query: str, source: str, response: dict, ttl_seconds: int = 86400) -> None:
        key = self._hash(query, source)
        expires = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        expires_str = expires.strftime("%Y-%m-%dT%H:%M:%S")
        db = await get_db()
        try:
            await db.execute(
                """INSERT OR REPLACE INTO search_cache
                   (query_hash, source, query, response, expires_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (key, source, query, json.dumps(response), expires_str),
            )
            await db.commit()
        finally:
            await db.close()

    async def cleanup_expired(self) -> int:
        now = self._utcnow_iso()
        db = await get_db()
        try:
            cursor = await db.execute(
                "DELETE FROM search_cache WHERE expires_at <= ?", (now,)
            )
            await db.commit()
            return cursor.rowcount
        finally:
            await db.close()

    def _hash(self, query: str, source: str) -> str:
        return hashlib.sha256(f"{source}:{query}".encode()).hexdigest()
