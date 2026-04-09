# Examples

This directory contains example usage and configurations.

---

## Contents

- `basic_usage.py` - Basic usage examples
- `advanced_usage.py` - Advanced scenarios
- `neo4j_config.example.json` - Example Neo4j configuration

---

## Quick Start

```bash
# Copy example config
cp neo4j_config.example.json neo4j_config.json

# Edit with your credentials
# Run example
python basic_usage.py
```

---

## Example Neo4j Config

```json
{
  "uri": "bolt://localhost:7687",
  "user": "neo4j",
  "password": "your_password",
  "database": "neo4j"
}
```

---

## Sample Cypher Queries

### View call chains

```cypher
MATCH (url:FrontendUrl)-[c:CALLS]->(route:GatewayRoute)-[r:ROUTES_TO]->(api:BackendApi)
RETURN 
  url.raw_url as frontend_url,
  route.full_path as gateway_path,
  api.class_name + '.' + api.method_name as backend_handler,
  c.confidence as fe_confidence,
  r.confidence as gw_confidence
ORDER BY c.confidence DESC, r.confidence DESC
LIMIT 20;
```

### Find unmatched frontend URLs

```cypher
MATCH (url:FrontendUrl)
WHERE NOT (url)-[:CALLS]->(:GatewayRoute)
RETURN url.raw_url, url.file_path, url.line_number
ORDER BY url.file_path;
```

### Statistics by repo

```cypher
MATCH (n)
WHERE n.repo IS NOT NULL
RETURN n.repo as repo, labels(n)[0] as type, count(*) as count
ORDER BY repo, type;
```

### High-confidence matches only

```cypher
MATCH ()-[r:CALLS|ROUTES_TO]->()
WHERE r.confidence >= 0.8
RETURN r.match_type, count(*) as count;
```
