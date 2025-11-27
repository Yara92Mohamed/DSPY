# Retail Analytics Copilot

A hybrid AI agent that combines retrieval-augmented generation (RAG) with SQL query generation to answer complex retail analytics questions. Built with DSPy, LangGraph, and local LLMs via Ollama.

## Overview

This project implements an intelligent retail analytics assistant that:
- Routes queries to the appropriate processing pipeline (RAG, SQL, or hybrid)
- Extracts business constraints from documentation (dates, KPIs, policies)
- Generates and executes SQLite queries for quantitative analysis
- Synthesizes answers with proper citations and confidence scores

## Features

- **Intelligent Query Routing**: Automatically determines whether to use document retrieval, database queries, or both
- **Template-Based SQL Generation**: Reliable query generation using templates with LLM fallback
- **Constraint Extraction**: Parses marketing calendars, KPI definitions, and policies from documentation
- **Multi-Source Citations**: Tracks and reports sources from both documents and database tables
- **Error Recovery**: Automatic SQL repair and validation with retry logic
- **Local LLM Integration**: Runs entirely offline using Ollama (Phi-3.5 model)

## Project Structure

```
retail-analytics-copilot/
│
├── agent/
│   ├── __init__.py
│   ├── graph_hybrid.py              # Main agent orchestration with LangGraph
│   ├── dspy_signatures.py           # DSPy signatures and modules
│   │
│   ├── rag/
│   │   ├── __init__.py
│   │   └── retrieval.py             # TF-IDF document retriever
│   │
│   └── tools/
│       ├── __init__.py
│       └── sqlite_tool.py           # Enhanced SQLite database interface
│
├── docs/                            # Knowledge base documents
│   ├── catalog.md                   # Product catalog information
│   ├── kpi_definitions.md           # KPI formulas and definitions
│   ├── marketing_calendar.md        # Campaign dates and details
│   └── product_policy.md            # Return policies and guidelines
│
├── data/
│   └── northwind.sqlite             # Northwind sample database
│
├── tests/                           # Testing and validation scripts
│   ├── inspect_database.py          # Database structure inspector
│   ├── test_agent_debug.py          # Agent debugging utilities
│   ├── test_sql_direct.py           # Direct SQL query testing
│   └── validate_output.py           # Output validation suite
│
├── run_agent_hybrid.py              # Main CLI entrypoint
├── optimize_dspy.py                 # DSPy optimization experiments
├── sample_questions_hybrid_eval.jsonl  # Evaluation questions
├── outputs_final1.jsonl             # Expected outputs
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

## Architecture

### Component Flow

```
User Question
     │
     ▼
┌─────────────────┐
│ RouterModule    │ ─── Determines: RAG / SQL / Hybrid
└────────┬────────┘
         │
         ├─────────────────┬─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Retrieve     │  │ Plan & SQL   │  │ Both         │
│ Documents    │  │ Generation   │  │ Pipelines    │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       │                 ▼                 │
       │        ┌──────────────┐          │
       │        │ Execute SQL  │          │
       │        └──────┬───────┘          │
       │               │                  │
       │               ▼                  │
       │        ┌──────────────┐          │
       │        │ Validate     │          │
       │        └──────┬───────┘          │
       │               │                  │
       └───────────────┴──────────────────┘
                       │
                       ▼
              ┌──────────────┐
              │ Synthesize   │
              │ Final Answer │
              └──────────────┘
```

### Key Components

**1. RouterModule** (`dspy_signatures.py`)
- Classifies queries as `rag`, `sql`, or `hybrid`
- Uses heuristics and DSPy Chain-of-Thought reasoning

**2. TFIDFRetriever** (`rag/retrieval.py`)
- TF-IDF based document retrieval
- Chunks markdown documents from `docs/` directory
- Returns top-k relevant passages with similarity scores

**3. TemplateSQLGenerator** (`graph_hybrid.py`)
- Template-based SQL generation for common patterns
- Fallback to DSPy NLToSQLModule for complex queries
- Automatic date range extraction and constraint parsing

**4. SQLiteTool** (`tools/sqlite_tool.py`)
- Enhanced SQLite interface with error handling
- Automatic query repair for common issues
- Schema introspection and validation

**5. HybridAgent** (`graph_hybrid.py`)
- LangGraph-based state machine orchestration
- Multi-step workflow with error recovery
- Citation tracking across documents and database

## Installation

### Prerequisites

- Python 3.9+
- [Ollama](https://ollama.ai/) installed and running
- Phi-3.5 model downloaded: `ollama pull phi3.5:3.8b-mini-instruct-q4_K_M`

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd retail-analytics-copilot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify Ollama is running
curl http://localhost:11434/api/tags
```

### Database Setup

