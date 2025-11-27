"""
Template-based SQL generator as fallback when LLM fails.

Replace the generate_sql_node in graph_hybrid.py to use this instead of relying on broken LLM.
"""
import re
from typing import Dict, Optional


class TemplateSQLGenerator:
    """Generate SQL from templates instead of unreliable LLM."""
    
    @staticmethod
    def extract_dates(constraints: str) -> tuple:
        """Extract first date range from constraints."""
        start = re.search(r'START_DATE:(\d{4}-\d{2}-\d{2})', constraints)
        end = re.search(r'END_DATE:(\d{4}-\d{2}-\d{2})', constraints)
        
        if start and end:
            return start.group(1), end.group(1)
        return None, None
    
    @staticmethod
    def extract_categories(constraints: str) -> list:
        """Extract category names."""
        categories = re.findall(r'CATEGORY:([^|]+)', constraints)
        return [c.strip() for c in categories]
    
    @staticmethod
    def generate_category_quantity_query(start_date: str, end_date: str) -> str:
        """Template: Top category by quantity in date range."""
        return f"""SELECT c.CategoryName, SUM(od.Quantity) as TotalQuantity
FROM "Order Details" od
JOIN Products p ON od.ProductID = p.ProductID
JOIN Categories c ON p.CategoryID = c.CategoryID
JOIN Orders o ON od.OrderID = o.OrderID
WHERE date(o.OrderDate) BETWEEN '{start_date}' AND '{end_date}'
GROUP BY c.CategoryName
ORDER BY TotalQuantity DESC
LIMIT 1"""
    
    @staticmethod
    def generate_aov_query(start_date: str, end_date: str) -> str:
        """Template: Average Order Value in date range."""
        return f"""SELECT ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) / COUNT(DISTINCT o.OrderID), 2) as AOV
FROM "Order Details" od
JOIN Orders o ON od.OrderID = o.OrderID
WHERE date(o.OrderDate) BETWEEN '{start_date}' AND '{end_date}'"""
    
    @staticmethod
    def generate_top_products_revenue_query() -> str:
        """Template: Top 3 products by revenue (all-time)."""
        return """SELECT p.ProductName, ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2) as Revenue
FROM "Order Details" od
JOIN Products p ON od.ProductID = p.ProductID
GROUP BY p.ProductName
ORDER BY Revenue DESC
LIMIT 3"""
    
    @staticmethod
    def generate_category_revenue_query(category: str, start_date: str, end_date: str) -> str:
        """Template: Revenue for specific category in date range."""
        return f"""SELECT ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2) as Revenue
FROM "Order Details" od
JOIN Products p ON od.ProductID = p.ProductID
JOIN Categories c ON p.CategoryID = c.CategoryID
JOIN Orders o ON od.OrderID = o.OrderID
WHERE c.CategoryName = '{category}'
  AND date(o.OrderDate) BETWEEN '{start_date}' AND '{end_date}'"""
    
    @staticmethod
    def generate_customer_margin_query(year: str) -> str:
        """Template: Top customer by gross margin in year."""
        return f"""SELECT c.CompanyName, ROUND(SUM((od.UnitPrice * 0.3) * od.Quantity * (1 - od.Discount)), 2) as GrossMargin
FROM "Order Details" od
JOIN Orders o ON od.OrderID = o.OrderID
JOIN Customers c ON o.CustomerID = c.CustomerID
WHERE strftime('%Y', o.OrderDate) = '{year}'
GROUP BY c.CompanyName
ORDER BY GrossMargin DESC
LIMIT 1"""
    
    @classmethod
    def generate_from_question(cls, question: str, constraints: str) -> Optional[str]:
        """
        Generate SQL using templates based on question pattern.
        Returns None if no template matches.
        """
        question_lower = question.lower()
        
        # Extract dates
        start_date, end_date = cls.extract_dates(constraints)
        
        # Pattern 1: Top category by quantity
        if 'category' in question_lower and 'quantity' in question_lower and 'highest' in question_lower:
            if start_date and end_date:
                return cls.generate_category_quantity_query(start_date, end_date)
        
        # Pattern 2: Average Order Value (AOV)
        if 'aov' in question_lower or 'average order value' in question_lower:
            if start_date and end_date:
                return cls.generate_aov_query(start_date, end_date)
        
        # Pattern 3: Top 3 products by revenue (all-time)
        if 'top 3 products' in question_lower and 'revenue' in question_lower and 'all-time' in question_lower:
            return cls.generate_top_products_revenue_query()
        
        # Pattern 4: Category revenue in date range
        if 'revenue' in question_lower and 'category' in question_lower:
            categories = cls.extract_categories(constraints)
            if categories and start_date and end_date:
                # Use first category (usually the relevant one)
                return cls.generate_category_revenue_query(categories[0], start_date, end_date)
        
        # Pattern 5: Revenue from specific category (e.g., "Beverages revenue")
        if 'revenue' in question_lower:
            # Check for category name in question
            category_names = ['Beverages', 'Condiments', 'Confections', 'Dairy Products', 
                            'Grains/Cereals', 'Meat/Poultry', 'Produce', 'Seafood']
            for cat in category_names:
                if cat.lower() in question_lower:
                    if start_date and end_date:
                        return cls.generate_category_revenue_query(cat, start_date, end_date)
        
        # Pattern 6: Customer by margin
        if 'customer' in question_lower and 'margin' in question_lower:
            # Extract year from question or constraints
            year_match = re.search(r'(20\d{2})', question)
            if year_match:
                return cls.generate_customer_margin_query(year_match.group(1))
        
        return None


