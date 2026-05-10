import logging.config
import os
import sys

import structlog


def setup_logging(log_level: str = "INFO"):
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "console": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processor": structlog.dev.ConsoleRenderer(),
                    "foreign_pre_chain": shared_processors,
                },
                "json": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processor": structlog.processors.JSONRenderer(),
                    "foreign_pre_chain": shared_processors,
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": log_level,
                    "formatter": "console",
                    "stream": sys.stdout,
                },
                "json_file": {
                    "class": "logging.handlers.TimedRotatingFileHandler",
                    "level": "WARNING",
                    "formatter": "json",
                    "filename": os.path.join(log_dir, "app_structlog.json"),
                    "when": "D",
                    "interval": 1,
                    "backupCount": 14,
                    "encoding": "utf-8",
                },
            },
            "root": {
                "handlers": ["console", "json_file"],
                "level": log_level,
            },
        }
    )

    structlog.configure(
        processors=shared_processors
                   + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        wrapper_class=structlog.stdlib.AsyncBoundLogger,
        cache_logger_on_first_use=True,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )


setup_logging()