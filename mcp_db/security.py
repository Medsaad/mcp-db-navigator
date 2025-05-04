import re
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import ssl
from functools import wraps
import time
# Import the Pydantic model
from mcp_db.db import DatabaseCredentials

logger = logging.getLogger(__name__)

class SecurityManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SecurityManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize security settings"""
        self.rate_limit = {
            'max_queries_per_minute': 100,
            'current_minute': None,
            'current_count': 0
        }
        # Keep blocked patterns for query sanitization if needed elsewhere
        self.blocked_patterns = [
            r'(?i)(?:delete|drop|truncate)\s+(?:table|database)',
            r'(?i)(?:alter|create)\s+(?:table|database|user)',
            r'(?i)execute\s+(?:procedure|function)',
            r'(?i)grant\s+|revoke\s+',
            r'(?i)system_user\(\)',
            r'(?i)super\s+privilege',
        ]

    def get_ssl_context(self, ssl_ca: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Create SSL context for secure connection"""
        if not ssl_ca:
            logger.debug("No SSL CA provided, SSL context not created.")
            return None

        try:
            ssl_ca_path = Path(ssl_ca)
            if not ssl_ca_path.is_file():
                # Log as an error, but let the connection attempt handle the failure
                logger.error(f"SSL CA file not found at path: {ssl_ca}")
                raise FileNotFoundError(f"SSL CA file not found: {ssl_ca}")

            # Configuration options for mysql.connector's SSL arguments
            ssl_options = {
                'ssl_ca': str(ssl_ca_path),
                # Add other options like ssl_cert, ssl_key, ssl_verify_cert if needed
                # 'ssl_verify_cert': True, # Often default, but can be explicit
            }
            logger.info(f"SSL context options prepared using CA: {ssl_ca}")
            return ssl_options

        except Exception as e:
            logger.error(f"Failed to prepare SSL context options: {e}", exc_info=True)
            # Propagate the error to be handled during connection attempt
            raise

    def sanitize_query(self, query: str) -> str:
        """Sanitize SQL query (basic checks for dangerous patterns)."""
        # Ensure query is a string
        if not isinstance(query, str):
            raise ValueError("Query must be a string.")

        # Remove comments (basic removal)
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL) # Handle multi-line comments
        query = re.sub(r'--.*$', '', query, flags=re.MULTILINE)
        query = re.sub(r'#.*$', '', query, flags=re.MULTILINE) # Handle hash comments

        # Check for dangerous patterns
        for pattern in self.blocked_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                logger.warning(f"Query blocked due to forbidden pattern: {pattern}")
                raise ValueError(f"Query contains forbidden pattern: {pattern}")

        # Trim whitespace
        sanitized_query = query.strip()
        if not sanitized_query:
             raise ValueError("Query cannot be empty after sanitization.")

        logger.debug("Query passed basic sanitization checks.")
        return sanitized_query

    def check_rate_limit(self) -> bool:
        """Check if current request exceeds rate limit"""
        current_time = time.time()
        current_minute = int(current_time / 60)

        if self.rate_limit['current_minute'] != current_minute:
            # Reset count for the new minute
            self.rate_limit['current_minute'] = current_minute
            self.rate_limit['current_count'] = 0
            logger.debug(f"Rate limit minute reset to {current_minute}")

        self.rate_limit['current_count'] += 1
        logger.debug(f"Rate limit count for minute {current_minute}: {self.rate_limit['current_count']}/{self.rate_limit['max_queries_per_minute']}")

        if self.rate_limit['current_count'] > self.rate_limit['max_queries_per_minute']:
            logger.warning(f"Rate limit exceeded ({self.rate_limit['current_count']}/{self.rate_limit['max_queries_per_minute']})")
            return False # Rate limit exceeded

        return True # Within rate limit

    def sanitize_connection_params(self, params: DatabaseCredentials) -> None:
        """
        Validate database connection parameters directly on the Pydantic model.
        Raises ValueError for invalid parameters.
        Note: This method modifies the validation logic to work with the model's attributes.
              It no longer returns a dict, as it validates the input model directly.
        """
        logger.debug(f"Sanitizing connection parameters for host: {params.host}, db: {params.database}")

        # Validate host (allow hostname or IP address)
        # More permissive regex: allows domain names, localhost, IPv4, IPv6
        host_pattern = r"^(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}|localhost|(?:\d{1,3}\.){3}\d{1,3}|\[?[a-fA-F0-9:]+\]?)$"
        if not re.match(host_pattern, params.host):
            logger.error(f"Invalid host format detected: {params.host}")
            raise ValueError(f"Invalid host format: {params.host}")

        # Validate port
        if not isinstance(params.port, int) or not (1 <= params.port <= 65535):
            logger.error(f"Invalid port number detected: {params.port}")
            raise ValueError(f"Invalid port number: {params.port}. Must be between 1 and 65535.")

        # Validate database name (allow alphanumeric, underscore, hyphen)
        db_name_pattern = r'^[a-zA-Z0-9_-]+$'
        if not re.match(db_name_pattern, params.database):
            logger.error(f"Invalid database name format detected: {params.database}")
            raise ValueError(f"Invalid database name format: {params.database}. Use alphanumeric, underscore, or hyphen.")

        # Validate username (similar to database name)
        username_pattern = r'^[a-zA-Z0-9_@.-]+$' # Allow more chars often used in usernames
        if not re.match(username_pattern, params.username):
             logger.error(f"Invalid username format detected: {params.username}")
             raise ValueError(f"Invalid username format: {params.username}")

        # Validate password (check if it's set - Pydantic handles SecretStr)
        if not params.password or not params.password.get_secret_value():
             logger.error("Database password is required but not provided.")
             raise ValueError("Database password is required.")

        # Validate SSL CA path if provided
        if params.ssl_ca:
            ssl_ca_path = Path(params.ssl_ca)
            if not ssl_ca_path.is_file():
                # Log as warning, connection will fail later if file is truly needed and missing
                logger.warning(f"Provided SSL CA path does not point to a file: {params.ssl_ca}")
                # Optionally raise ValueError here if SSL is mandatory and file must exist
                # raise ValueError(f"SSL CA file not found at path: {params.ssl_ca}")

        # Validate retries and delay
        if not isinstance(params.max_retries, int) or params.max_retries < 0:
             logger.error(f"Invalid max_retries value: {params.max_retries}")
             raise ValueError("max_retries must be a non-negative integer.")
        if not isinstance(params.retry_delay, (int, float)) or params.retry_delay < 0:
             logger.error(f"Invalid retry_delay value: {params.retry_delay}")
             raise ValueError("retry_delay must be a non-negative number.")

        logger.debug("Connection parameters passed validation.")
        # No need to return anything as we are validating the passed object.


