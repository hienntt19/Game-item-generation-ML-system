import logging
import os

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.pika import PikaInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.sdk.trace.sampling import ALWAYS_ON

from .config import settings

logger = logging.getLogger(__name__)


def setup_tracing(app: FastAPI):
    resource = Resource(attributes={SERVICE_NAME: settings.OTEL_SERVICE_NAME})

    provider = TracerProvider(resource=resource, sampler=ALWAYS_ON)

    trace.set_tracer_provider(provider)

    jaeger_exporter = JaegerExporter(
        agent_host_name=settings.JAEGER_AGENT_HOST,
        agent_port=int(settings.JAEGER_AGENT_PORT),
    )

    span_processor = BatchSpanProcessor(jaeger_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)

    logger.info(
        f"Tracing is configured for service '{service_name}' sending to Jaeger at {settings.JAEGER_AGENT_HOST}:{settings.JAEGER_AGENT_PORT}"
    )

    FastAPIInstrumentor.instrument_app(app)
    PikaInstrumentor().instrument()


tracer = trace.get_tracer(__name__)
