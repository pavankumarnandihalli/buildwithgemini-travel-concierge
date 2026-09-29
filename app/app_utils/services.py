# Copyright 2026 Google LLC

"""Process-wide ADK session, artifact, and memory services shared by every serving surface.

Registered under ``shared://`` so the ADK web routes, the A2A path, and the
reasoning_engine adapter share one instance.
"""

from __future__ import annotations

import functools
import os

from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
from google.adk.cli.service_registry import get_service_registry
from google.adk.cli.utils.service_factory import (
    create_memory_service_from_options,
    create_session_service_from_options,
)
from google.adk.memory.vertex_ai_memory_bank_service import (
    VertexAiMemoryBankService,
)

SESSION_SERVICE_URI = "shared://session"
ARTIFACT_SERVICE_URI = "shared://artifact"
MEMORY_SERVICE_URI = "shared://memory"

MEMORY_BANK_ID = "5137285561853149184"

_AGENT_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)


@functools.cache
def get_session_service():
    """Process-wide session service shared across every serving surface."""
    if uri := os.environ.get("SESSION_SERVICE_URI"):
        return create_session_service_from_options(
            base_dir=_AGENT_DIR, session_service_uri=uri
        )
    if agent_engine_id := os.environ.get("GOOGLE_CLOUD_AGENT_ENGINE_ID"):
        from google.adk.sessions.vertex_ai_session_service import VertexAiSessionService

        return VertexAiSessionService(
            project="qwiklabs-gcp-02-2a28910a07ed",
            location=os.environ.get("GOOGLE_CLOUD_AGENT_ENGINE_LOCATION") or "us-east1",
            agent_engine_id=agent_engine_id,
        )
    from google.adk.sessions.in_memory_session_service import InMemorySessionService

    return InMemorySessionService()


@functools.cache
def get_artifact_service():
    """Process-wide artifact service: GCS when a bucket is set, else in-memory."""
    if bucket := os.environ.get("LOGS_BUCKET_NAME"):
        return GcsArtifactService(bucket_name=bucket)
    return InMemoryArtifactService()


@functools.cache
def get_memory_service():
    """Process-wide memory service using Vertex AI Memory Bank."""
    if uri := os.environ.get("MEMORY_SERVICE_URI"):
        return create_memory_service_from_options(
            base_dir=_AGENT_DIR, memory_service_uri=uri
        )
    return VertexAiMemoryBankService(
        project="qwiklabs-gcp-02-2a28910a07ed",
        location="us-east1",
        agent_engine_id=MEMORY_BANK_ID,
    )


_registry = get_service_registry()
_registry.register_session_service("shared", lambda uri, **kw: get_session_service())
_registry.register_artifact_service("shared", lambda uri, **kw: get_artifact_service())
_registry.register_memory_service("shared", lambda uri, **kw: get_memory_service())
