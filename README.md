# MySQL Navigator MCP

A powerful MySQL/MariaDB database navigation tool using MCP (Model Control Protocol) for easy database querying and management.

## Features

- Connect to MySQL/MariaDB databases
- Execute SQL queries with type safety
- Pydantic model validation for query parameters
- Environment variable configuration
- Secure credential management

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd mysql-navigator-mcp
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with your database credentials:
```env
DB_HOST=your_host
DB_PORT=your_port
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password
```

## Usage

1. Start the MCP server:
```bash
python main.py
```

2. Use the following query structure for database operations:
```python
query = {
    "table_name": "your_table",
    "select_fields": ["*"],
    "where_conditions": {"column": "value"},
    "order_by": ["column_name"],
    "order_direction": "ASC",
    "limit": 10
}
```

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

## Security

- Database credentials are managed through environment variables
- Passwords are stored as SecretStr in Pydantic models
- Input validation for all query parameters
- SQL injection prevention through parameterized queries

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 