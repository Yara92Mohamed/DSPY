"""DSPy optimization script for NL-to-SQL module."""
import dspy
from agent.dspy_signatures import NLToSQLModule
from agent.tools.sqlite_tool import SQLiteTool
from rich.console import Console
from rich.table import Table

console = Console()


def setup_dspy():
    """Configure DSPy with local Ollama model."""
    try:
        # Try the newer DSPy API first
        lm = dspy.LM(
            model="ollama/phi3.5:3.8b-mini-instruct-q4_K_M",
            api_base="http://localhost:11434",
            max_tokens=800,
            temperature=0.1
        )
    except:
        # Fallback to older API
        try:
            from dspy.clients import Ollama
            lm = Ollama(
                model="phi3.5:3.8b-mini-instruct-q4_K_M",
                max_tokens=800,
                temperature=0.1
            )
        except:
            # Last resort
            lm = dspy.OpenAI(
                model="ollama/phi3.5:3.8b-mini-instruct-q4_K_M",
                api_base="http://localhost:11434",
                api_key="dummy",
                max_tokens=800,
                temperature=0.1
            )
    dspy.settings.configure(lm=lm)


def create_training_examples():
    """Create a comprehensive training set for SQL generation."""
    db = SQLiteTool()
    schema = db.get_schema()
    
    examples = [
        # Simple aggregation
        dspy.Example(
            question="What are the top 3 products by revenue?",
            schema=schema,
            constraints="Revenue = SUM(UnitPrice * Quantity * (1 - Discount)) | Use \"Order Details\" with quotes | Return top 3",
            sql="""SELECT p.ProductName, ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2) as Revenue
FROM "Order Details" od
JOIN Products p ON od.ProductID = p.ProductID
GROUP BY p.ProductName
ORDER BY Revenue DESC
LIMIT 3"""
        ).with_inputs('question', 'schema', 'constraints'),
        
        # Category quantity with date filter
        dspy.Example(
            question="Which category had the highest quantity sold in June 2017?",
            schema=schema,
            constraints="START_DATE:2017-06-01 | END_DATE:2017-06-30 | Use date(OrderDate) for comparisons | Sum quantities",
            sql="""SELECT c.CategoryName, SUM(od.Quantity) as TotalQuantity
FROM "Order Details" od
JOIN Products p ON od.ProductID = p.ProductID
JOIN Categories c ON p.CategoryID = c.CategoryID
JOIN Orders o ON od.OrderID = o.OrderID
WHERE date(o.OrderDate) BETWEEN '2017-06-01' AND '2017-06-30'
GROUP BY c.CategoryName
ORDER BY TotalQuantity DESC
LIMIT 1"""
        ).with_inputs('question', 'schema', 'constraints'),
        
        # AOV calculation
        dspy.Example(
            question="What was the average order value in December 2017?",
            schema=schema,
            constraints="START_DATE:2017-12-01 | END_DATE:2017-12-31 | KPI:AOV=SUM(revenue)/COUNT(DISTINCT OrderID) | Use date(OrderDate)",
            sql="""SELECT ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) / COUNT(DISTINCT o.OrderID), 2) as AOV
FROM "Order Details" od
JOIN Orders o ON od.OrderID = o.OrderID
WHERE date(o.OrderDate) BETWEEN '2017-12-01' AND '2017-12-31'"""
        ).with_inputs('question', 'schema', 'constraints'),
        
        # Category revenue with filter
        dspy.Example(
            question="Total revenue from Beverages in June 2017",
            schema=schema,
            constraints="CATEGORY:Beverages | START_DATE:2017-06-01 | END_DATE:2017-06-30 | Revenue formula | Use date(OrderDate)",
            sql="""SELECT ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2) as Revenue
FROM "Order Details" od
JOIN Products p ON od.ProductID = p.ProductID
JOIN Categories c ON p.CategoryID = c.CategoryID
JOIN Orders o ON od.OrderID = o.OrderID
WHERE c.CategoryName = 'Beverages'
  AND date(o.OrderDate) BETWEEN '2017-06-01' AND '2017-06-30'"""
        ).with_inputs('question', 'schema', 'constraints'),
        
        # Customer by margin
        dspy.Example(
            question="Which customer had the highest gross margin in 2017?",
            schema=schema,
            constraints="KPI:GrossMargin=SUM((UnitPrice*0.3)*Quantity*(1-Discount)) | Year:2017 | Cost=70% of price",
            sql="""SELECT c.CompanyName, ROUND(SUM((od.UnitPrice * 0.3) * od.Quantity * (1 - od.Discount)), 2) as GrossMargin
FROM "Order Details" od
JOIN Orders o ON od.OrderID = o.OrderID
JOIN Customers c ON o.CustomerID = c.CustomerID
WHERE strftime('%Y', o.OrderDate) = '2017'
GROUP BY c.CompanyName
ORDER BY GrossMargin DESC
LIMIT 1"""
        ).with_inputs('question', 'schema', 'constraints'),
        
        # Multiple products
        dspy.Example(
            question="List top 3 products by total revenue",
            schema=schema,
            constraints="Revenue = SUM(UnitPrice * Quantity * (1 - Discount)) | Return 3 rows | Order by revenue descending",
            sql="""SELECT p.ProductName, ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2) as Revenue
FROM "Order Details" od
JOIN Products p ON od.ProductID = p.ProductID
GROUP BY p.ProductName
ORDER BY Revenue DESC
LIMIT 3"""
        ).with_inputs('question', 'schema', 'constraints'),
    ]
    
    return examples


