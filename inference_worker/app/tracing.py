import logging
import os
import sys

from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.exporter.jaeger.proto.grpc import (
    JaegerExporter as JaegerGrpcSpanExporter,
)
from opentelemetry.instrumentation.pika import PikaInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ALWAYS_ON
from pythonjsonlogger import jsonlogger

load_dotenv()

logHandler = logging.StreamHandler(sys.stdout)
formatter = jsonlogger.JsonFormatter("%(asctime)s %(name)s %(levelname)s %(message)s")
logHandler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)


def setup_tracing():
    service_name = os.getenv("OTEL_SERVICE_NAME", "inference-worker")

    resource = Resource(attributes={SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource, sampler=ALWAYS_ON)
    trace.set_tracer_provider(provider)

    jaeger_collector_host = os.getenv("JAEGER_COLLECTOR_HOST", "localhost")
    jaeger_collector_port = int(os.getenv("JAEGER_COLLECTOR_PORT", 14250))

    jaeger_exporter = JaegerGrpcSpanExporter(
        collector_endpoint=f"{jaeger_collector_host}:{jaeger_collector_port}",
        insecure=True,
    )

    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(jaeger_exporter))

    logger.info(
        f"Tracing is configured for service '{service_name}' sending to Jaeger Collector at {jaeger_collector_host}:{jaeger_collector_port}"
    )

    PikaInstrumentor().instrument()
    RequestsInstrumentor().instrument()


tracer = trace.get_tracer(__name__)
