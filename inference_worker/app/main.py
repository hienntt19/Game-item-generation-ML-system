import os

from dotenv import load_dotenv

load_dotenv()

if os.path.exists("gcs-key.json"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcs-key.json"

from config import setup_logging
from consumer import RabbitMQConsumer
from processing import load_model_and_dependencies
from tracing import setup_tracing


def main():
    setup_logging()
    setup_tracing()

    pipe, device, gcs_bucket = load_model_and_dependencies()

    consumer = RabbitMQConsumer(pipe=pipe, device=device, gcs_bucket=gcs_bucket)

    consumer.run()


if __name__ == "__main__":
    main()
