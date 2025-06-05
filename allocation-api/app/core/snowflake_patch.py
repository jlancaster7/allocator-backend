"""Patch for Snowflake SQLAlchemy JSON handling"""

import json
from snowflake.sqlalchemy.snowdialect import SnowflakeDialect

# Add JSON deserializer to SnowflakeDialect if it doesn't exist
if not hasattr(SnowflakeDialect, '_json_deserializer'):
    SnowflakeDialect._json_deserializer = staticmethod(json.loads)

if not hasattr(SnowflakeDialect, '_json_serializer'):
    SnowflakeDialect._json_serializer = staticmethod(json.dumps)