"""VANTYX Health Check Schemas."""

from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Liveness probe response."""
    status: str = Field(default="ok", description="Liveness status indicator")
    app: str = Field(default="VANTYX", description="Application name")
    version: str = Field(default="0.1.0", description="Application semantic version")
    environment: str = Field(description="Active runtime environment")
    timestamp: datetime = Field(description="UTC timestamp of the health check")


class ComponentHealth(BaseModel):
    """Component-level health status."""
    status: str = Field(description="Component status: healthy | degraded | unreachable")
    message: str = Field(description="Descriptive status message")
    latency_ms: Optional[float] = Field(default=None, description="Probe latency in milliseconds if measured")


class ReadinessResponse(BaseModel):
    """Readiness probe response indicating system and dependency availability."""
    status: str = Field(description="Overall readiness: ready | degraded")
    timestamp: datetime = Field(description="UTC timestamp of the readiness check")
    components: Dict[str, ComponentHealth] = Field(
        description="Health states of subsystem components and external dependencies"
    )
