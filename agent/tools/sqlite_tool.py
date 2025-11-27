"""Enhanced SQLite database tool with better schema introspection and error handling."""
import sqlite3
import re
from typing import Dict, List, Any, Optional
from pathlib import Path


class SQLiteTool:
    """Enhanced SQLite tool with robust query execution and schema analysis."""
    
    def __init__(self, db_path: str = "data/northwind.sqlite"):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        self._schema_cache = None
        self._date_format_cache = None
        self._detect_date_format()
    
    def _detect_date_format(self):
        """Detect the date format used in the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT OrderDate FROM Orders LIMIT 1")
            sample_date = cursor.fetchone()
            conn.close()
            
            if sample_date:
                date_str = sample_date[0]
                # Check if format is YYYY-MM-DD or includes time
                if 'T' in date_str or ' ' in date_str:
                    self._date_format_cache = 'datetime'
                else:
                    self._date_format_cache = 'date'
        except:
            self._date_format_cache = 'date'
    
    def get_schema(self) -> str:
        """Get comprehensive schema description for the database."""
        if self._schema_cache:
            return self._schema_cache    
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        
        schema_parts = [
            "Database Schema:",
            "",
            "IMPORTANT NOTES:",
            "- Use 'Order Details' table name in quotes: \"Order Details\"",
            "- Date format: YYYY-MM-DD (use strftime or date functions)",
            "- Revenue formula: SUM(UnitPrice * Quantity * (1 - Discount))",
            "- For date filtering: Use date(OrderDate) or strftime('%Y-%m-%d', OrderDate)",
            ""
        ]
        
        for table in tables:
            # Get table info
            cursor.execute(f"PRAGMA table_info('{table}')")
            columns = cursor.fetchall()
            
            schema_parts.append(f"\nTable: {table}")
            schema_parts.append("Columns:")
            for col in columns:
                col_name, col_type = col[1], col[2]
                pk = " (PRIMARY KEY)" if col[3] else ""
                schema_parts.append(f"  - {col_name}: {col_type}{pk}")
            
            # Add foreign key info
            cursor.execute(f"PRAGMA foreign_key_list('{table}')")
            fks = cursor.fetchall()
            if fks:
                schema_parts.append("  Foreign Keys:")
                for fk in fks:
                    schema_parts.append(f"    - {fk[3]} -> {fk[2]}({fk[4]})")
        
        # Add common query patterns
        schema_parts.extend([
            "",
            "COMMON QUERY PATTERNS:",
            "1. Revenue by Product:",
            "   SELECT p.ProductName, SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) as Revenue",
            "   FROM Products p JOIN \"Order Details\" od ON p.ProductID = od.ProductID",
            "   GROUP BY p.ProductName ORDER BY Revenue DESC",
            "",
            "2. Filter by Date Range:",
            "   WHERE date(o.OrderDate) BETWEEN '1997-06-01' AND '1997-06-30'",
            "",
            "3. Join Categories:",
            "   FROM Products p JOIN Categories c ON p.CategoryID = c.CategoryID",
        ])
        
        conn.close()
        
        self._schema_cache = "\n".join(schema_parts)
        return self._schema_cache
    
    def execute_query(self, sql: str, max_retries: int = 1) -> Dict[str, Any]:
        """
        Execute SQL query with automatic retry on common errors.
        
        Args:
            sql: SQL query to execute
            max_retries: Number of retry attempts for fixable errors
            
        Returns:
            Dictionary with success status, data, and metadata
        """
        original_sql = sql
        
        for attempt in range(max_retries + 1):
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute(sql)
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                
                conn.close()
                
                return {
                    'success': True,
                    'columns': columns,
                    'rows': rows,
                    'row_count': len(rows),
                    'error': None,
                    'sql_used': sql
                }
            
            except sqlite3.Error as e:
                error_msg = str(e)
                
                # Try to auto-fix common errors
                if attempt < max_retries:
                    fixed_sql = self._attempt_fix(sql, error_msg)
                    if fixed_sql != sql:
                        sql = fixed_sql
                        continue
                
                return {
                    'success': False,
                    'columns': [],
                    'rows': [],
                    'row_count': 0,
                    'error': error_msg,
                    'sql_used': original_sql
                }
        
        return {
            'success': False,
            'columns': [],
            'rows': [],
            'row_count': 0,
            'error': 'Max retries exceeded',
            'sql_used': original_sql
        }
    
    def _attempt_fix(self, sql: str, error_msg: str) -> str:
        """Attempt to fix common SQL errors."""
        fixed = sql
        
        # Fix: Order Details without quotes
        if 'no such table' in error_msg.lower() and 'order' in error_msg.lower():
            fixed = re.sub(r'\bOrder\s+Details\b', '"Order Details"', fixed, flags=re.IGNORECASE)
            if fixed != sql:
                return fixed
        
        # Fix: Missing date function for date comparisons
        if 'type' in error_msg.lower() or 'datatype' in error_msg.lower():
            # Wrap date comparisons in date() function
            fixed = re.sub(
                r"OrderDate\s*([<>=]+)\s*'(\d{4}-\d{2}-\d{2})",
                r"date(OrderDate) \1 '\2",
                fixed
            )
            if fixed != sql:
                return fixed
        
        # Fix: YEAR() function not available in SQLite
        if 'year' in error_msg.lower() or 'no such function' in error_msg.lower():
            fixed = re.sub(
                r'YEAR\(([^)]+)\)',
                r"strftime('%Y', \1)",
                fixed,
                flags=re.IGNORECASE
            )
            if fixed != sql:
                return fixed
        
        return sql
    
    def get_tables_from_query(self, sql: str) -> List[str]:
        """Extract table names mentioned in SQL query."""
        tables = set()
        sql_upper = sql.upper()
        
        # Common Northwind tables
        table_patterns = {
            'ORDERS': 'Orders',
            'ORDER DETAILS': 'Order Details',
            '"ORDER DETAILS"': 'Order Details',
            'PRODUCTS': 'Products',
            'CUSTOMERS': 'Customers',
            'CATEGORIES': 'Categories',
            'SUPPLIERS': 'Suppliers',
            'EMPLOYEES': 'Employees',
            'SHIPPERS': 'Shippers'
        }
        
        for pattern, canonical_name in table_patterns.items():
            if pattern in sql_upper:
                tables.add(canonical_name)
        
        return sorted(list(tables))
    
    def validate_query(self, sql: str) -> Dict[str, Any]:
        """
        Validate SQL query without executing (EXPLAIN).
        
        Returns:
            Dictionary with validation status and potential issues
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Use EXPLAIN QUERY PLAN to validate
            cursor.execute(f"EXPLAIN QUERY PLAN {sql}")
            plan = cursor.fetchall()
            
            conn.close()
            
            return {
                'valid': True,
                'plan': plan,
                'issues': []
            }
        
        except sqlite3.Error as e:
            return {
                'valid': False,
                'plan': [],
                'issues': [str(e)]
            }
    
    def get_date_range(self) -> Dict[str, str]:
        """Get the actual date range in the database."""
        result = self.execute_query("""
            SELECT 
                MIN(OrderDate) as min_date,
                MAX(OrderDate) as max_date
            FROM Orders
            WHERE OrderDate IS NOT NULL
        """)
        
        if result['success'] and result['rows']:
            return {
                'min': result['rows'][0][0],
                'max': result['rows'][0][1]
            }
        return {'min': None, 'max': None}
    
    def get_available_years(self) -> List[int]:
        """Get list of years with data."""
        result = self.execute_query("""
            SELECT DISTINCT strftime('%Y', OrderDate) as year
            FROM Orders
            WHERE OrderDate IS NOT NULL
            ORDER BY year
        """)
        
        if result['success']:
            return [int(row[0]) for row in result['rows'] if row[0]]
        return []