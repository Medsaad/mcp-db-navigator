# MySQL Navigator MCP

A powerful MySQL/MariaDB database navigation tool using MCP (Model Control Protocol) for easy database querying and management.

## Features

- Connect to MySQL/MariaDB databases
- Switch between different databases dynamically
- Execute SQL queries with type safety
- Retrieve database schema information
- Pydantic model validation for query parameters
- Secure credential management
- Comprehensive logging system
- Connection pooling and retry mechanisms
- SSL/TLS support for secure connections

## Log File Location (Cross-Platform)

By default, all logs are written to:

- **Windows:** `C:\Users\<YourUsername>\.mcp\mcp-db.log`
- **macOS/Linux:** `/home/<yourusername>/.mcp/mcp-db.log` or `/Users/<yourusername>/.mcp/mcp-db.log`

If the `.mcp` folder does not exist in your home directory, the application will automatically create it. If you run into any issues, you can manually create the folder:

**Windows:**
```powershell
mkdir $env:USERPROFILE\.mcp
```
**macOS/Linux:**
```bash
mkdir -p ~/.mcp
```

## Installation

### From PyPI (recommended for most users):
```bash
pip install mcp-db-navigator
```

### From source (for development):
```bash
git clone <your-repo-url>
cd mcp-db
pip install -e .
```

3. Create a `.env` file with your database credentials:
```env
DB_HOST=your_host
DB_PORT=your_port
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password
DB_SSL_CA=/path/to/ssl/ca.pem  # Optional: for SSL/TLS connections
DB_MAX_RETRIES=3  # Optional: number of connection retries
DB_RETRY_DELAY=1.0  # Optional: delay between retries in seconds
```

## Usage Examples

### 1. Command Line
Run the MCP server directly from your terminal:
```bash
mcp-db --config /path/to/your/project/.env
```

### 2. In Cursor
To use this MCP server in [Cursor](https://www.cursor.so):
- Open Cursor settings and add a new MCP server.
- Use the following configuration (example):

```json
{
  "mcpServers": {
    "mysql-navigator": {
      "command": "mcp-db",
      "args": [
        "--config",
        "/absolute/path/to/your/.env"
      ]
    }
  }
}
```
- Make sure the path to your `.env` file is absolute.

### 3. In Claude Desktop
If Claude Desktop supports MCP servers:
- Add a new MCP server and point it to the `mcp-db` command with the `--config` argument as above.
- Refer to Claude Desktop's documentation for details on adding custom MCP servers.

## Query Parameters

The query dictionary supports the following parameters:

- `table_name` (required): Name of the table to query
- `select_fields` (optional): List of fields to select (defaults to ["*"])
- `where_conditions` (optional): Dictionary of field-value pairs for WHERE clause
- `order_by` (optional): List of fields to order by
- `order_direction` (optional): Sort direction "ASC" or "DESC" (default: "ASC")
- `limit` (optional): Number of records to return
- `offset` (optional): Number of records to skip
- `group_by` (optional): List of fields to group by
- `having` (optional): Dictionary of field-value pairs for HAVING clause
- `join_table` (optional): Name of the table to join with
- `join_type` (optional): Type of JOIN operation (default: "INNER")
- `join_conditions` (optional): Dictionary of join conditions

## Security Features

- Database credentials are managed through a config file
- Passwords are stored as SecretStr in Pydantic models
- Input validation for all query parameters
- SQL injection prevention through parameterized queries
- SSL/TLS support for encrypted connections
- Connection string sanitization
- Rate limiting for queries
- Query parameter sanitization

## Production Features

### Error Handling
- Comprehensive error handling for database operations
- Connection timeout handling
- Automatic retry mechanism for failed connections
- Input validation for all parameters

### Performance
- Connection pooling for optimal resource usage
- Query execution time logging
- Connection pool statistics
- Performance metrics collection

### Monitoring
- Structured logging with different log levels
- Query execution tracking
- Connection state monitoring
- Error rate tracking

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 