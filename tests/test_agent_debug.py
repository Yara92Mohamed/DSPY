"""Debug script to identify why agent returns None for SQL queries."""
import dspy
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from agent.dspy_signatures import RouterModule, NLToSQLModule
from agent.rag.retrieval import TFIDFRetriever
from agent.tools.sqlite_tool import SQLiteTool
from agent.graph_hybrid import HybridAgent

console = Console()


def setup_dspy():
    """Configure DSPy."""
    try:
        lm = dspy.LM(
            model="ollama/phi3.5:3.8b-mini-instruct-q4_K_M",
            api_base="http://localhost:11434",
            max_tokens=800,
            temperature=0.1
        )
    except:
        try:
            from dspy.clients import Ollama
            lm = Ollama(
                model="phi3.5:3.8b-mini-instruct-q4_K_M",
                max_tokens=800,
                temperature=0.1
            )
        except:
            lm = dspy.OpenAI(
                model="ollama/phi3.5:3.8b-mini-instruct-q4_K_M",
                api_base="http://localhost:11434",
                api_key="dummy",
                max_tokens=800,
                temperature=0.1
            )
    dspy.settings.configure(lm=lm)


def debug_question_2():
    """Debug: Top category by quantity in Summer 2017."""
    console.print("\n[bold cyan]Debugging Question 2: Top category in Summer 2017[/bold cyan]")
    
    # Initialize components
    retriever = TFIDFRetriever("docs")
    db = SQLiteTool()
    router = RouterModule()
    sql_gen = NLToSQLModule()
    
    question = "During 'Summer Beverages 2017' as defined in the marketing calendar, which product category had the highest total quantity sold? Return {category:str, quantity:int}."
    
    # Step 1: Check routing
    console.print(f"\n[yellow]1. Routing:[/yellow]")
    route = router(question)
    console.print(f"   Route: {route}")
    
    # Step 2: Document retrieval
    console.print(f"\n[yellow]2. Document Retrieval:[/yellow]")
    docs = retriever.retrieve("Summer Beverages 2017", top_k=5)
    for doc in docs:
        console.print(f"   - {doc['id']} (score: {doc['score']:.3f})")
        if '2017-06-01' in doc['content']:
            console.print(f"     [green]✓ Contains dates![/green]")
            console.print(f"     Content: {doc['content'][:100]}...")
    
    # Step 3: Constraint extraction (simulate plan_node)
    console.print(f"\n[yellow]3. Constraint Extraction:[/yellow]")
    import re
    constraints = []
    
    for doc in docs:
        content = doc['content']
        
        # Date extraction
        date_patterns = [
            r'Dates?:\s*(\d{4}-\d{2}-\d{2})\s*(?:to|through|-)\s*(\d{4}-\d{2}-\d{2})',
            r'(\d{4}-\d{2}-\d{2})\s*(?:to|through|-)\s*(\d{4}-\d{2}-\d{2})',
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if len(match) == 2:
                    constraints.append(f"START_DATE:{match[0]}")
                    constraints.append(f"END_DATE:{match[1]}")
                    console.print(f"   [green]✓ Found dates: {match[0]} to {match[1]}[/green]")
    
    constraint_str = ' | '.join(constraints)
    console.print(f"   Constraints: {constraint_str}")
    
    # Step 4: SQL Generation
    console.print(f"\n[yellow]4. SQL Generation:[/yellow]")
    schema = db.get_schema()
    
    sql = sql_gen(
        question=question,
        schema=schema,
        constraints=constraint_str + " | Use date(OrderDate) | Sum quantities by category"
    )
    
    console.print(Panel(Syntax(sql, "sql", theme="monokai"), title="Generated SQL"))
    
    # Step 5: SQL Execution
    console.print(f"\n[yellow]5. SQL Execution:[/yellow]")
    result = db.execute_query(sql)
    
    if result['success']:
        console.print(f"   [green]✓ Success![/green]")
        console.print(f"   Columns: {result['columns']}")
        console.print(f"   Rows: {result['rows']}")
        console.print(f"   Row count: {result['row_count']}")
    else:
        console.print(f"   [red]✗ Failed![/red]")
        console.print(f"   Error: {result['error']}")
        
        # Try manual fix
        console.print(f"\n[yellow]6. Attempting Manual Fix:[/yellow]")
        
        # Check if dates are the issue
        test_sql = """
SELECT COUNT(*) FROM Orders 
WHERE date(OrderDate) BETWEEN '2017-06-01' AND '2017-06-30'
        """
        test_result = db.execute_query(test_sql)
        
        if test_result['success']:
            console.print(f"   Orders in June 2017: {test_result['rows'][0][0]}")
        else:
            console.print(f"   [red]Date query also failed: {test_result['error']}[/red]")
    
    # Step 6: Check answer parsing
    if result['success'] and result['rows']:
        console.print(f"\n[yellow]6. Answer Parsing:[/yellow]")
        
        try:
            row = result['rows'][0]
            answer = {
                'category': str(row[0]), 
                'quantity': int(float(row[1]))
            }
            console.print(f"   [green]✓ Parsed: {answer}[/green]")
        except Exception as e:
            console.print(f"   [red]✗ Parse failed: {e}[/red]")


def debug_full_agent():
    """Debug the full agent run."""
    console.print("\n[bold cyan]Debugging Full Agent Run[/bold cyan]")
    
    # Initialize agent
    retriever = TFIDFRetriever("docs")
    db = SQLiteTool()
    router = RouterModule()
    sql_gen = NLToSQLModule()
    from agent.dspy_signatures import SynthesizerModule
    synthesizer = SynthesizerModule()
    
    agent = HybridAgent(
        router_module=router,
        sql_module=sql_gen,
        synth_module=synthesizer,
        retriever=retriever,
        db_tool=db
    )
    
    # Test question
    question = "During 'Summer Beverages 2017' as defined in the marketing calendar, which product category had the highest total quantity sold? Return {category:str, quantity:int}."
    format_hint = "{category:str, quantity:int}"
    
    console.print(f"\n[yellow]Question:[/yellow] {question}")
    console.print(f"[yellow]Format:[/yellow] {format_hint}")
    
    # Run agent
    console.print(f"\n[yellow]Running agent...[/yellow]")
    result = agent.run(question, format_hint)
    
    console.print(f"\n[cyan]Results:[/cyan]")
    console.print(f"  Answer: {result['final_answer']}")
    console.print(f"  SQL: {result['sql'][:100]}..." if result['sql'] else "  SQL: None")
    console.print(f"  Confidence: {result['confidence']}")
    console.print(f"  Explanation: {result['explanation']}")
    console.print(f"  Citations: {result['citations']}")
    
    console.print(f"\n[cyan]Execution Trace:[/cyan]")
    for step in result['trace']:
        console.print(f"  - {step}")


def main():
    """Run all debug tests."""
    console.print("[bold]Agent Debugging Suite[/bold]")
    console.print("=" * 70)
    
    setup_dspy()
    
    # Debug individual components
    debug_question_2()
    
    # Debug full agent
    debug_full_agent()
    
    console.print("\n[bold green]Debug complete![/bold green]")
    console.print("\nLook for [red]✗ Failed[/red] markers above to identify issues.")


if __name__ == '__main__':
    main()