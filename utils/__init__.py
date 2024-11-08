"""
Utility Module Initialization and Shared Utilities

This module provides centralized utility functions, decorators, 
and common helper methods used across the application.
"""

import functools
import time
import logging
from typing import Any, Callable, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from contextlib import contextmanager

class Utilities:
    """
    Centralized utility class for common application-wide functions
    """
    
    def __init__(self):
        """
        Initialize utility services
        """
        self.logger = logging.getLogger(__name__)
        self._thread_pool = ThreadPoolExecutor(max_workers=10)
        self._cache = {}
        self._cache_lock = Lock()

    def retry(
        self, 
        max_attempts: int = 3, 
        delay: float = 1.0, 
        backoff: float = 2.0,
        exceptions: tuple = (Exception,)
    ):
        """
        Decorator for retrying functions with exponential backoff
        
        :param max_attempts: Maximum number of retry attempts
        :param delay: Initial delay between retries
        :param backoff: Exponential backoff factor
        :param exceptions: Tuple of exceptions to catch and retry
        :return: Decorated function
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                current_delay = delay
                for attempt in range(1, max_attempts + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        if attempt == max_attempts:
                            raise
                        
                        self.logger.warning(
                            f"Retry attempt {attempt} for {func.__name__}: {e}"
                        )
                        
                        time.sleep(current_delay)
                        current_delay *= backoff
            return wrapper
        return decorator

    def rate_limit(
        self, 
        max_calls: int = 5, 
        period: float = 1.0
    ):
        """
        Decorator to limit function call rate
        
        :param max_calls: Maximum number of calls allowed
        :param period: Time period in seconds
        :return: Decorated function
        """
        def decorator(func):
            calls = []
            
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                current_time = time.time()
                
                # Remove old calls outside the period
                calls[:] = [call for call in calls if current_time - call < period]
                
                if len(calls) >= max_calls:
                    raise RuntimeError("Rate limit exceeded")
                
                calls.append(current_time)
                return func(*args, **kwargs)
            
            return wrapper
        return decorator

    def memoize(
        self, 
        timeout: Optional[float] = None
    ):
        """
        Decorator for caching function results
        
        :param timeout: Cache expiration time
        :return: Decorated function
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Create a hashable key from arguments
                key = str(args) + str(kwargs)
                
                with self._cache_lock:
                    # Check if result is in cache and not expired
                    if key in self._cache:
                        result, timestamp = self._cache[key]
                        
                        if timeout is None or time.time() - timestamp < timeout:
                            return result
                    
                    # Compute and cache result
                    result = func(*args, **kwargs)
                    self._cache[key] = (result, time.time())
                
                return result
            
            return wrapper
        return decorator

    def run_parallel(
        self, 
        functions: list, 
        max_workers: int = 5
    ) -> Dict[Callable, Any]:
        """
        Execute multiple functions in parallel
        
        :param functions: List of functions to execute
        :param max_workers: Maximum number of concurrent workers
        :return: Dictionary of function results
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all functions to executor
            futures = {
                executor.submit(func): func 
                for func in functions
            }
            
            # Collect results as they complete
            for future in as_completed(futures):
                func = futures[future]
                try:
                    results[func] = future.result()
                except Exception as e:
                    self.logger.error(f"Parallel execution error for {func.__name__}: {e}")
                    results[func] = None
        
        return results

    @contextmanager
    def timer(self, label: str = "Operation"):
        """
        Context manager for timing code execution
        
        :param label: Label for the timed operation
        :yield: Timing context
        """
        start_time = time.time()
        yield
        end_time = time.time()
        
        self.logger.info(f"{label} took {end_time - start_time:.4f} seconds")

    def validate_input(
        self, 
        data: Any, 
        validators: Optional[list] = None
    ) -> bool:
        """
        Validate input data against multiple validators
        
        :param data: Input data to validate
        :param validators: List of validation functions
        :return: Validation result
        """
        validators = validators or []
        
        for validator in validators:
            try:
                if not validator(data):
                    return False
            except Exception as e:
                self.logger.error(f"Validation error: {e}")
                return False
        
        return True

    def sanitize_data(
        self, 
        data: Any, 
        sanitizers: Optional[list] = None
    ) -> Any:
        """
        Sanitize input data using multiple sanitization functions
        
        :param data: Input data to sanitize
        :param sanitizers: List of sanitization functions
        :return: Sanitized data
        """
        sanitizers = sanitizers or []
        
        for sanitizer in sanitizers:
            try:
                data = sanitizer(data)
            except Exception as e:
                self.logger.error(f"Sanitization error: {e}")
                return None
        
        return data

    def log_performance(
        self, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> Any:
        """
        Performance logging decorator
        
        :param func: Function to log
        :return: Function result
        """
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        self.logger.info(
            f"Function: {func.__name__}, "
            f"Execution Time: {end_time - start_time:.4f} seconds"
        )
        
        return result

# Create a singleton instance
utils = Utilities()

# Export utility functions and class
__all__ = ['utils']
