"""Retry handler with exponential backoff."""

import time
import logging
from typing import Callable, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 10.0
    exponential_base: float = 2.0


DEFAULT_RETRY_CONFIG = RetryConfig()


def execute_with_retry(
    func: Callable,
    retry_config: RetryConfig = DEFAULT_RETRY_CONFIG
) -> Any:
    """
    Execute a function with retry logic and exponential backoff.
    
    Args:
        func: Function to execute
        retry_config: Retry configuration
    
    Returns:
        Result from the function
    
    Raises:
        Exception: If all retry attempts fail
    """
    last_exception = None
    delay = retry_config.initial_delay
    
    for attempt in range(1, retry_config.max_attempts + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e
            
            if attempt == retry_config.max_attempts:
                logger.error(
                    f"All {retry_config.max_attempts} retry attempts failed. "
                    f"Last error: {str(e)}"
                )
                raise
            
            logger.warning(
                f"Attempt {attempt}/{retry_config.max_attempts} failed: {str(e)}. "
                f"Retrying in {delay:.1f}s..."
            )
            
            time.sleep(delay)
            delay = min(delay * retry_config.exponential_base, retry_config.max_delay)
    
    # This should never be reached, but just in case
    raise last_exception