The project uses the Northwind sample database. Ensure `data/northwind.sqlite` exists with the following tables:
- Orders
- Order Details (note: quoted name)
- Products
- Categories
- Customers
- Employees
- Suppliers
- Shippers

## Usage

### Basic Usage

```bash
# Run agent on evaluation questions
python run_agent_hybrid.py \
  --batch sample_questions_hybrid_eval.jsonl \
  --out outputs_hybrid.jsonl
```

### Example Questions

The agent can handle various query types:

**RAG-only** (from documents):
```
"According to the product policy, what is the return window for unopened Beverages?"
```

**SQL-only** (from database):
```
"What are the top 3 products by total revenue all-time?"
```

**Hybrid** (both sources):
```
"During 'Summer Beverages 2017', which category had the highest quantity sold?"
"What was the AOV during 'Winter Classics 2017'?"
```

### Testing & Validation

```bash
# Inspect database structure
python tests/inspect_database.py

# Test SQL queries directly
python tests/test_sql_direct.py

# Debug agent behavior
python tests/test_agent_debug.py

# Validate outputs against expected answers
python tests/validate_output.py

# Run DSPy optimization experiments
python optimize_dspy.py
```

## Configuration

### DSPy Settings

The agent uses Ollama with these default settings (in `run_agent_hybrid.py`):

```python
lm = dspy.LM(
    model="ollama/phi3.5:3.8b-mini-instruct-q4_K_M",
    api_base="http://localhost:11434",
    max_tokens=500,
    temperature=0.1
)
```

### SQL Templates

Templates are defined in `TemplateSQLGenerator.generate()` for:
- Category quantity by date range
- Average Order Value (AOV)
- Top N products by revenue
- Category revenue filtering
- Customer gross margin

## Output Format

Each result includes:

```json
{
  "id": "question_id",
  "final_answer": <typed_answer>,
  "sql": "generated SQL query",
  "confidence": 0.8,
  "explanation": "Brief explanation",
  "citations": ["source1", "source2"]
}
```

## Evaluation Metrics

The agent is evaluated on:
- **Correctness**: Exact match with expected answers
- **Valid SQL Rate**: Percentage of executable queries
- **Citation Quality**: Proper source attribution
- **Confidence Calibration**: Alignment with actual performance

Expected performance (from `outputs_final1.jsonl`):
- 6/6 questions answered correctly
- 100% valid SQL generation
- Average confidence: 0.8

## Troubleshooting

### Common Issues

**1. Ollama Connection Error**
```
Error: Connection refused to localhost:11434
```
**Solution**: Start Ollama service: `ollama serve`

**2. SQL Syntax Errors**
```
Error: no such table: Order Details
```
**Solution**: The table name requires quotes: `"Order Details"`

**3. Date Format Issues**
```
Error: type mismatch in date comparison
```
**Solution**: Use `date(OrderDate)` wrapper for comparisons

**4. No Results from SQL**
```
Warning: Query returned 0 rows
```
**Solution**: Check date ranges in `docs/marketing_calendar.md` - the database may use different years (e.g., 1997 instead of 2017)

### Debug Mode

Enable detailed logging:

```python
agent.debug = True  # In graph_hybrid.py
```

## Extending the Agent

### Adding New Query Templates

Edit `TemplateSQLGenerator.generate()`:

```python
# Template for new pattern
if 'your_keyword' in q_lower:
    return f"""
    SELECT ...
    FROM ...
    WHERE ...
    """
```

### Adding New Documents

1. Create markdown file in `docs/`
2. Retriever automatically indexes on initialization
3. No code changes needed

### Custom KPI Formulas

Update `docs/kpi_definitions.md`:

```markdown
## Your New KPI
- Formula: SUM(metric1 * metric2)
- Notes: Calculation details
```

## Performance Optimization

### DSPy Optimization

Run optimization experiments:

```bash
python optimize_dspy.py
```

This compares:
- Baseline (zero-shot Predict)
- Optimized (ChainOfThought + templates)

Expected improvement: ~30-50% in valid SQL rate

### Caching

The agent caches:
- Database schema (`_schema_cache`)
- Date format (`_date_format_cache`)
- TF-IDF vectorizer (after initialization)

## Contributing

Areas for contribution:
- Additional SQL templates for common patterns
- Enhanced constraint extraction from natural language
- Multi-database support beyond Northwind
- Advanced DSPy optimization (BootstrapFewShot, MIPROv2)
- Web interface for interactive queries

## License

[Your License Here]

## Acknowledgments

- Built with [DSPy](https://github.com/stanfordnlp/dspy)
- Orchestrated with [LangGraph](https://github.com/langchain-ai/langgraph)
- Powered by [Ollama](https://ollama.ai/)
- Sample data from [Northwind Database](https://github.com/jpwhite3/northwind-SQLite3)