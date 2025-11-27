"""Main entrypoint for the hybrid retail analytics agent."""
import json
import click
import dspy
from pathlib import Path
from rich.console import Console
from rich.progress import track

from agent.graph_hybrid import HybridAgent
from agent.dspy_signatures import RouterModule, NLToSQLModule, SynthesizerModule
from agent.rag.retrieval import TFIDFRetriever
from agent.tools.sqlite_tool import SQLiteTool

console = Console()


def setup_dspy():
    """Configure DSPy with local Ollama model."""
    try:
        # Try the newer DSPy API first
        lm = dspy.LM(
            model="ollama/phi3.5:3.8b-mini-instruct-q4_K_M",
            api_base="http://localhost:11434",
            max_tokens=500,
            temperature=0.1
        )
    except:
        # Fallback to older API
        try:
            from dspy.clients import Ollama
            lm = Ollama(
                model="phi3.5:3.8b-mini-instruct-q4_K_M",
                max_tokens=500,
                temperature=0.1
            )
        except:
            # Last resort
            lm = dspy.OpenAI(
                model="ollama/phi3.5:3.8b-mini-instruct-q4_K_M",
                api_base="http://localhost:11434",
                api_key="dummy",
                max_tokens=500,
                temperature=0.1
            )
    dspy.settings.configure(lm=lm)


def create_agent():
    """Initialize all components and create the agent."""
    console.print("[bold blue]Initializing agent components...[/bold blue]")
    
    # Initialize components
    retriever = TFIDFRetriever(docs_dir="docs")
    db_tool = SQLiteTool(db_path="data/northwind.sqlite")
    
    # Initialize DSPy modules
    router = RouterModule()
    sql_gen = NLToSQLModule()
    synthesizer = SynthesizerModule()
    
    # Create agent
    agent = HybridAgent(
        router_module=router,
        sql_module=sql_gen,
        synth_module=synthesizer,
        retriever=retriever,
        db_tool=db_tool
    )
    
    console.print("[bold green]✓ Agent initialized[/bold green]")
    return agent


@click.command()
@click.option('--batch', required=True, help='Input JSONL file with questions')
@click.option('--out', required=True, help='Output JSONL file for results')
def main(batch: str, out: str):
    """Run the hybrid agent on a batch of questions."""
    console.print("[bold]Retail Analytics Copilot[/bold]\n")
    
    # Setup DSPy
    setup_dspy()
    
    # Create agent
    agent = create_agent()
    
    # Load questions
    batch_path = Path(batch)
    if not batch_path.exists():
        console.print(f"[bold red]Error: {batch} not found[/bold red]")
        return
    
    questions = []
    with open(batch_path, 'r') as f:
        for line in f:
            questions.append(json.loads(line))
    
    console.print(f"\n[bold]Processing {len(questions)} questions...[/bold]\n")
    
    # Process each question
    results = []
    for q in track(questions, description="Processing"):
        console.print(f"\n[cyan]Q: {q['question']}[/cyan]")
        
        try:
            result = agent.run(
                question=q['question'],
                format_hint=q['format_hint']
            )
            
            output = {
                'id': q['id'],
                'final_answer': result['final_answer'],
                'sql': result['sql'],
                'confidence': result['confidence'],
                'explanation': result['explanation'],
                'citations': result['citations']
            }
            
            console.print(f"[green]A: {result['final_answer']}[/green]")
            console.print(f"[dim]Citations: {', '.join(result['citations'])}[/dim]")
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            output = {
                'id': q['id'],
                'final_answer': None,
                'sql': '',
                'confidence': 0.0,
                'explanation': f"Error: {str(e)}",
                'citations': []
            }
        
        results.append(output)
    
    # Write outputs
    out_path = Path(out)
    with open(out_path, 'w') as f:
        for result in results:
            f.write(json.dumps(result) + '\n')
    
    console.print(f"\n[bold green]✓ Results written to {out}[/bold green]")


if __name__ == '__main__':
    main()