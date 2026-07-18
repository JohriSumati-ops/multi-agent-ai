"""
core/logging.py

WHY THIS FILE EXISTS
---------------------
Five different categories of log line will exist in this system: general
application logs, API request/response logs, database logs, error logs, and
(from Phase 3 onward) agent execution logs. If every module calls
`print()` or configures its own logger ad hoc, log output becomes
impossible to filter, ship to a log aggregator, or reason about in
production.

This module configures ONE logging tree with named child loggers, so every
part of the app gets consistent formatting and can be filtered independently
(e.g., "show me only database logs at WARNING level").

SOFTWARE ENGINEERING PRINCIPLE
--------------------------------
Centralized, hierarchical logging configuration — configure once at
startup, obtain loggers by name everywhere else (`logging.getLogger(__name__)`
convention).

HOW FUTURE AI MODULES WILL USE THIS
-------------------------------------
The "agent" logger channel defined here is what `agents/base_agent.py` and
the AgentExecutionLog repository will write to once agents exist. Setting it
up now means Phase 3 doesn't need to touch logging configuration at all.
"""

import logging
import logging.config
import sys

from core.config import settings

# Named logger channels. Using these names consistently lets an operator
# tune verbosity per-subsystem in one place (e.g., silence DB logs but keep
# agent logs at DEBUG).
LOGGER_NAMES = {
    "app": "app",
    "api": "app.api",
    "database": "app.database",
    "error": "app.error",
    "agent": "app.agent",
}


def _build_logging_config() -> dict:
    formatter = "json" if settings.LOG_JSON else "standard"

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "format": (
                    '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
                    '"logger": "%(name)s", "message": "%(message)s"}'
                ),
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": formatter,
                "stream": sys.stdout,
            },
        },
        "loggers": {
            LOGGER_NAMES["app"]: {"handlers": ["console"], "level": settings.LOG_LEVEL, "propagate": False},
            LOGGER_NAMES["api"]: {"handlers": ["console"], "level": settings.LOG_LEVEL, "propagate": False},
            LOGGER_NAMES["database"]: {"handlers": ["console"], "level": settings.LOG_LEVEL, "propagate": False},
            LOGGER_NAMES["error"]: {"handlers": ["console"], "level": "WARNING", "propagate": False},
            LOGGER_NAMES["agent"]: {"handlers": ["console"], "level": settings.LOG_LEVEL, "propagate": False},
            # Quiet down noisy third-party loggers by default.
            "uvicorn.access": {"handlers": ["console"], "level": "WARNING", "propagate": False},
            "sqlalchemy.engine": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        },
        "root": {"handlers": ["console"], "level": settings.LOG_LEVEL},
    }


def configure_logging() -> None:
    """Call once at application startup (see main.py)."""
    logging.config.dictConfig(_build_logging_config())


def get_logger(channel: str = "app") -> logging.Logger:
    """
    Retrieve a named logger by channel key (see LOGGER_NAMES).

    Example:
        logger = get_logger("agent")
        logger.info("Reading Agent started execution")
    """
    name = LOGGER_NAMES.get(channel, channel)
    return logging.getLogger(name)
