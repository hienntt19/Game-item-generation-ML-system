import logging

LOG_LEVEL = "INFO"

JSON_FORMAT = (
    "%(timestamp)s %(levelname)s %(message)s "
    "%(otelTraceID)s %(otelSpanID)s %(otelServiceName)s"
)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": JSON_FORMAT,
            "rename_fields": {"levelname": "level", "asctime": "timestamp"},
        },
    },
    "handlers": {
        "default": {
            "formatter": "json",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "": {"handlers": ["default"], "level": LOG_LEVEL, "propagate": True},
        "uvicorn.error": {"handlers": ["default"], "level": LOG_LEVEL, "propagate": False},
        "uvicorn.access": {"handlers": ["default"], "level": LOG_LEVEL, "propagate": False},
    },
}