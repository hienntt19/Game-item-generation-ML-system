import json
import logging
import time

import pika
from opentelemetry import trace
from opentelemetry.propagate import extract
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from config import settings
from processing import process_image_request
from tracing import tracer

logger = logging.getLogger(__name__)


class RabbitMQConsumer:
    def __init__(self, pipe, device, gcs_bucket):
        self.pipe = pipe
        self.device = device
        self.gcs_bucket = gcs_bucket
        self.credentials = pika.PlainCredentials(
            settings.RABBITMQ_DEFAULT_USER, settings.RABBITMQ_DEFAULT_PASS
        )

    def _publish_result(self, channel, request_id: str, image_url: str):
        result_message = {
            "request_id": request_id,
            "status": "Completed" if image_url else "failed",
            "image_url": image_url,
        }

        try:
            channel.basic_publish(
                exchange="",
                routing_key=settings.RESULTS_QUEUE_NAME,
                body=json.dumps(result_message),
                properties=pika.BasicProperties(
                    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
                ),
            )
            logger.info("Result message published", extra={"request_id": request_id})
        except Exception as e:
            logger.error(
                "Failed to publish result message",
                extra={"request_id": request_id, "error": str(e)},
            )

    def _on_message(self, ch, method, properties, body):
        request_id = None
        carrier = properties.headers if properties.headers else {}
        ctx = TraceContextTextMapPropagator().extract(carrier=carrier)

        try:
            message = json.loads(body.decode("utf-8"))
            request_id = message.get("request_id")

            with tracer.start_as_current_span(
                "process_inference_request", context=ctx
            ) as span:
                span.set_attribute("request_id", request_id)
                logger.info("Received message", extra={"request_id": request_id})

                image_url = process_image_request(
                    pipe=self.pipe,
                    device=self.device,
                    gcs_bucket=self.gcs_bucket,
                    request_id=request_id,
                    params=message.get("params", {}),
                )

                self._publish_result(ch, request_id, image_url)

        except Exception as e:
            logger.error(
                "Error processing message",
                extra={"request_id": request_id, "error": str(e)},
                exc_info=True,
            )
            if request_id:
                self._publish_result(ch, request_id, None)
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            try:
                trace.get_tracer_provider().force_flush()
            except Exception as e:
                logger.error(
                    "Failed to flush spans",
                    extra={"request_id": request_id, "error": str(e)},
                )

    def run(self):
        while True:
            connection = None
            try:
                connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host=settings.RABBITMQ_HOST,
                        credentials=self.credentials,
                        heartbeat=600,
                    )
                )
                channel = connection.channel()
                channel.queue_declare(queue=settings.QUEUE_NAME, durable=True)
                channel.queue_declare(queue=settings.RESULTS_QUEUE_NAME, durable=True)
                channel.basic_qos(prefetch_count=1)
                channel.basic_consume(
                    queue=settings.QUEUE_NAME,
                    on_message_callback=self._on_message,
                )

                logger.info("--> Connected to RabbitMQ. Waiting for messages...")
                channel.start_consuming()
            except pika.exceptions.AMQPConnectionError as e:
                logger.error(
                    "Connection failed, retrying in 10s...", extra={"error": str(e)}
                )
                time.sleep(10)
            except Exception as e:
                logger.error(
                    "Unexpected error, restarting consumer in 10s...",
                    extra={"error": str(e)},
                    exc_info=True,
                )
                time.sleep(10)
            finally:
                if connection and connection.is_open:
                    connection.close()
