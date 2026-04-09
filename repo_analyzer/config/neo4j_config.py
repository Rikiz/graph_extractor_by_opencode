import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Neo4jConfig:
    uri: str
    user: str
    password: str
    database: str = "neo4j"

    @classmethod
    def from_env(cls) -> "Neo4jConfig":
        return cls(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password"),
            database=os.getenv("NEO4J_DATABASE", "neo4j"),
        )

    @classmethod
    def from_file(cls, config_path: str) -> "Neo4jConfig":
        import json

        with open(config_path, "r") as f:
            config = json.load(f)

        return cls(
            uri=config.get("uri", "bolt://localhost:7687"),
            user=config.get("user", "neo4j"),
            password=config.get("password", "password"),
            database=config.get("database", "neo4j"),
        )
