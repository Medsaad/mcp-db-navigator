from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import os
from db import DatabaseCredentials, SelectQuery
import mysql.connector
from mysql.connector import Error
from typing import List, Tuple, Any
import logging
import sys

# Create a logger for this module
logger = logging.getLogger(__name__)

"""
NEXT STEPS:
resource: https://www.youtube.com/watch?v=fJgFZRGO9AQ
- Upload to github
- Add it to Glama
- Add it to Cursor Directory
"""

load_dotenv()

mcp = FastMCP("MySQL Navigator MCP")
database_connection = None


def connect_db(connection_data: DatabaseCredentials) -> mysql.connector.connection.MySQLConnection:
    try:
        connection = mysql.connector.connect(
            host=connection_data.host,
            port=connection_data.port,
            database=connection_data.database,
            user=connection_data.username,
            password=connection_data.password.get_secret_value(),
        )
        
        if connection.is_connected():
            db_info = connection.server_info
            logger.info(f"Connected to MySQL Server version {db_info}")
            global database_connection
            database_connection = connection
            
    except Error as e:
        logger.error(f"Error connecting to MySQL Database: {e}")
        raise Error(f"Error connecting to MySQL Database: {e}")
    
    return database_connection

@mcp.tool()
def connect_to_database() -> mysql.connector.connection.MySQLConnection:
    """Connect to a mysql or mariadb database

    Returns:
        The connection object that can be used to query the database
    """
    port = os.getenv("DB_PORT")
    if port is not None:
        port = int(port)
    else:
        port = 3306

    connection_data = DatabaseCredentials(
        host=os.getenv("DB_HOST"),
        port=port,
        database=os.getenv("DB_NAME"),
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

    return connect_db(connection_data)

@mcp.tool()
def switch_database(database: str) -> mysql.connector.connection.MySQLConnection:
    """Switch to a different mysql or mariadb database
    Args:
        database: the name of the database to switch to

    Returns:
        The connection object that can be used to query the database
    """
    port = os.getenv("DB_PORT")
    if port is not None:
        port = int(port)
    else:
        port = 3306

    connection_data = DatabaseCredentials(
        host=os.getenv("DB_HOST"),
        port=port,
        database=database,
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

    return connect_db(connection_data)
        

@mcp.tool()
def load_database_schema() -> dict:
    """Get the database schema
    """
    try:
        cursor = database_connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        schema = {}
        for table in tables:
            table_name = table[0]
            cursor.execute(f"describe {table_name}")
            columns = cursor.fetchall()
            schema[table_name] = [column[0] for column in columns]
        return schema
    except Error as e:
        logger.error(f"Error getting database schema: {e}")
        raise Error(f"Error getting database schema: {e}")

def build_query(query: SelectQuery) -> str:
    query_str = "SELECT " + ", ".join(query.select_fields) + " FROM " + query.table_name
    
    if query.join_table:
        if query.join_type:
            query_str += " " + query.join_type
        query_str += " JOIN " + query.join_table
        if query.join_conditions:
            query_str += " ON " + " AND ".join(query.join_conditions)

    if query.where_conditions:
        where_conditions = []
        for k, v in query.where_conditions.items():
            if str(v).replace('.', '').isdigit():
                where_conditions.append(f"{k} = {v}")
            else:
                where_conditions.append(f"{k} = '{v}'")
        query_str += " WHERE " + " AND ".join(where_conditions)
    
    if query.order_by:
        query_str += " ORDER BY " + ", ".join(query.order_by)
        if query.order_direction:
            query_str += " " + query.order_direction
    
    if query.limit:
        query_str += " LIMIT " + str(query.limit)
    
    if query.offset:
        query_str += " OFFSET " + str(query.offset)
    
    if query.group_by:
        query_str += " GROUP BY " + ", ".join(query.group_by)
    
    logger.info(f"Executing query: {query_str}")
    return query_str

@mcp.tool()
def query_database(query: dict) -> List[Tuple[Any, ...]]:
    """Query the database using a query dictionary
    
    Args:
        query: A dictionary containing:
            - select_fields: List of fields to select (default: ["*"])
            - table_name: Name of the table to query from (required)
            - where_conditions: Dictionary of field-value pairs for WHERE clause (optional)
            - order_by: List of fields to order by (optional)
            - order_direction: Sort direction "ASC" or "DESC" (default: "ASC")
            - limit: Number of records to return (optional)
            - offset: Number of records to skip (optional)
            - group_by: List of fields to group by (optional)
            - having: Dictionary of field-value pairs for HAVING clause (optional)
            - join_table: Name of the table to join with (optional)
            - join_type: Type of JOIN operation (default: "INNER")
            - join_conditions: Dictionary of join conditions (optional)
        
    Returns:
        The result of the query as a list of tuples
    """
    try:
        # Convert dictionary to SelectQuery object
        """
        TODO
        - Load database schema before running query
        - Add a tool to get the database schema
        """
        select_query = SelectQuery(**query)
        
        global database_connection
        if database_connection is None:
            logger.info("No database connection found. Establishing new connection...")
            database_connection = connect_to_database()
        
        cursor = database_connection.cursor()
        query_str = build_query(select_query)
        cursor.execute(query_str)
        results = cursor.fetchall()
        logger.info(f"Query executed successfully. Retrieved {len(results)} rows.")
        return results
    except Exception as e:
        logger.error(f"Error executing query: {str(e)}")
        raise ValueError(f"Error executing query: {str(e)}")

if __name__ == "__main__":
    # Configure logging only when run as a script
    logging.basicConfig(
        level=logging.INFO,
    
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logger.info("Starting MySQL Navigator MCP...")
    try:
        mcp.run()
    except Exception as e:
        logger.error(f"Failed to start MCP: {e}")
        sys.exit(1)