def validate_sql(sql: str, db: SQLiteTool) -> tuple[bool, str]:
    """Check if SQL is valid and executable."""
    result = db.execute_query(sql)
    if result['success']:
        return True, "OK"
    else:
        return False, result['error']


def evaluate_module(module: NLToSQLModule, examples: list, db: SQLiteTool) -> dict:
    """Evaluate SQL generation quality with detailed metrics."""
    valid_count = 0
    syntax_errors = 0
    execution_errors = 0
    total = len(examples)
    
    results = []
    
    for ex in examples:
        try:
            generated_sql = module.forward(
                question=ex.question,
                schema=ex.schema,
                constraints=ex.constraints
            )
            
            is_valid, error_msg = validate_sql(generated_sql, db)
            
            if is_valid:
                valid_count += 1
                status = "✓ Valid"
            else:
                if "syntax" in error_msg.lower():
                    syntax_errors += 1
                    status = "✗ Syntax Error"
                else:
                    execution_errors += 1
                    status = "✗ Execution Error"
            
            results.append({
                'question': ex.question[:50] + "...",
                'status': status,
                'error': error_msg if not is_valid else ""
            })
            
        except Exception as e:
            syntax_errors += 1
            results.append({
                'question': ex.question[:50] + "...",
                'status': "✗ Generation Failed",
                'error': str(e)
            })
    
    return {
        'valid_sql_rate': valid_count / total if total > 0 else 0,
        'valid_count': valid_count,
        'total': total,
        'syntax_errors': syntax_errors,
        'execution_errors': execution_errors,
        'results': results
    }


class BaselineModule(dspy.Module):
    """Baseline zero-shot SQL generator without optimizations."""
    
    def __init__(self):
        super().__init__()
        from agent.dspy_signatures import GenerateSQL
        self.generator = dspy.Predict(GenerateSQL)  # No CoT
    
    def forward(self, question: str, schema: str, constraints: str = "") -> str:
        try:
            result = self.generator(
                question=question,
                db_schema=schema,
                constraints=constraints or "No constraints"
            )
            
            sql = result.sql.strip()
            
            # Minimal cleaning
            if sql.startswith('```'):
                lines = sql.split('\n')
                sql = '\n'.join([l for l in lines if not l.startswith('```')])
            
            return sql.strip()
        except:
            return "SELECT 1"


