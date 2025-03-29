import sys
from datetime import datetime
from typing import Optional

from loguru import logger as _logger


# Remove all default handlers
_logger.remove()

# Add only console handler for default logger
_logger.add(sys.stderr, level="INFO")

# Export the console-only logger as the default
logger = _logger


def define_log_level(print_level="INFO", logfile_level="DEBUG", name: Optional[str] = None) -> _logger.__class__:
    """
    Configure a new logger with console and file output.

    Args:
        print_level: Log level for console output
        logfile_level: Log level for file output
        name: Logger name (used for log filename)

    Returns:
        Configured logger instance
    """
    # Import here to avoid circular imports
    from app.workspace_manager import workspace_manager

    # Create a new logger instance
    new_logger = _logger.bind()

    # Remove any existing handlers
    new_logger.remove()

    # Add console handler
    new_logger.add(sys.stderr, level=print_level)

    # Ensure a meaningful log name is always used
    if name:
        # Create logs directory in the workspace
        log_path = workspace_manager.setup_logging(name)

        # Add file handler
        new_logger.add(str(log_path), level=logfile_level)

    return new_logger


if __name__ == "__main__":
    # Example usage
    test_logger = define_log_level(name="test")
    test_logger.info("Starting application")
    test_logger.debug("Debug message")
    test_logger.warning("Warning message")
    test_logger.error("Error message")
    test_logger.critical("Critical message")

    try:
        raise ValueError("Test error")
    except Exception as e:
        test_logger.exception(f"An error occurred: {e}")
