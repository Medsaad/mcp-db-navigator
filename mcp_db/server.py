# --- Standard Library Imports ---
import sys
import logging
import json
import re
from pathlib import Path
from typing import Dict, Optional
import argparse

# --- Third-party Library Imports ---
from mysql.connector import Error
from mcp.server.fastmcp import FastMCP

# --- Local Application/Library Specific Imports ---
from mcp_db.db import DatabaseCredentials
from mcp_db.connection_pool import ConnectionPool
from mcp_db.security import SecurityManager, enforce_security
from mcp_db.metrics import MetricsTracker, track_query_metrics

# ==============================================================================
# Logging Configuration
# ==============================================================================
log_dir = Path.home() / ".mcp"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "mcp-db.log"
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout), # Log to console
        logging.FileHandler(log_file, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ==============================================================================
# Custom Error Class
# ==============================================================================
class MCPError(Exception):
    """Custom exception class for MCP-specific errors."""
    def __init__(self, message: str, details: Optional[Dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict:
        return {"error": self.message, "details": self.details}

# ==============================================================================
# Error Handling Decorator
# ==============================================================================
def handle_error(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except MCPError as e:
            logger.error(f"MCP Error in {func.__name__}: {e.message}", exc_info=False)
            logger.debug(f"MCP Error Details: {e.details}")
            try:
                return json.dumps(e.to_dict())
            except Exception as serialization_error:
                logger.critical(f"Failed to serialize MCPError: {serialization_error}", exc_info=True)
                return json.dumps({"error": "Internal Server Error: Failed to report specific error."})
        except Error as db_error:
            logger.error(f"Database Error in {func.__name__}: {db_error}", exc_info=True)
            error_dict = {
                "error": f"Database operation failed: {db_error.msg}",
                "details": {
                    "type": type(db_error).__name__,
                    "errno": db_error.errno,
                    "sqlstate": db_error.sqlstate,
                }
            }
            try:
                return json.dumps(error_dict)
            except Exception as serialization_error:
                logger.critical(f"Failed to serialize Database Error details: {serialization_error}", exc_info=True)
                return json.dumps({"error": "Internal Server Error: Failed to report database error details."})
        except Exception as e:
            logger.error(f"Unexpected Error in {func.__name__}: {e}", exc_info=True)
            error_dict = {
                "error": "An unexpected internal server error occurred.",
                "details": {
                    "type": type(e).__name__,
                    "message": str(e),
                }
            }
            try:
                return json.dumps(error_dict)
            except Exception as serialization_error:
                logger.critical(f"CRITICAL: Failed to serialize unexpected error details: {serialization_error}", exc_info=True)
                return json.dumps({"error": "Internal Server Error: Failed to report error details."})
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    wrapper.__annotations__ = func.__annotations__
    return wrapper

# ==============================================================================
# Environment Loading
# ==============================================================================
def load_env_file(env_path: str) -> Dict[str, str]:
    if not env_path:
        logger.critical("No .env file path provided. Use --env to specify the path.")
        raise MCPError("Configuration Error: .env file path is required.")
    env_file = Path(env_path)
    if not env_file.is_file():
        logger.critical(f".env file not found at specified path: {env_path}")
        raise MCPError(f"Configuration Error: .env file not found at {env_path}")
    env_vars = {}
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            env_vars[key.strip()] = value.strip()
    logger.info(f"Successfully loaded environment variables from {env_path}")
    return env_vars

# ==============================================================================
# Main Application Setup
# ==============================================================================
def run_server(env_file_path: str):
    try:
        env_vars = load_env_file(env_file_path)
        logger.info("Initializing MCP server...")
        mcp = FastMCP(
            "MySQL Navigator MCP",
            description="A powerful MySQL/MariaDB database navigation tool using MCP.",
            version="1.0.0"
        )
        logger.info("MCP server framework initialized.")
        pool = ConnectionPool()
        security_manager = SecurityManager()
        metrics = MetricsTracker()
        logger.info("Core services (Connection Pool, Security, Metrics) initialized.")
        try:
            db_port = env_vars.get("DB_PORT")
            db_credentials = DatabaseCredentials(
                host=env_vars.get("DB_HOST", "localhost"),
                port=int(db_port) if db_port and db_port.isdigit() else 3306,
                database=env_vars.get("DB_NAME"),
                username=env_vars.get("DB_USER"),
                password=env_vars.get("DB_PASSWORD"),
                ssl_ca=env_vars.get("DB_SSL_CA"),
                max_retries=int(env_vars.get("DB_MAX_RETRIES", "3")),
                retry_delay=float(env_vars.get("DB_RETRY_DELAY", "1.0"))
            )
            security_manager.sanitize_connection_params(db_credentials)
            logger.info(f"Database credentials loaded and validated for initial database: {db_credentials.database}")
        except Exception as e:
            logger.critical(f"Failed to load or validate initial database credentials from environment: {e}", exc_info=True)
            raise MCPError(f"Configuration Error: Invalid database credentials in .env: {e}")
        try:
            pool.initialize_pool(db_credentials)
            logger.info(f"Connection pool initialized for database: {db_credentials.database}")
        except Exception as e:
            logger.critical(f"Failed to initialize connection pool: {e}", exc_info=True)
            raise MCPError(f"Initialization Error: Could not establish initial database connection pool: {e}")

        # MCP Tool Definitions
        @mcp.tool()
        @handle_error
        def connect_to_database() -> str:
            global db_credentials
            logger.info(f"Attempting to connect/verify connection to database: {db_credentials.database}")
            try:
                pool.close_all()
                pool.initialize_pool(db_credentials)
                conn = pool.get_connection()
                conn.ping(reconnect=True, attempts=1, delay=0)
                conn.close()
                logger.info(f"Successfully connected/verified connection to database: {db_credentials.database}")
                status = {"status": "connected", "database": db_credentials.database, "host": db_credentials.host}
                return json.dumps(status)
            except Error as db_err:
                logger.error(f"Database connection/verification failed: {db_err}", exc_info=True)
                raise MCPError(f"Failed to connect to database '{db_credentials.database}'", {"details": str(db_err), "errno": db_err.errno})
            except Exception as e:
                logger.error(f"Unexpected error during connect_to_database: {e}", exc_info=True)
                raise MCPError("Failed to connect to database due to an unexpected error.", {"details": str(e)})

        @mcp.tool()
        @handle_error
        def switch_database(database: str) -> str:
            global db_credentials
            logger.info(f"Attempting to switch database connection to: {database}")
            if not database or not isinstance(database, str):
                raise MCPError("Invalid input: 'database' parameter must be a non-empty string.")
            try:
                new_credentials = DatabaseCredentials(
                    host=db_credentials.host,
                    port=db_credentials.port,
                    database=database.strip(),
                    username=db_credentials.username,
                    password=db_credentials.password,
                    ssl_ca=db_credentials.ssl_ca,
                    max_retries=db_credentials.max_retries,
                    retry_delay=db_credentials.retry_delay
                )
                security_manager.sanitize_connection_params(new_credentials)
                pool.close_all()
                pool.initialize_pool(new_credentials)
                conn = pool.get_connection()
                conn.ping(reconnect=True, attempts=1, delay=0)
                conn.close()
                db_credentials = new_credentials
                logger.info(f"Successfully switched connection pool to database: {database}")
                status = {"status": "switched", "database": database, "host": db_credentials.host}
                return json.dumps(status)
            except Error as db_err:
                logger.error(f"Failed to switch to database '{database}': {db_err}", exc_info=True)
                raise MCPError(f"Failed to switch to database '{database}'", {"details": str(db_err), "errno": db_err.errno})
            except Exception as e:
                logger.error(f"Unexpected error during switch_database: {e}", exc_info=True)
                raise MCPError(f"Failed to switch database due to an unexpected error.", {"details": str(e)})

        @mcp.tool()
        @handle_error
        @enforce_security
        def load_database_schema() -> str:
            logger.info(f"Loading schema for database: {db_credentials.database}")
            connection = None
            try:
                connection = pool.get_connection()
                cursor = connection.cursor()
                cursor.execute("SHOW TABLES")
                tables = [table[0] for table in cursor.fetchall()]
                logger.debug(f"Found tables: {tables}")
                schema = {}
                for table_name in tables:
                    if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
                        logger.warning(f"Skipping potentially unsafe table name for DESCRIBE: {table_name}")
                        continue
                    cursor.execute(f"DESCRIBE `{table_name}`")
                    columns = cursor.fetchall()
                    schema[table_name] = [{"name": col[0], "type": col[1]} for col in columns]
                    logger.debug(f"Schema for table '{table_name}': {schema[table_name]}")
                logger.info(f"Successfully loaded schema for {len(schema)} tables.")
                return json.dumps({"schema": schema})
            except Error as db_err:
                logger.error(f"Error getting database schema: {db_err}", exc_info=True)
                raise MCPError("Error getting database schema", {"details": str(db_err), "errno": db_err.errno})
            except Exception as e:
                logger.error(f"Unexpected error loading schema: {e}", exc_info=True)
                raise MCPError("Unexpected error loading schema.", {"details": str(e)})
            finally:
                if connection and connection.is_connected():
                    cursor.close()
                    connection.close()
                    logger.debug("Database connection closed after loading schema.")

        @mcp.tool()
        @handle_error
        @enforce_security
        @track_query_metrics
        def query_database(query_params: dict) -> str:
            logger.info(f"Received query request for database: {db_credentials.database}")
            logger.debug(f"Query parameters received: {query_params}")
            connection = None
            try:
                table_name = query_params.get("table_name")
                if not table_name or not isinstance(table_name, str) or not re.match(r'^[a-zA-Z0-9_]+$', table_name):
                    raise MCPError("Invalid or missing 'table_name'. Must be alphanumeric/underscore.")
                select_fields_input = query_params.get("select_fields", ["*"])
                if not isinstance(select_fields_input, list) or not select_fields_input:
                    raise MCPError("'select_fields' must be a non-empty list.")
                select_fields = []
                for field in select_fields_input:
                    if field == "*":
                        select_fields.append("*")
                    elif isinstance(field, str) and re.match(r'^[a-zA-Z0-9_]+$', field):
                        select_fields.append(f"`{field}`")
                    else:
                        raise MCPError(f"Invalid character in select field: {field}")
                select_clause = ", ".join(select_fields)
                where_conditions = query_params.get("where_conditions")
                order_by_input = query_params.get("order_by")
                order_direction_input = query_params.get("order_direction", "ASC").upper()
                limit_input = query_params.get("limit")
                offset_input = query_params.get("offset")
                query_parts = [f"SELECT {select_clause} FROM `{table_name}`"]
                parameters = []
                if isinstance(where_conditions, dict) and where_conditions:
                    where_clauses = []
                    for key, value in where_conditions.items():
                        if not isinstance(key, str) or not re.match(r'^[a-zA-Z0-9_]+$', key):
                            raise MCPError(f"Invalid character in where condition key: {key}")
                        where_clauses.append(f"`{key}` = %s")
                        parameters.append(value)
                    if where_clauses:
                        query_parts.append("WHERE " + " AND ".join(where_clauses))
                if isinstance(order_by_input, list) and order_by_input:
                    order_by_clauses = []
                    for field in order_by_input:
                        if not isinstance(field, str) or not re.match(r'^[a-zA-Z0-9_]+$', field):
                            raise MCPError(f"Invalid character in order_by field: {field}")
                        order_by_clauses.append(f"`{field}`")
                    if order_by_clauses:
                        if order_direction_input not in ["ASC", "DESC"]:
                            raise MCPError("Invalid 'order_direction'. Must be 'ASC' or 'DESC'.")
                        query_parts.append(f"ORDER BY {', '.join(order_by_clauses)} {order_direction_input}")
                effective_limit = 100
                if limit_input is not None:
                    try:
                        limit_val = int(limit_input)
                        if limit_val < 1:
                            raise MCPError("'limit' must be a positive integer.")
                        effective_limit = min(limit_val, 500)
                    except (ValueError, TypeError):
                        raise MCPError("'limit' must be an integer.")
                query_parts.append("LIMIT %s")
                parameters.append(effective_limit)
                if offset_input is not None:
                    try:
                        offset_val = int(offset_input)
                        if offset_val < 0:
                            raise MCPError("'offset' must be a non-negative integer.")
                        query_parts.append("OFFSET %s")
                        parameters.append(offset_val)
                    except (ValueError, TypeError):
                        raise MCPError("'offset' must be an integer.")
                final_query = " ".join(query_parts)
                logger.info(f"Executing parameterized query: {final_query}")
                logger.debug(f"Parameters: {tuple(parameters)}")
                connection = pool.get_connection()
                cursor = connection.cursor(dictionary=True)
                cursor.execute(final_query, tuple(parameters))
                results = cursor.fetchall()
                logger.info(f"Query executed successfully. Retrieved {len(results)} rows.")
                return json.dumps({"results": results, "row_count": len(results)})
            except Error as db_err:
                logger.error(f"Database query execution failed: {db_err}", exc_info=True)
                raise MCPError(f"Database query failed: {db_err.msg}", {"details": str(db_err), "errno": db_err.errno, "sqlstate": db_err.sqlstate})
            except MCPError:
                raise
            except Exception as e:
                logger.error(f"Unexpected error during query execution: {e}", exc_info=True)
                raise MCPError("An unexpected error occurred while executing the query.", {"details": str(e)})
            finally:
                if connection and connection.is_connected():
                    if 'cursor' in locals() and cursor:
                        cursor.close()
                    connection.close()
                    logger.debug("Database connection closed after query.")

        logger.info("Starting MySQL Navigator MCP...")
        try:
            if pool._pool is None:
                logger.critical("Connection pool not available. Aborting server start.")
                sys.exit("Error: Database connection pool failed to initialize.")
            logger.info("MCP server setup complete. Ready to accept connections.")
            mcp.run()
        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt (Ctrl+C). Initiating shutdown...")
        except MCPError as e:
            logger.critical(f"MCP Initialization Error: {e.message} - Details: {e.details}")
            sys.exit(f"Error: {e.message}")
        except Exception as e:
            logger.critical(f"Failed to start MCP server: {e}", exc_info=True)
            sys.exit(f"Error: Failed to start server - {e}")
        finally:
            logger.info("Initiating server shutdown sequence...")
            if 'pool' in locals() and pool:
                pool.close_all()
                logger.info("Database connection pool closed.")
            else:
                logger.warning("Connection pool object not found during shutdown.")
            logger.info("MySQL Navigator MCP server shutdown complete.")
    except Exception as e:
        logger.critical(f"A critical error occurred outside the main execution block: {e}", exc_info=True)
        sys.exit(f"Critical Error: {e}")

def main_cli():
    parser = argparse.ArgumentParser(description="MySQL Navigator MCP Server")
    parser.add_argument('--config', type=str, required=True, help="Path to .env file with DB credentials")
    args = parser.parse_args()
    run_server(args.config)