def main():
    """Run DSPy optimization experiment."""
    console.print("[bold]DSPy Optimization Experiment: NL-to-SQL[/bold]\n")
    
    # Setup
    console.print("Setting up DSPy with Ollama...")
    setup_dspy()
    db = SQLiteTool()
    
    # Create training examples
    console.print("Creating training examples...")
    train_examples = create_training_examples()
    console.print(f"✓ Created {len(train_examples)} training examples\n")
    
    # Baseline evaluation (zero-shot Predict)
    console.print("[cyan]Evaluating Baseline (Zero-shot Predict)...[/cyan]")
    baseline_module = BaselineModule()
    baseline_metrics = evaluate_module(baseline_module, train_examples, db)
    console.print(f"✓ Baseline: {baseline_metrics['valid_count']}/{baseline_metrics['total']} valid queries\n")
    
    # Optimized evaluation (ChainOfThought + enhanced prompting)
    console.print("[cyan]Evaluating Optimized (ChainOfThought + Fallbacks)...[/cyan]")
    optimized_module = NLToSQLModule()  # Uses CoT + fallbacks
    optimized_metrics = evaluate_module(optimized_module, train_examples, db)
    console.print(f"✓ Optimized: {optimized_metrics['valid_count']}/{optimized_metrics['total']} valid queries\n")
    
    # Display results table
    table = Table(title="DSPy Optimization Results", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan", width=30)
    table.add_column("Baseline (Predict)", style="yellow", justify="right")
    table.add_column("Optimized (CoT)", style="green", justify="right")
    table.add_column("Δ Change", style="blue", justify="right")
    
    # Valid SQL Rate
    baseline_rate = baseline_metrics['valid_sql_rate']
    optimized_rate = optimized_metrics['valid_sql_rate']
    delta_rate = (optimized_rate - baseline_rate) * 100
    
    table.add_row(
        "Valid SQL Rate",
        f"{baseline_rate:.1%}",
        f"{optimized_rate:.1%}",
        f"+{delta_rate:.1f}%" if delta_rate >= 0 else f"{delta_rate:.1f}%"
    )
    
    table.add_row(
        "Valid Queries",
        f"{baseline_metrics['valid_count']}/{baseline_metrics['total']}",
        f"{optimized_metrics['valid_count']}/{optimized_metrics['total']}",
        f"+{optimized_metrics['valid_count'] - baseline_metrics['valid_count']}"
    )
    
    table.add_row(
        "Syntax Errors",
        f"{baseline_metrics['syntax_errors']}",
        f"{optimized_metrics['syntax_errors']}",
        f"{optimized_metrics['syntax_errors'] - baseline_metrics['syntax_errors']}"
    )
    
    table.add_row(
        "Execution Errors",
        f"{baseline_metrics['execution_errors']}",
        f"{optimized_metrics['execution_errors']}",
        f"{optimized_metrics['execution_errors'] - baseline_metrics['execution_errors']}"
    )
    
    console.print(table)
    
    # Summary
    if delta_rate > 0:
        console.print(f"\n[bold green]✓ Improvement: +{delta_rate:.1f}% valid SQL rate[/bold green]")
    else:
        console.print(f"\n[bold yellow]⚠ Change: {delta_rate:.1f}% valid SQL rate[/bold yellow]")
    
    console.print("\n[bold]Optimizations Applied:[/bold]")
    console.print("  1. ChainOfThought reasoning for step-by-step SQL construction")
    console.print("  2. Structured constraint parsing (dates, categories, formulas)")
    console.print("  3. Fallback SQL generation for common query patterns")
    console.print("  4. Automatic SQL cleaning and error fixes")
    console.print("  5. Enhanced prompting with explicit instructions")
    
    # Show detailed results if requested
    console.print("\n[dim]Detailed Results:[/dim]")
    detail_table = Table(show_header=True, header_style="bold")
    detail_table.add_column("Question", style="cyan", width=40)
    detail_table.add_column("Baseline", style="yellow", width=15)
    detail_table.add_column("Optimized", style="green", width=15)
    
    for i, (base_res, opt_res) in enumerate(zip(baseline_metrics['results'], optimized_metrics['results'])):
        detail_table.add_row(
            base_res['question'],
            base_res['status'],
            opt_res['status']
        )
    
    console.print(detail_table)
    
    console.print("\n[dim italic]Note: For production use, consider DSPy's BootstrapFewShot or MIPROv2")
    console.print("with a larger training set (50-100+ examples) for further improvements.[/dim italic]")


if __name__ == '__main__':
    main()