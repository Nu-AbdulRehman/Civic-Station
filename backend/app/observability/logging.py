"""JSON logs on stdout with the five fixed fields of FR-BE-023 (AD-040, AD-057).

structlog renders through stdlib logging, so uvicorn's own records come out as the same JSON.
"""

import logging
import sys
from datetime import UTC, datetime
from typing import IO, Any

import structlog
from structlog.types import EventDict, WrappedLogger


def _add_ts(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    now = datetime.now(UTC).isoformat(timespec="milliseconds")
    event_dict["ts"] = now.replace("+00:00", "Z")
    return event_dict


def _ensure_request_id(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    event_dict.setdefault("request_id", None)
    return event_dict


_SHARED: list[Any] = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    _add_ts,
    _ensure_request_id,
]


def configure_logging(level: str, stream: IO[str] = sys.stdout) -> None:
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_SHARED,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            lambda _, __, ed: {**ed, "level": ed["level"].upper()},
            structlog.processors.format_exc_info,
            structlog.processors.EventRenamer("msg"),
            structlog.processors.JSONRenderer(),
        ],
    )
    handler = logging.StreamHandler(stream)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    # Our middleware logs every request; uvicorn's access line would duplicate it unstructured.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True
    logging.getLogger("uvicorn.access").disabled = True

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *_SHARED,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    logger: structlog.stdlib.BoundLogger = structlog.stdlib.get_logger(name)
    return logger
