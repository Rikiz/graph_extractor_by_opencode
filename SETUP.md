# Setup Guide

Quick setup instructions to get started.

---

## Prerequisites

- Python 3.9 or higher
- Neo4j 5.0 or higher
- Git

---

## Step 1: Install Neo4j

### Option A: Docker (Recommended)

```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  neo4j:5-community
```

### Option B: Local Installation

Download from: https://neo4j.com/download/

---

## Step 2: Clone and Install

```bash
# Clone repository
git clone https://github.com/Rikiz/graph_extractor_by_opencode.git
cd graph_extractor_by_opencode

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: .\venv\Scripts\activate  # Windows

# Install
pip install -e .

# Install dev dependencies (optional)
pip install -e ".[dev]"
```

---

## Step 3: Configure Neo4j

```bash
# Set environment variables
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="password123"
```

Or create `neo4j_config.json`:

```json
{
  "uri": "bolt://localhost:7687",
  "user": "neo4j",
  "password": "password123"
}
```

---

## Step 4: Run Tests

```bash
# Run unit tests
make test

# Or directly
pytest tests/ -v
```

---

## Step 5: Try the Example

```bash
# See examples directory
python examples/basic_usage.py
```

---

## Next Steps

- Read [README.md](README.md) for full documentation
- See [examples/](examples/) for usage examples
- Check [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for design details

---

## Troubleshooting

### Neo4j Connection Error

```
Error: Unable to connect to Neo4j
```

**Solution:**
1. Ensure Neo4j is running: `docker ps` or check Neo4j Desktop
2. Verify credentials are correct
3. Check if port 7687 is accessible

### Import Error

```
ModuleNotFoundError: No module named 'repo_analyzer'
```

**Solution:**
```bash
# Make sure you installed in editable mode
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Permission Error

```
PermissionError: [Errno 13] Permission denied
```

**Solution:**
```bash
# Use virtual environment
python -m venv venv
source venv/bin/activate
pip install -e .
```

---

## Need Help?

- [Open an issue](https://github.com/Rikiz/graph_extractor_by_opencode/issues)
- [Read the docs](README.md)
