import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.pika import PikaInstrumentor
from opentelemetry.sdk.trace.sampling import ALWAYS_ON


def setup_tracing(app):
    service_name = os.getenv("OTEL_SERVICE_NAME", "api-gateway")
    
    resource = Resource(
        attributes = {
            SERVICE_NAME: service_name
        }
    )
    
    provider = TracerProvider(resource=resource, sampler=ALWAYS_ON)
    
    trace.set_tracer_provider(provider)
    
    jaeger_agent_host = os.getenv("JAEGER_AGENT_HOST", "localhost")
    
    jaeger_exporter = JaegerExporter(
        agent_host_name = jaeger_agent_host,
        agent_port=6831
    )
    
    # span_processor = BatchSpanProcessor(jaeger_exporter)
    span_processor = SimpleSpanProcessor(jaeger_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
    
    print(f"Tracing is configured for service '{service_name}' sending to Jaeger at {jaeger_agent_host}:6831")
    
    FastAPIInstrumentor.instrument_app(app)
    
    PikaInstrumentor().instrument()
    