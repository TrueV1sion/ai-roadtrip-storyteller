import logging
import sys
from typing import Any, Dict
from functools import lru_cache

# Try to import Google Cloud Logging, but make it optional
try:
    import google.cloud.logging
    from google.cloud.logging.handlers import CloudLoggingHandler, setup_logging
    HAS_CLOUD_LOGGING = True
except ImportError:
    HAS_CLOUD_LOGGING = False
    CloudLoggingHandler = None

# --- LoggerConfig can likely be simplified or removed ---
# class LoggerConfig:
#     """Configuration class for logger settings"""
#     LOGGER_NAME_PREFIX = "roadtrip"
#     # DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s' # Format handled by CloudLoggingHandler
#     DEFAULT_LEVEL = logging.INFO
#
#     def __init__(self):
#         self.loggers: Dict[str, logging.Logger] = {}


@lru_cache(maxsize=None)
def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger instance configured for Google Cloud Logging.

    Args:
        name: The name for the logger instance (e.g., __name__)

    Returns:
        logging.Logger: Configured logger instance
    """
    # Use a simpler naming convention if desired, or keep the prefix
    logger_name = f"roadtrip.{name}"
    logger = logging.getLogger(logger_name)

    # Check if the logger already has the CloudLoggingHandler
    # This prevents adding duplicate handlers if get_logger is called multiple times
    if HAS_CLOUD_LOGGING and any(isinstance(h, CloudLoggingHandler) for h in logger.handlers):
        return logger

    # If no handlers (or no CloudLoggingHandler), configure it
    if not logger.handlers:
        try:
            # Try to use Cloud Logging if available
            if HAS_CLOUD_LOGGING:
                # Initialize the Cloud Logging client
                client = google.cloud.logging.Client()

                # Create a handler that sends logs to Cloud Logging
                # This handler automatically formats logs as JSON structured logs
                handler = CloudLoggingHandler(client, name=logger_name)

                # Attach the handler to the logger
                # setup_logging(handler) # setup_logging attaches it to the root logger, we want specific loggers
                logger.addHandler(handler)

                # Set the logging level (e.g., INFO, DEBUG)
                logger.setLevel(logging.INFO) # Or get from config if needed

                # Prevent propagation to avoid duplicate logs if root logger is also configured
                logger.propagate = False

                logger.info(f"Cloud Logging handler configured for logger: {logger_name}")
            else:
                # Cloud Logging not available, use console handler
                raise ImportError("Google Cloud Logging not available")

        except Exception as e:
            # Fallback to basic console logging if Cloud Logging setup fails
            if HAS_CLOUD_LOGGING:
                print(f"WARNING: Failed to set up Cloud Logging handler for {logger_name}: {e}. Falling back to basic console logging.", file=sys.stderr)
            if not logger.handlers: # Ensure fallback handler isn't added multiple times
                console_handler = logging.StreamHandler(sys.stdout)
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                console_handler.setFormatter(formatter)
                logger.addHandler(console_handler)
                logger.setLevel(logging.INFO)
                logger.propagate = False

    return logger


# --- configure_logger and clear_logger might need adjustments or become less relevant ---
# If direct configuration via get_logger is sufficient, these might be removed.
# If kept, they should interact with the CloudLoggingHandler appropriately.

# def configure_logger(
#     name: str,
#     level: int = logging.INFO,
#     format_string: str = None, # Format string is less relevant with CloudLoggingHandler
#     file_path: str = None
# ) -> logging.Logger:
#     """
#     Configure a logger with custom settings. (Needs review for Cloud Logging)
#     """
#     logger = get_logger(name)
#     logger.setLevel(level)
#
#     # Custom formatters might conflict with CloudLoggingHandler's JSON format.
#     # Adding file handlers might still be useful for local debugging.
#     if file_path:
#         # Check if file handler already exists
#         if not any(isinstance(h, logging.FileHandler) and h.baseFilename == file_path for h in logger.handlers):
#             try:
#                 file_handler = logging.FileHandler(file_path)
#                 file_handler.setLevel(level)
#                 # Use a standard formatter for the file handler
#                 formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#                 file_handler.setFormatter(formatter)
#                 logger.addHandler(file_handler)
#             except Exception as e:
#                 logger.error(f"Failed to add file handler for {file_path}: {e}")
#
#     return logger
#
#
# def clear_logger(name: str) -> None:
#     """
#     Clear all handlers from a logger. (Use with caution)
#     """
#     logger = get_logger(name)
#     for handler in logger.handlers[:]:
#         logger.removeHandler(handler)


# Create a default logger instance for backward compatibility
logger = get_logger(__name__)