"""
Logging configuration for Market Data Aggregator Service.
Supports both JSON and text logging formats.
"""

import logging
import logging.config
import sys
from typing import Dict, Any
from pythonjsonlogger import jsonlogger

from .config import settings


def setup_logging() -> None:
    """Setup structured logging for the application."""
    
    if settings.log_format == "json":
        logging_config = get_json_logging_config()
    else:
        logging_config = get_text_logging_config()
    
    logging.config.dictConfig(logging_config)
    
    # Set log level for the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level))
    
    # Reduce noise from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)


def get_json_logging_config() -> Dict[str, Any]:
    """Get JSON logging configuration."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": jsonlogger.JsonFormatter,
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(module)s %(funcName)s %(lineno)d",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.log_level,
                "formatter": "json",
                "stream": sys.stdout
            }
        },
        "loggers": {
            "": {
                "handlers": ["console"],
                "level": settings.log_level,
                "propagate": False
            },
            "app": {
                "handlers": ["console"],
                "level": settings.log_level,
                "propagate": False
            }
        }
    }


def get_text_logging_config() -> Dict[str, Any]:
    """Get text logging configuration."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s (%(filename)s:%(lineno)d)",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s [in %(pathname)s:%(lineno)d]",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.log_level,
                "formatter": "standard" if settings.log_level == "INFO" else "detailed",
                "stream": sys.stdout
            }
        },
        "loggers": {
            "": {
                "handlers": ["console"],
                "level": settings.log_level,
                "propagate": False
            },
            "app": {
                "handlers": ["console"],
                "level": settings.log_level,
                "propagate": False
            }
        }
    }


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(f"app.{name}")


# Convenience function for getting loggers
def create_logger(module_name: str) -> logging.Logger:
    """Create a logger for a specific module."""
    return get_logger(module_name)