from pydantic import BaseModel, Field, SecretStr, field_validator
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class DatabaseCredentials(BaseModel):
    """Pydantic model for database credentials"""
    host: str = Field(default="localhost", description="Database host address")
    port: int = Field(default=3306, description="Database port number")
    database: str = Field(..., description="Database name")
    username: str = Field(..., description="Database username")
    password: SecretStr = Field(..., description="Database password")
    ssl_ca: Optional[str] = Field(default=None, description="SSL CA certificate")
    max_retries: int = Field(default=3, description="Maximum number of retries")
    retry_delay: float = Field(default=1.0, description="Retry delay in seconds")
    

class SelectQuery(BaseModel):
    """Pydantic model for SELECT query elements"""
    select_fields: List[str] = Field(
        default=["*"],
        description="List of fields to select"
    )
    table_name: str = Field(
        ...,
        description="Name of the table to query from"
    )
    where_conditions: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Dictionary of field-value pairs for WHERE clause"
    )
    order_by: Optional[List[str]] = Field(
        default=None,
        description="List of fields to order by"
    )
    order_direction: str = Field(
        default="ASC",
        description="Sort direction (ASC or DESC)",
        pattern="^(ASC|DESC)$"
    )
    limit: Optional[int] = Field(
        default=None,
        description="Number of records to return",
        ge=1,
        le=100
    )
    offset: Optional[int] = Field(
        default=None,
        description="Number of records to skip",
        ge=0
    )
    group_by: Optional[List[str]] = Field(
        default=None,
        description="List of fields to group by"
    )
    having: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Dictionary of field-value pairs for HAVING clause"
    )
    join_table: Optional[str] = Field(
        default=None,
        description="Name of the table to join with"
    )
    join_type: str = Field(
        default="INNER",
        description="Type of JOIN operation",
        pattern="^(INNER|LEFT|RIGHT|FULL)$"
    )
    join_conditions: Optional[List[str]] = Field(
        default=None,
        description="List of join conditions (field pairs)"
    )

    @field_validator('table_name')
    def table_name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('table_name cannot be empty')
        return v.strip()

    @field_validator('select_fields')
    def select_fields_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('select_fields cannot be empty')
        return v

    @field_validator('where_conditions')
    def validate_where_conditions(cls, v):
        if v is not None:
            for key, value in v.items():
                if not key or not key.strip():
                    raise ValueError('where_conditions keys cannot be empty')
                if value is None:
                    raise ValueError('where_conditions values cannot be None')
        return v

    class Config:
        arbitrary_types_allowed = True
