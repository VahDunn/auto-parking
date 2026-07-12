import os
import socket
from collections.abc import Sequence

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.aiokafka import AIOKafkaInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import (
    Decision,
    ParentBased,
    Sampler,
    SamplingResult,
    TraceIdRatioBased,
)
from opentelemetry.trace import Link, SpanKind, TraceState
from opentelemetry.util.types import Attributes
from sqlalchemy.ext.asyncio import AsyncEngine

from auto_parking.core.config import settings

TRACER_PROVIDER_STATE_KEY = "otel_tracer_provider"


class EntryPointSampler(Sampler):
    def __init__(self, delegate: Sampler) -> None:
        self._delegate = delegate

    def should_sample(
        self,
        parent_context: Context | None,
        trace_id: int,
        name: str,
        kind: SpanKind | None = None,
        attributes: Attributes = None,
        links: Sequence[Link] | None = None,
        trace_state: TraceState | None = None,
    ) -> SamplingResult:
        if kind not in {SpanKind.SERVER, SpanKind.CONSUMER}:
            return SamplingResult(Decision.DROP)

        return self._delegate.should_sample(
            parent_context=parent_context,
            trace_id=trace_id,
            name=name,
            kind=kind,
            attributes=attributes,
            links=links,
            trace_state=trace_state,
        )

    def get_description(self) -> str:
        return f"EntryPointSampler{{delegate={self._delegate.get_description()}}}"


def setup_tracing(app: FastAPI, engine: AsyncEngine) -> TracerProvider | None:
    if not settings.otel_tracing_enabled:
        return None

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.namespace": "auto-parking",
            "service.version": settings.otel_service_version,
            "service.instance.id": f"{socket.gethostname()}:{os.getpid()}",
            "deployment.environment.name": settings.app_env,
        }
    )
    provider = TracerProvider(
        resource=resource,
        sampler=ParentBased(
            root=EntryPointSampler(TraceIdRatioBased(settings.otel_trace_sample_ratio))
        ),
    )
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_traces_endpoint))
    )
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=provider,
        excluded_urls=settings.otel_fastapi_excluded_urls,
        exclude_spans=["receive", "send"],
    )
    SQLAlchemyInstrumentor().instrument(
        engine=engine.sync_engine,
        tracer_provider=provider,
    )
    HTTPXClientInstrumentor().instrument(tracer_provider=provider)
    RedisInstrumentor().instrument(tracer_provider=provider)
    AIOKafkaInstrumentor().instrument(tracer_provider=provider)

    setattr(app.state, TRACER_PROVIDER_STATE_KEY, provider)
    return provider


def shutdown_tracing(app: FastAPI) -> None:
    provider = getattr(app.state, TRACER_PROVIDER_STATE_KEY, None)
    if not isinstance(provider, TracerProvider):
        return

    provider.shutdown()
    delattr(app.state, TRACER_PROVIDER_STATE_KEY)
