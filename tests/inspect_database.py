"""Inspect the Northwind database to understand its structure and data."""
from agent.tools.sqlite_tool import SQLiteTool
from rich.console import Console
from rich.table import Table

console = Console()

def inspect_database():
    """Inspect database contents."""
    db = SQLiteTool()
    
    # 1. Check date ranges in Orders
    console.print("\n[bold cyan]1. Date Range in Orders[/bold cyan]")
    result = db.execute_query("""
        SELECT MIN(OrderDate) as MinDate, 
               MAX(OrderDate) as MaxDate,
               COUNT(*) as TotalOrders
        FROM Orders
    """)
    if result['success']:
        console.print(f"Date Range: {result['rows'][0][0]} to {result['rows'][0][1]}")
        console.print(f"Total Orders: {result['rows'][0][2]}")
    
    # 2. Sample orders from 1997
    console.print("\n[bold cyan]2. Sample Orders from 1997[/bold cyan]")
    result = db.execute_query("""
        SELECT OrderID, OrderDate, CustomerID
        FROM Orders
        WHERE OrderDate LIKE '1997%'
        LIMIT 5
    """)
    if result['success']:
        for row in result['rows']:
            console.print(f"  {row}")
    
    # 3. Check June 1997 orders
    console.print("\n[bold cyan]3. Orders in June 1997[/bold cyan]")
    result = db.execute_query("""
        SELECT COUNT(*) as Count
        FROM Orders
        WHERE OrderDate LIKE '1997-06%'
    """)
    if result['success']:
        console.print(f"Count: {result['rows'][0][0]}")
    
    # 4. Check Categories
    console.print("\n[bold cyan]4. Categories[/bold cyan]")
    result = db.execute_query("""
        SELECT CategoryID, CategoryName
        FROM Categories
    """)
    if result['success']:
        for row in result['rows']:
            console.print(f"  {row}")
    
    # 5. Check Order Details structure
    console.print("\n[bold cyan]5. Sample Order Details[/bold cyan]")
    result = db.execute_query("""
        SELECT *
        FROM "Order Details"
        LIMIT 3
    """)
    if result['success']:
        console.print(f"Columns: {result['columns']}")
        for row in result['rows']:
            console.print(f"  {row}")
    
    # 6. Test a simple revenue query
    console.print("\n[bold cyan]6. Total Revenue (All Time)[/bold cyan]")
    result = db.execute_query("""
        SELECT ROUND(SUM(UnitPrice * Quantity * (1 - Discount)), 2) as TotalRevenue
        FROM "Order Details"
    """)
    if result['success']:
        console.print(f"Total Revenue: {result['rows'][0][0]}")
    
    # 7. Orders per year
    console.print("\n[bold cyan]7. Orders per Year[/bold cyan]")
    result = db.execute_query("""
        SELECT substr(OrderDate, 1, 4) as Year, COUNT(*) as OrderCount
        FROM Orders
        WHERE OrderDate IS NOT NULL
        GROUP BY Year
        ORDER BY Year
    """)
    if result['success']:
        for row in result['rows']:
            console.print(f"  {row[0]}: {row[1]} orders")
    
    # 8. Check if dates are stored as text or datetime
    console.print("\n[bold cyan]8. Date Format Check[/bold cyan]")
    result = db.execute_query("""
        SELECT OrderDate, typeof(OrderDate) as DateType
        FROM Orders
        LIMIT 3
    """)
    if result['success']:
        for row in result['rows']:
            console.print(f"  Date: {row[0]}, Type: {row[1]}")
    
    # 9. Check Beverages products
    console.print("\n[bold cyan]9. Beverages Products[/bold cyan]")
    result = db.execute_query("""
        SELECT p.ProductName, c.CategoryName
        FROM Products p
        JOIN Categories c ON p.CategoryID = c.CategoryID
        WHERE c.CategoryName = 'Beverages'
        LIMIT 5
    """)
    if result['success']:
        for row in result['rows']:
            console.print(f"  {row[0]} ({row[1]})")
    
    # 10. Test AOV calculation
    console.print("\n[bold cyan]10. AOV Calculation Test[/bold cyan]")
    result = db.execute_query("""
        SELECT 
            COUNT(DISTINCT o.OrderID) as OrderCount,
            ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2) as TotalRevenue,
            ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) / COUNT(DISTINCT o.OrderID), 2) as AOV
        FROM "Order Details" od
        JOIN Orders o ON od.OrderID = o.OrderID
    """)
    if result['success']:
        console.print(f"  Orders: {result['rows'][0][0]}")
        console.print(f"  Total Revenue: {result['rows'][0][1]}")
        console.print(f"  AOV: {result['rows'][0][2]}")


if __name__ == '__main__':
    inspect_database()