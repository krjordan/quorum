"""
Logging configuration
"""
import logging
import sys


def setup_logging():
    """Configure application logging"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Set LiteLLM logging to warning only
    litellm_logger = logging.getLogger("litellm")
    litellm_logger.setLevel(logging.WARNING)

    # Set httpx logging to warning only
    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel(logging.WARNING)
