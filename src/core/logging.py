import logging
import sys
import json
from datetime import datetime, timezone
from src.config import settings


class StructuredJSONFormatter(logging.Formatter):
    """
    Custom log formatter outputting logs as structured JSON strings.
    Improves searchability and standardizes log parsing.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "func_name": record.funcName,
            "line_number": record.lineno,
        }
        
        # Append exception tracebacks if an exception is logged
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        # Allow passing extra structured metadata
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            # Safe merge
            for key, val in record.extra.items():
                if key not in log_data:
                    log_data[key] = val
                    
        return json.dumps(log_data)


def setup_logging() -> None:
    """
    Configures the root logger and specific web server loggers to emit 
    structured JSON logs to stdout.
    """
    root_logger = logging.getLogger()
    
    # Clear any existing pre-configured handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredJSONFormatter())
    root_logger.addHandler(console_handler)
    
    # Determine the log level
    level_name = settings.LOG_LEVEL.upper()
    log_level = getattr(logging, level_name, logging.INFO)
    root_logger.setLevel(log_level)
    
    # Configure Uvicorn and FastAPI loggers to align formats
    web_loggers = ["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"]
    for logger_name in web_loggers:
        logger = logging.getLogger(logger_name)
        logger.handlers = [console_handler]
        logger.setLevel(log_level)
        logger.propagate = False
