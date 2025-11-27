"""Validate and test SQL outputs for each evaluation question."""
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from agent.tools.sqlite_tool import SQLiteTool

console = Console()


def test_question_1_rag():
    """Test: Return window for unopened Beverages (RAG only)."""
    console.print("\n[bold cyan]Question 1: Return window for unopened Beverages[/bold cyan]")
    console.print("Expected: 14 (integer)")
    console.print("Type: RAG only (from product_policy.md)")
    
    # Check the document
    from agent.rag.retrieval import TFIDFRetriever
    retriever = TFIDFRetriever("docs")
    docs = retriever.retrieve("return window unopened Beverages", top_k=3)
    
    for doc in docs:
        if 'Beverages' in doc['content']:
            console.print(f"\n[green]Found in {doc['id']}:[/green]")
            console.print(doc['content'])
    
    console.print("\n[green]✓ Correct answer: 14[/green]")
    return {"expected": 14, "type": "int"}


def test_question_2_category_qty():
    """Test: Top category by quantity in Summer 2017."""
    console.print("\n[bold cyan]Question 2: Top category by quantity (Summer 2017)[/bold cyan]")
    console.print("Expected: {category:str, quantity:int}")
    console.print("Date range: 2017-06-01 to 2017-06-30")
    
    db = SQLiteTool()
    
    # First, check if we have data in that range
    console.print("\n[yellow]Step 1: Check data availability[/yellow]")
    result = db.execute_query("""
        SELECT COUNT(*) as OrderCount
        FROM Orders
        WHERE date(OrderDate) BETWEEN '2017-06-01' AND '2017-06-30'
    """)
    
    if result['success']:
        order_count = result['rows'][0][0]
        console.print(f"Orders in June 2017: {order_count}")
        
        if order_count == 0:
            console.print("[red]✗ No data in this date range![/red]")
            return {"expected": None, "type": "{category:str, quantity:int}", "error": "No data"}
    
    # Now get the actual answer
    console.print("\n[yellow]Step 2: Calculate top category[/yellow]")
    
    sql = """
SELECT c.CategoryName, SUM(od.Quantity) as TotalQuantity
FROM "Order Details" od
JOIN Products p ON od.ProductID = p.ProductID
JOIN Categories c ON p.CategoryID = c.CategoryID
JOIN Orders o ON od.OrderID = o.OrderID
WHERE date(o.OrderDate) BETWEEN '2017-06-01' AND '2017-06-30'
GROUP BY c.CategoryName
ORDER BY TotalQuantity DESC
LIMIT 1
    """
    
    console.print(Panel(Syntax(sql, "sql", theme="monokai"), title="SQL Query"))
    
    result = db.execute_query(sql)
    
    if result['success'] and result['rows']:
        category, quantity = result['rows'][0]
        answer = {"category": category, "quantity": int(quantity)}
        console.print(f"\n[green]✓ Correct answer: {answer}[/green]")
        return {"expected": answer, "type": "{category:str, quantity:int}"}
    else:
        console.print(f"\n[red]✗ Query failed or no results[/red]")
        if not result['success']:
            console.print(f"Error: {result['error']}")
        return {"expected": None, "type": "{category:str, quantity:int}", "error": result.get('error', 'No rows')}


def test_question_3_aov_winter():
    """Test: AOV during Winter 2017."""
    console.print("\n[bold cyan]Question 3: AOV during Winter Classics 2017[/bold cyan]")
    console.print("Expected: float (rounded to 2 decimals)")
    console.print("Date range: 2017-12-01 to 2017-12-31")
    console.print("Formula: SUM(UnitPrice * Quantity * (1-Discount)) / COUNT(DISTINCT OrderID)")
    
    db = SQLiteTool()
    
    # Check data
    console.print("\n[yellow]Step 1: Check data availability[/yellow]")
    result = db.execute_query("""
        SELECT COUNT(*) as OrderCount
        FROM Orders
        WHERE date(OrderDate) BETWEEN '2017-12-01' AND '2017-12-31'
    """)
    
    if result['success']:
        order_count = result['rows'][0][0]
        console.print(f"Orders in Dec 2017: {order_count}")
        
        if order_count == 0:
            console.print("[red]✗ No data in this date range![/red]")
            return {"expected": None, "type": "float", "error": "No data"}
    
    # Calculate AOV
    console.print("\n[yellow]Step 2: Calculate AOV[/yellow]")
    
    sql = """
SELECT ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) / COUNT(DISTINCT o.OrderID), 2) as AOV
FROM "Order Details" od
JOIN Orders o ON od.OrderID = o.OrderID
WHERE date(o.OrderDate) BETWEEN '2017-12-01' AND '2017-12-31'
    """
    
    console.print(Panel(Syntax(sql, "sql", theme="monokai"), title="SQL Query"))
    
    result = db.execute_query(sql)
    
    if result['success'] and result['rows']:
        aov = float(result['rows'][0][0])
        console.print(f"\n[green]✓ Correct answer: {aov}[/green]")
        return {"expected": aov, "type": "float"}
    else:
        console.print(f"\n[red]✗ Query failed or no results[/red]")
        if not result['success']:
            console.print(f"Error: {result['error']}")
        return {"expected": None, "type": "float", "error": result.get('error', 'No rows')}


