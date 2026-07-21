"""
MySQL adapter module.
Provides MySQL-specific connection management using PyMySQL.
Used when DB_MODE=mysql in .env configuration.

This module demonstrates INSERT ... ON DUPLICATE KEY UPDATE
and other MySQL-specific features referenced in sql/ files.
"""
import json
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

try:
    import pymysql
    import pymysql.cursors
    PYMYSQL_AVAILABLE = True
except ImportError:
    PYMYSQL_AVAILABLE = False
    logger.info("PyMySQL not installed. MySQL mode unavailable.")


class MySQLAdapter:
    """
    MySQL-specific database adapter.
    Mirrors DatabaseManager's interface but uses PyMySQL and MySQL syntax.
    """

    def __init__(self, host, port, user, password, database):
        if not PYMYSQL_AVAILABLE:
            raise ImportError(
                "PyMySQL is required for MySQL mode. "
                "Install with: pip install pymysql"
            )
        self.connection_config = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
            "charset": "utf8mb4",
            "cursorclass": pymysql.cursors.DictCursor,
        }

    @contextmanager
    def get_connection(self):
        """Context manager for MySQL connections."""
        conn = pymysql.connect(**self.connection_config)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def upsert_product(self, sku, name, category_id, attributes_json,
                       source_competitor_id):
        """
        MySQL-specific upsert using INSERT ... ON DUPLICATE KEY UPDATE.
        Uses JSON_MERGE_PATCH to merge JSON attributes.
        """
        query = """
            INSERT INTO products (sku, name, category_id, attributes, source_competitor_id)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                attributes = JSON_MERGE_PATCH(
                    COALESCE(attributes, '{}'),
                    VALUES(attributes)
                ),
                source_competitor_id = VALUES(source_competitor_id),
                updated_at = CURRENT_TIMESTAMP
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    query,
                    (sku, name, category_id, attributes_json,
                     source_competitor_id)
                )
                # Return the product ID
                if cursor.lastrowid:
                    return cursor.lastrowid
                # If updated, fetch the existing ID
                cursor.execute(
                    "SELECT id FROM products WHERE sku = %s", (sku,)
                )
                row = cursor.fetchone()
                return row["id"] if row else None

    def insert_price_with_upsert(self, product_id, competitor_id, price,
                                  currency="USD", in_stock=True):
        """
        MySQL-specific price insert with ON DUPLICATE KEY UPDATE.
        Updates price if a record already exists for the same timestamp.
        """
        query = """
            INSERT INTO price_history
                (product_id, competitor_id, price, currency, in_stock)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                price = VALUES(price),
                in_stock = VALUES(in_stock)
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    query,
                    (product_id, competitor_id, price, currency, int(in_stock))
                )

    def query_json_attributes(self, attribute_path: str, value: str):
        """
        Query products using MySQL JSON operators.
        Example: query_json_attributes('$.brand', 'Apple')
        """
        query = """
            SELECT id, sku, name, attributes->>%s AS attr_value
            FROM products
            WHERE attributes->>%s = %s
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (attribute_path, attribute_path, value))
                return cursor.fetchall()

    def get_products_with_json_table(self):
        """
        Demonstrate JSON_TABLE to flatten nested product attributes
        into relational rows.
        """
        query = """
            SELECT p.id, p.name, specs.*
            FROM products p,
            JSON_TABLE(p.attributes, '$' COLUMNS (
                brand VARCHAR(100) PATH '$.brand',
                weight_g DECIMAL(10,2) PATH '$.weight_g',
                rating_score DECIMAL(3,1) PATH '$.rating_score',
                review_count INT PATH '$.review_count'
            )) AS specs
            WHERE p.attributes IS NOT NULL
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                return cursor.fetchall()