def enforce_security(func):
    """Decorator to enforce security measures like rate limiting and query sanitization."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get the SecurityManager instance
        # Assumes SecurityManager is initialized elsewhere (e.g., in main.py)
        # If not, might need a way to access the instance created in main.py
        # For simplicity here, we re-create it, but a shared instance is better.
        security_manager = SecurityManager() # Or access a shared instance

        # --- Check Rate Limit ---
        if not security_manager.check_rate_limit():
            # Raise an exception that the handle_error decorator can catch
            raise Exception("Rate limit exceeded. Please try again later.") # Or a custom RateLimitError

        # --- Sanitize Query (if applicable) ---
        # Check if 'query' or 'query_params' exists in kwargs and needs sanitization
        # This part depends on which tool is being decorated and its arguments.
        # Example: If decorating query_database which takes query_params dict
        if func.__name__ == 'query_database' and 'query_params' in kwargs:
             # This example assumes the raw SQL isn't passed directly.
             # If a raw SQL string *was* passed (which is discouraged), sanitize it:
             # if 'raw_sql_query' in kwargs:
             #    kwargs['raw_sql_query'] = security_manager.sanitize_query(kwargs['raw_sql_query'])
             # Since we build parameterized queries, direct SQL sanitization might not be needed here,
             # but validation of inputs (table names, field names) within query_database is crucial.
             logger.debug(f"Security checks passed for {func.__name__}.") # Placeholder log
             pass # Parameterized queries handle SQL injection risk

        # Execute the original function
        return func(*args, **kwargs)

    # Preserve original function signature for MCP introspection
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    wrapper.__annotations__ = func.__annotations__
    return wrapper
