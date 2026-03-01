import logging.config
import os
import sys

import structlog

def setup_logging(log_level: str = "INFO"):
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json_formatter": {
                "class": "logging.Formatter",
                "format": "%(message)s",
            },
            "console_formatter": {
                "class": "logging.Formatter",
                "format": "%(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "console_formatter",
                "stream": sys.stdout,
            },
            "json_file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "level": "WARNING",
                "formatter": "json_formatter",
                "filename": os.path.join(log_dir, "app_structlog.json"),
                "when": "D",
                "interval": 1,
                "backupCount": 14,
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "": {
                "handlers": ["console", "json_file"],
                "level": "DEBUG",
                "propagate": True,
            },
        }
    })

def setup_structlog():
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.AsyncBoundLogger, #type: ignore
        cache_logger_on_first_use=True,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )

    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if handler.name == "json_file":
            handler.setFormatter(formatter)
            break

setup_logging()
setup_structlog()