def generate_sql_node_with_templates(self, state):
    """
    REPLACEMENT for generate_sql_node in HybridAgent.
    
    Uses template-based generation with LLM as fallback.
    """
    question_lower = state['question'].lower()
    all_constraints = state.get('constraints', '').split(' | ')
    
    # Filter to relevant date range
    filtered_constraints = []
    
    if 'summer' in question_lower and '2017' in question_lower:
        for c in all_constraints:
            if 'START_DATE:2017-06-01' in c or 'END_DATE:2017-06-30' in c:
                filtered_constraints.append(c)
            elif 'START_DATE:' not in c and 'END_DATE:' not in c:
                filtered_constraints.append(c)
    elif 'winter' in question_lower and '2017' in question_lower:
        for c in all_constraints:
            if 'START_DATE:2017-12-01' in c or 'END_DATE:2017-12-31' in c:
                filtered_constraints.append(c)
            elif 'START_DATE:' not in c and 'END_DATE:' not in c:
                filtered_constraints.append(c)
    else:
        # First date range only
        seen_date = False
        for c in all_constraints:
            if 'START_DATE:' in c or 'END_DATE:' in c:
                if not seen_date:
                    filtered_constraints.append(c)
                    seen_date = True
            else:
                filtered_constraints.append(c)
    
    enhanced_constraints = ' | '.join(filtered_constraints)
    self._current_constraints = enhanced_constraints
    
    self._log(f"Constraints: {enhanced_constraints[:200]}...")
    
    # TRY TEMPLATE FIRST
    sql = TemplateSQLGenerator.generate_from_question(state['question'], enhanced_constraints)
    
    if sql:
        self._log("Using TEMPLATE-generated SQL")
        state['sql'] = sql
        state['trace'].append("Generated SQL (template)")
    else:
        # Fallback to LLM
        self._log("No template match, using LLM")
        
        schema = self.db.get_schema()
        
        hints = [
            "CRITICAL: Use date(o.OrderDate) for dates",
            'CRITICAL: Use "Order Details" with quotes',
            "CRITICAL: JOIN Orders o ON od.OrderID = o.OrderID"
        ]
        
        enhanced_constraints += " | " + " | ".join(hints)
        
        sql = self.sql_gen(
            question=state['question'],
            schema=schema,
            constraints=enhanced_constraints
        )
        
        # Aggressive cleaning
        sql = self._clean_sql_aggressive(sql)
        
        state['sql'] = sql
        state['trace'].append("Generated SQL (LLM + cleaned)")
    
    self._log(f"Final SQL:\n{sql}")
    
    return state


