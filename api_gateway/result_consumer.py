import json
import logging
import threading
import time
import uuid

import pika

from .config import settings
from .database import GenerationRequest, SessionLocal

logger = logging.getLogger(__name__)


class ResultConsumer:
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self.run, daemon=True)

    def _on_message(self, ch, method, properties, body):
        try:
            message = json.loads(body.decode("utf-8"))
            request_id_str = message.get("request_id")
            status = message.get("status")
            image_url = message.get("image_url")

            logger.info(
                "Received result message",
                extra={"request_id": request_id_str, "status": status},
            )

            db = SessionLocal()
            try:
                request_uuid = uuid.UUID(request_id_str)
                db.query(GenerationRequest).filter(
                    GenerationRequest.request_id == request_uuid
                ).update({"status": status, "image_url": image_url})
                db.commit()
                logger.info(
                    "Database updated successfully",
                    extra={"request_id": request_id_str},
                )
            finally:
                db.close()

        except Exception as e:
            logger.error("Failed to process result message", exc_info=True)
        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def run(self):
        while not self._stop_event.is_set():
            try:
                credentials = pika.PlainCredentials(
                    settings.RABBITMQ_USER, settings.RABBITMQ_PASS
                )
                connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host=settings.RABBITMQ_HOST,
                        credentials=credentials,
                        heartbeat=60,
                    )
                )
                channel = connection.channel()
                channel.queue_declare(queue=settings.RESULTS_QUEUE_NAME, durable=True)
                channel.basic_consume(
                    queue=settings.RESULTS_QUEUE_NAME,
                    on_message_callback=self._on_message,
                )

                logger.info("Result consumer connected, waiting for results...")
                channel.start_consuming()

            except pika.exceptions.AMQPConnectionError:
                logger.error("Result consumer connection failed. Retrying in 5s...")
                time.sleep(5)
            except Exception:
                logger.error(
                    "An unexpected error occurred in result consumer. Restarting...",
                    exc_info=True,
                )
                time.sleep(5)

    def start(self):
        logger.info("Starting result consumer thread...")
        self._thread.start()

    def stop(self):
        logger.info("Stopping result consumer thread...")
        self._stop_event.set()
        self._thread.join(timeout=5)
