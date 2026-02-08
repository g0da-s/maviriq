from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel


class SSEEvent(BaseModel):
    event: str
    data: dict[str, Any]


class AgentStartedEvent(SSEEvent):
    event: str = "agent_started"

    @classmethod
    def create(cls, agent_num: int, name: str) -> "AgentStartedEvent":
        return cls(data={"agent": agent_num, "name": name, "timestamp": datetime.now(timezone.utc).isoformat()})


class AgentProgressEvent(SSEEvent):
    event: str = "agent_progress"

    @classmethod
    def create(cls, agent_num: int, message: str, progress: float) -> "AgentProgressEvent":
        return cls(data={"agent": agent_num, "message": message, "progress": progress})


class AgentCompletedEvent(SSEEvent):
    event: str = "agent_completed"

    @classmethod
    def create(cls, agent_num: int, name: str, output: dict) -> "AgentCompletedEvent":
        return cls(data={"agent": agent_num, "name": name, "output": output, "timestamp": datetime.now(timezone.utc).isoformat()})


class PipelineCompletedEvent(SSEEvent):
    event: str = "pipeline_completed"

    @classmethod
    def create(cls, run_id: str, verdict: str, confidence: float) -> "PipelineCompletedEvent":
        return cls(data={"id": run_id, "verdict": verdict, "confidence": confidence, "timestamp": datetime.now(timezone.utc).isoformat()})


class PipelineErrorEvent(SSEEvent):
    event: str = "pipeline_error"

    @classmethod
    def create(cls, agent_num: int, error: str) -> "PipelineErrorEvent":
        return cls(data={"agent": agent_num, "error": error, "timestamp": datetime.now(timezone.utc).isoformat()})
