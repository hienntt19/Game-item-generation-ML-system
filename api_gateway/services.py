import logging

import pika
from fastapi import HTTPException

from .config import settings

logger = logging.getLogger(__name__)


class RabbitMQManager:
    def __init__(self, host, user, password, queue_name):
        self.host = host
        self.user = user
        self.password = password
        self.queue_name = queue_name
        self.connection = None
        self.channel = None

    def _is_connection_open(self):
        return (
            self.connection
            and self.connection.is_open
            and self.channel
            and self.channel.is_open
        )

    def connect(self):
        if self._is_connection_open():
            logger.debug("Connection is already open.")
            return True
        try:
            logger.info("Attempting to connect to RabbitMQ...")
            credentials = pika.PlainCredentials(self.user, self.password)
            params = pika.ConnectionParameters(
                host=self.host,
                credentials=credentials,
                heartbeat=60,
                blocked_connection_timeout=300,
            )
            self.connection = pika.BlockingConnection(params)
            self.channel = self.connection.channel()

            self.channel.queue_declare(queue=self.queue_name, durable=True)
            self.channel.confirm_delivery()

            logger.info("RabbitMQ connection and channel established successfully!")
            return True

        except pika.exceptions.AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            self.connection = None
            self.channel = None
            return False

    def get_channel(self):
        if self._is_connection_open():
            return self.channel

        logger.warning(
            "RabbitMQ connection is closed or not established. Attempting to connect."
        )
        if self.connect():
            return self.channel
        else:
            logger.critical("Could not re-establish connection to RabbitMQ.")
            return None

    def close(self):
        if self.connection and self.connection.is_open:
            logger.info("Closing RabbitMQ connection...")
            self.connection.close()
            logger.info("RabbitMQ connection closed.")


rabbitmq_manager = RabbitMQManager(
    host=settings.RABBITMQ_HOST,
    user=settings.RABBITMQ_USER,
    password=settings.RABBITMQ_PASS,
    queue_name=settings.QUEUE_NAME,
)


def get_mq_channel():
    channel = rabbitmq_manager.get_channel()
    if not channel:
        raise HTTPException(
            status_code=503,
            detail="Service unavailable: Cannot connect to message queue",
        )
    return channel
