from mysql.connector import pooling, Error
import logging
from typing import Any
from mcp_db.db import DatabaseCredentials
from mcp_db.security import SecurityManager

logger = logging.getLogger(__name__)

class ConnectionPool:
    _instance = None
    _pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConnectionPool, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.pool_name = "mysql_pool"
        self.pool_size = 5
        self.security_manager = SecurityManager()
        
    def initialize_pool(self, credentials: DatabaseCredentials) -> None:
        """Initialize the connection pool with given credentials"""
        if self._pool is not None:
            logger.warning("Pool already initialized")
            return
            
        try:
            # Get SSL context if SSL CA is provided
            ssl_context = self.security_manager.get_ssl_context(credentials.ssl_ca)
            
            pool_config = {
                "pool_name": self.pool_name,
                "pool_size": self.pool_size,
                "host": credentials.host,
                "port": credentials.port,
                "database": credentials.database,
                "user": credentials.username,
                "password": credentials.password.get_secret_value(),
                "connect_timeout": 10,  # 10 seconds timeout
                "use_pure": True,  # Use pure Python implementation
            }
            
            # Add SSL configuration if available
            if ssl_context:
                pool_config.update(ssl_context)
                logger.info("SSL/TLS connection enabled")
            
            # Remove None values
            pool_config = {k: v for k, v in pool_config.items() if v is not None}
            
            self._pool = pooling.MySQLConnectionPool(**pool_config)
            logger.info(f"Connection pool initialized with size {self.pool_size}")
            
        except Error as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise
            
    def get_connection(self) -> Any:
        """Get a connection from the pool"""
        if self._pool is None:
            raise RuntimeError("Pool not initialized. Call initialize_pool first.")
            
        try:
            connection = self._pool.get_connection()
            logger.debug("Retrieved connection from pool")
            return connection
        except Error as e:
            logger.error(f"Failed to get connection from pool: {e}")
            raise
            
    def close_all(self) -> None:
        """Close all connections in the pool"""
        if self._pool is not None:
            try:
                # Close all connections
                self._pool._remove_connections()
                logger.info("All connections in pool closed")
            except Error as e:
                logger.error(f"Error closing pool connections: {e}")
                raise
            finally:
                self._pool = None 