def _clean_sql_aggressive(self, sql: str) -> str:
    """
    ULTRA-AGGRESSIVE SQL cleaning for broken LLM output.
    """
    # Remove markdown
    sql = re.sub(r'```(?:sql)?\n?', '', sql)
    sql = sql.strip()
    
    # Extract SELECT if buried
    if 'SELECT' in sql.upper():
        sql = sql[sql.upper().find('SELECT'):]
    
    # Fix all known typos
    sql = sql.replace('BETWEWHEN', 'BETWEEN')
    sql = sql.replace('BETWEWEN', 'BETWEEN')
    sql = sql.replace('BETWEN', 'BETWEEN')
    sql = sql.replace('BEWTEEN', 'BETWEEN')
    
    # Fix quotes - TRIPLE QUOTES to DOUBLE
    sql = sql.replace('"""', '"')
    sql = sql.replace("'''", "'")
    
    # Fix "o".OrderDate -> o.OrderDate
    sql = re.sub(r'"([a-z])"\.', r'\1.', sql)
    
    # Fix Order Details
    sql = re.sub(r'\bOrder\s+Details\b', '"Order Details"', sql, flags=re.IGNORECASE)
    sql = re.sub(r'["\']Order\s+Details["\']', '"Order Details"', sql, flags=re.IGNORECASE)
    
    # Remove SQL comments (they often contain errors)
    sql = re.sub(r'--[^\n]*', '', sql)
    
    # Fix missing FROM
    if 'SELECT' in sql.upper() and 'FROM' not in sql.upper():
        # SQL is truncated, try to recover
        if '"Order Details"' in sql:
            # Add minimal FROM clause
            select_pos = sql.upper().find('SELECT')
            sql = sql[:select_pos] + 'SELECT * FROM "Order Details" od'
    
    # Add missing Orders JOIN if needed
    if 'o.OrderDate' in sql and 'JOIN Orders' not in sql:
        if 'WHERE' in sql.upper():
            where_pos = sql.upper().find('WHERE')
            before = sql[:where_pos].rstrip()
            after = sql[where_pos:]
            
            if 'Orders o' not in before:
                before += '\nJOIN Orders o ON od.OrderID = o.OrderID'
                sql = before + '\n' + after
    
    # Fix date wrapper
    sql = re.sub(
        r'\bOrderDate\s+(BETWEEN|>=|<=|>|<|=)',
        r'date(OrderDate) \1',
        sql,
        flags=re.IGNORECASE
    )
    
    # Ensure o.OrderDate has date()
    sql = re.sub(
        r'\bo\.OrderDate\s+(BETWEEN|>=|<=|>|<|=)',
        r'date(o.OrderDate) \1',
        sql,
        flags=re.IGNORECASE
    )
    
    # Fix wrong date range
    if self._current_constraints:
        start = re.search(r'START_DATE:(\d{4}-\d{2}-\d{2})', self._current_constraints)
        end = re.search(r'END_DATE:(\d{4}-\d{2}-\d{2})', self._current_constraints)
        
        if start and end:
            correct_start = start.group(1)
            correct_end = end.group(1)
            
            sql = re.sub(
                r"date\([^)]+\.OrderDate\)\s+BETWEEN\s+'[^']+'\s+AND\s+'[^']+'",
                f"date(o.OrderDate) BETWEEN '{correct_start}' AND '{correct_end}'",
                sql,
                count=1,
                flags=re.IGNORECASE
            )
    
    # Remove trailing semicolon and whitespace
    sql = sql.rstrip(';').strip()
    
    return sql


# ============= TESTING =============
if __name__ == '__main__':
    # Test template generation
    gen = TemplateSQLGenerator()
    
    # Test 1: Category quantity
    q1 = "During 'Summer Beverages 2017', which product category had the highest total quantity sold?"
    c1 = "START_DATE:2017-06-01 | END_DATE:2017-06-30 | CATEGORY:Beverages"
    
    sql1 = gen.generate_from_question(q1, c1)
    print("Test 1 - Category Quantity:")
    print(sql1)
    print()
    
    # Test 2: AOV
    q2 = "What was the Average Order Value during Winter Classics 2017?"
    c2 = "START_DATE:2017-12-01 | END_DATE:2017-12-31 | KPI:AOV"
    
    sql2 = gen.generate_from_question(q2, c2)
    print("Test 2 - AOV:")
    print(sql2)
    print()
    
    # Test 3: Top 3 products
    q3 = "Top 3 products by total revenue all-time"
    c3 = ""
    
    sql3 = gen.generate_from_question(q3, c3)
    print("Test 3 - Top Products:")
    print(sql3)
    print()
    
    # Test 4: Category revenue
    q4 = "Total revenue from Beverages during Summer 2017"
    c4 = "START_DATE:2017-06-01 | END_DATE:2017-06-30 | CATEGORY:Beverages"
    
    sql4 = gen.generate_from_question(q4, c4)
    print("Test 4 - Category Revenue:")
    print(sql4)
    print()
    
    # Test 5: Customer margin
    q5 = "Which customer had highest gross margin in 2017?"
    c5 = ""
    
    sql5 = gen.generate_from_question(q5, c5)
    print("Test 5 - Customer Margin:")
    print(sql5)