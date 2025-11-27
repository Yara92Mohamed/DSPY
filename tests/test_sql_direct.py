"""Direct SQL testing script to debug query generation."""
from agent.tools.sqlite_tool import SQLiteTool
from rich.console import Console
from rich.table import Table

console = Console()

def test_queries():
    """Test SQL queries directly against the database."""
    db = SQLiteTool()
    
    # Test queries for each question type
    test_cases = [
        {
            'name': 'Top 3 Products by Revenue',
            'sql': '''
                SELECT p.ProductName, 
                       ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2) as Revenue
                FROM "Order Details" od
                JOIN Products p ON od.ProductID = p.ProductID
                GROUP BY p.ProductName
                ORDER BY Revenue DESC
                LIMIT 3
            '''
        },
        {
            'name': 'AOV Winter 1997',
            'sql': '''
                SELECT ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) / 
                       COUNT(DISTINCT od.OrderID), 2) as AOV
                FROM "Order Details" od
                JOIN Orders o ON od.OrderID = o.OrderID
                WHERE o.OrderDate BETWEEN '1997-12-01' AND '1997-12-31'
            '''
        },
        {
            'name': 'Top Category Summer 1997',
            'sql': '''
                SELECT cat.CategoryName, SUM(od.Quantity) as TotalQuantity
                FROM "Order Details" od
                JOIN Products p ON od.ProductID = p.ProductID
                JOIN Categories cat ON p.CategoryID = cat.CategoryID
                JOIN Orders o ON od.OrderID = o.OrderID
                WHERE o.OrderDate BETWEEN '1997-06-01' AND '1997-06-30'
                GROUP BY cat.CategoryName
                ORDER BY TotalQuantity DESC
                LIMIT 1
            '''
        },
        {
            'name': 'Revenue Beverages Summer 1997',
            'sql': '''
                SELECT ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2) as Revenue
                FROM "Order Details" od
                JOIN Products p ON od.ProductID = p.ProductID
                JOIN Categories c ON p.CategoryID = c.CategoryID
                JOIN Orders o ON od.OrderID = o.OrderID
                WHERE c.CategoryName = 'Beverages'
                  AND o.OrderDate BETWEEN '1997-06-01' AND '1997-06-30'
            '''
        },
        {
            'name': 'Top Customer by Margin 1997',
            'sql': '''
                SELECT c.CompanyName,
                       ROUND(SUM((od.UnitPrice * 0.3) * od.Quantity * (1 - od.Discount)), 2) as Margin
                FROM "Order Details" od
                JOIN Orders o ON od.OrderID = o.OrderID
                JOIN Customers c ON o.CustomerID = c.CustomerID
                WHERE strftime('%Y', o.OrderDate) = '1997'
                GROUP BY c.CompanyName
                ORDER BY Margin DESC
                LIMIT 1
            '''
        },
        {
            'name': 'Total Orders 1997',
            'sql': '''
                SELECT COUNT(*) as TotalOrders
                FROM Orders
                WHERE strftime('%Y', OrderDate) = '1997'
            '''
        },
        {
            'name': 'Customer ALFKI LTV',
            'sql': '''
                SELECT ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2) as LTV
                FROM "Order Details" od
                JOIN Orders o ON od.OrderID = o.OrderID
                WHERE o.CustomerID = 'ALFKI'
            '''
        },
        {
            'name': 'Top Country by Orders',
            'sql': '''
                SELECT ShipCountry, COUNT(*) as OrderCount
                FROM Orders
                GROUP BY ShipCountry
                ORDER BY OrderCount DESC
                LIMIT 1
            '''
        }
    ]
    
    console.print("[bold]Testing SQL Queries[/bold]\n")
    
    for test in test_cases:
        console.print(f"\n[cyan]{test['name']}[/cyan]")
        console.print(f"[dim]{test['sql'].strip()[:100]}...[/dim]")
        
        result = db.execute_query(test['sql'])
        
        if result['success']:
            console.print(f"[green]✓ Success[/green]")
            console.print(f"Columns: {result['columns']}")
            console.print(f"Result: {result['rows'][:3]}")  # First 3 rows
        else:
            console.print(f"[red]✗ Failed: {result['error']}[/red]")


if __name__ == '__main__':
    test_queries()