def test_question_4_top3_products():
    """Test: Top 3 products by revenue all-time."""
    console.print("\n[bold cyan]Question 4: Top 3 products by revenue (all-time)[/bold cyan]")
    console.print("Expected: list[{product:str, revenue:float}]")
    console.print("Formula: SUM(UnitPrice * Quantity * (1-Discount))")
    
    db = SQLiteTool()
    
    sql = """
SELECT p.ProductName, ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2) as Revenue
FROM "Order Details" od
JOIN Products p ON od.ProductID = p.ProductID
GROUP BY p.ProductName
ORDER BY Revenue DESC
LIMIT 3
    """
    
    console.print(Panel(Syntax(sql, "sql", theme="monokai"), title="SQL Query"))
    
    result = db.execute_query(sql)
    
    if result['success'] and result['rows']:
        products = [
            {"product": row[0], "revenue": float(row[1])}
            for row in result['rows']
        ]
        console.print(f"\n[green]✓ Correct answer:[/green]")
        for p in products:
            console.print(f"  - {p['product']}: ${p['revenue']:,.2f}")
        return {"expected": products, "type": "list[{product:str, revenue:float}]"}
    else:
        console.print(f"\n[red]✗ Query failed[/red]")
        console.print(f"Error: {result['error']}")
        return {"expected": None, "type": "list[{product:str, revenue:float}]", "error": result['error']}


def test_question_5_beverages_revenue():
    """Test: Beverages revenue during Summer 2017."""
    console.print("\n[bold cyan]Question 5: Beverages revenue (Summer 2017)[/bold cyan]")
    console.print("Expected: float (rounded to 2 decimals)")
    console.print("Date range: 2017-06-01 to 2017-06-30")
    console.print("Category: Beverages")
    
    db = SQLiteTool()
    
    # Check data
    console.print("\n[yellow]Step 1: Check Beverages orders in June 2017[/yellow]")
    result = db.execute_query("""
        SELECT COUNT(*) as OrderCount
        FROM "Order Details" od
        JOIN Products p ON od.ProductID = p.ProductID
        JOIN Categories c ON p.CategoryID = c.CategoryID
        JOIN Orders o ON od.OrderID = o.OrderID
        WHERE c.CategoryName = 'Beverages'
          AND date(o.OrderDate) BETWEEN '2017-06-01' AND '2017-06-30'
    """)
    
    if result['success']:
        order_items = result['rows'][0][0]
        console.print(f"Beverage order items in June 2017: {order_items}")
        
        if order_items == 0:
            console.print("[red]✗ No beverage orders in this date range![/red]")
            return {"expected": None, "type": "float", "error": "No data"}
    
    # Calculate revenue
    console.print("\n[yellow]Step 2: Calculate revenue[/yellow]")
    
    sql = """
SELECT ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2) as Revenue
FROM "Order Details" od
JOIN Products p ON od.ProductID = p.ProductID
JOIN Categories c ON p.CategoryID = c.CategoryID
JOIN Orders o ON od.OrderID = o.OrderID
WHERE c.CategoryName = 'Beverages'
  AND date(o.OrderDate) BETWEEN '2017-06-01' AND '2017-06-30'
    """
    
    console.print(Panel(Syntax(sql, "sql", theme="monokai"), title="SQL Query"))
    
    result = db.execute_query(sql)
    
    if result['success'] and result['rows'] and result['rows'][0][0] is not None:
        revenue = float(result['rows'][0][0])
        console.print(f"\n[green]✓ Correct answer: ${revenue:,.2f}[/green]")
        return {"expected": revenue, "type": "float"}
    else:
        console.print(f"\n[red]✗ Query failed or no results[/red]")
        return {"expected": 0.0, "type": "float", "note": "No revenue (possibly no orders)"}


