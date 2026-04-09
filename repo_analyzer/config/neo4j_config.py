import os
import json
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


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
        with open(config_path, "r") as f:
            config = json.load(f)

        return cls(
            uri=config.get("uri", "bolt://localhost:7687"),
            user=config.get("user", "neo4j"),
            password=config.get("password", "password"),
            database=config.get("database", "neo4j"),
        )

    @classmethod
    def auto_detect(cls) -> "Neo4jConfig":
        """
        自动检测配置（优先级）:
        1. 环境变量
        2. 当前目录的 neo4j_config.json
        3. 默认值
        """
        # 优先使用环境变量
        if os.getenv("NEO4J_URI") and os.getenv("NEO4J_PASSWORD"):
            return cls.from_env()

        # 查找配置文件
        config_paths = [
            Path.cwd() / "neo4j_config.json",
            Path.cwd() / "config" / "neo4j_config.json",
            Path(__file__).parent.parent.parent / "neo4j_config.json",
        ]

        for config_path in config_paths:
            if config_path.exists():
                return cls.from_file(str(config_path))

        # 回退到环境变量（使用默认值）
        return cls.from_env()