def test_question_6_customer_margin():
    """Test: Top customer by gross margin in 2017."""
    console.print("\n[bold cyan]Question 6: Top customer by gross margin (2017)[/bold cyan]")
    console.print("Expected: {customer:str, margin:float}")
    console.print("Formula: SUM((UnitPrice * 0.3) * Quantity * (1-Discount))")
    console.print("Note: Cost = 70% of UnitPrice, so profit = 30%")
    
    db = SQLiteTool()
    
    # Check data
    console.print("\n[yellow]Step 1: Check orders in 2017[/yellow]")
    result = db.execute_query("""
        SELECT COUNT(*) as OrderCount
        FROM Orders
        WHERE strftime('%Y', OrderDate) = '2017'
    """)
    
    if result['success']:
        order_count = result['rows'][0][0]
        console.print(f"Orders in 2017: {order_count}")
        
        if order_count == 0:
            console.print("[red]✗ No data in 2017![/red]")
            return {"expected": None, "type": "{customer:str, margin:float}", "error": "No data"}
    
    # Calculate margin
    console.print("\n[yellow]Step 2: Calculate top customer by margin[/yellow]")
    
    sql = """
SELECT c.CompanyName, ROUND(SUM((od.UnitPrice * 0.3) * od.Quantity * (1 - od.Discount)), 2) as GrossMargin
FROM "Order Details" od
JOIN Orders o ON od.OrderID = o.OrderID
JOIN Customers c ON o.CustomerID = c.CustomerID
WHERE strftime('%Y', o.OrderDate) = '2017'
GROUP BY c.CompanyName
ORDER BY GrossMargin DESC
LIMIT 1
    """
    
    console.print(Panel(Syntax(sql, "sql", theme="monokai"), title="SQL Query"))
    
    result = db.execute_query(sql)
    
    if result['success'] and result['rows']:
        customer, margin = result['rows'][0]
        answer = {"customer": customer, "margin": float(margin)}
        console.print(f"\n[green]✓ Correct answer: {answer}[/green]")
        return {"expected": answer, "type": "{customer:str, margin:float}"}
    else:
        console.print(f"\n[red]✗ Query failed or no results[/red]")
        if not result['success']:
            console.print(f"Error: {result['error']}")
        return {"expected": None, "type": "{customer:str, margin:float}", "error": result.get('error', 'No rows')}


def compare_with_actual_output():
    """Compare expected answers with actual agent output."""
    console.print("\n[bold magenta]Comparing with actual agent output...[/bold magenta]")
    
    output_file = Path("outputs_hybrid.jsonl")
    if not output_file.exists():
        console.print("[yellow]No outputs_hybrid.jsonl file found. Run the agent first.[/yellow]")
        return
    
    # Load actual outputs
    with open(output_file, 'r') as f:
        actual_outputs = [json.loads(line) for line in f]
    
    # Load expected answers
    expected = {
        "rag_policy_beverages_return_days": 14,
        # Others will be computed above
    }
    
    # Create comparison table
    table = Table(title="Expected vs Actual Comparison", show_header=True)
    table.add_column("Question ID", style="cyan", width=30)
    table.add_column("Expected", style="green", width=30)
    table.add_column("Actual", style="yellow", width=30)
    table.add_column("Match", style="bold", width=10)
    
    for output in actual_outputs:
        qid = output['id']
        actual = output['final_answer']
        expected_val = expected.get(qid, "See test above")
        
        match = "✓" if str(actual) == str(expected_val) else "✗"
        
        table.add_row(
            qid,
            str(expected_val)[:30],
            str(actual)[:30] if actual is not None else "None",
            match
        )
    
    console.print(table)


def main():
    """Run all validation tests."""
    console.print("[bold]SQL Output Validation Suite[/bold]")
    console.print("=" * 70)
    
    results = {}
    
    results['q1'] = test_question_1_rag()
    results['q2'] = test_question_2_category_qty()
    results['q3'] = test_question_3_aov_winter()
    results['q4'] = test_question_4_top3_products()
    results['q5'] = test_question_5_beverages_revenue()
    results['q6'] = test_question_6_customer_margin()
    
    # Summary
    console.print("\n[bold green]Expected Answers Summary:[/bold green]")
    for qid, result in results.items():
        if result['expected'] is not None:
            console.print(f"  {qid}: {result['expected']}")
        else:
            console.print(f"  {qid}: [red]ERROR - {result.get('error', 'Unknown')}[/red]")
    
    # Compare with actual
    compare_with_actual_output()
    
    # Save expected answers
    expected_file = Path("expected_answers.json")
    expected_data = {
        qid: result['expected'] 
        for qid, result in results.items()
    }
    
    with open(expected_file, 'w') as f:
        json.dump(expected_data, f, indent=2)
    
    console.print(f"\n[green]✓ Expected answers saved to {expected_file}[/green]")


if __name__ == '__main__':
    main()