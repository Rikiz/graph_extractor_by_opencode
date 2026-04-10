"""
Neo4j 配置管理

支持多种配置方式（优先级从高到低）:
1. 环境变量 (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE)
2. .env 文件
3. neo4j_config.json 文件
4. 默认值
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 尝试导入 pydantic
try:
    from pydantic_settings import BaseSettings

    PYDANTIC_V2 = True
except ImportError:
    try:
        from pydantic import BaseSettings

        PYDANTIC_V2 = False
    except ImportError:
        BaseSettings = None
        PYDANTIC_V2 = False


if BaseSettings:
    # 使用 Pydantic BaseSettings
    class Neo4jConfig(BaseSettings):
        """Neo4j 配置，支持环境变量和 .env 文件"""

        uri: str = "bolt://localhost:7687"
        user: str = "neo4j"
        password: str = "password"
        database: str = "neo4j"

        if PYDANTIC_V2:
            # Pydantic v2 语法
            model_config = {
                "env_prefix": "NEO4J_",
                "env_file": ".env",
                "env_file_encoding": "utf-8",
                "extra": "ignore",
            }
        else:
            # Pydantic v1 语法
            class Config:
                env_prefix = "NEO4J_"
                env_file = ".env"
                env_file_encoding = "utf-8"
                extra = "ignore"

        @classmethod
        def auto_detect(cls) -> "Neo4jConfig":
            """
            自动检测配置（优先级）:
            1. 环境变量 / .env 文件 (通过 BaseSettings 自动处理)
            2. neo4j_config.json 文件
            3. 默认值
            """
            # 尝试加载 .env 文件
            cls._load_dotenv()

            # Pydantic BaseSettings 自动从环境变量读取
            return cls()

        @staticmethod
        def _load_dotenv():
            """加载 .env 文件"""
            try:
                from dotenv import load_dotenv

                env_paths = [
                    Path.cwd() / ".env",
                    Path(__file__).parent.parent.parent / ".env",
                ]

                for env_path in env_paths:
                    if env_path.exists():
                        logger.debug(f"Loading .env from {env_path}")
                        load_dotenv(env_path, override=True)
                        return
            except ImportError:
                logger.debug("python-dotenv not installed, skipping .env loading")

        @classmethod
        def from_file(cls, config_path: str) -> "Neo4jConfig":
            """从 JSON 配置文件加载"""
            logger.info(f"Loading config from {config_path}")
            with open(config_path, "r") as f:
                config = json.load(f)
            return cls(**config)

        @classmethod
        def from_env(cls) -> "Neo4jConfig":
            """从环境变量加载"""
            cls._load_dotenv()
            return cls()

else:
    # Fallback: 不使用 pydantic
    from dataclasses import dataclass

    @dataclass
    class Neo4jConfig:
        """Neo4j 配置（无 pydantic 版本）"""

        uri: str = "bolt://localhost:7687"
        user: str = "neo4j"
        password: str = "password"
        database: str = "neo4j"

        @classmethod
        def auto_detect(cls) -> "Neo4jConfig":
            """
            自动检测配置（优先级）:
            1. 环境变量 / .env 文件
            2. neo4j_config.json 文件
            3. 默认值
            """
            # 加载 .env 文件
            cls._load_dotenv()

            # 检查环境变量
            if os.getenv("NEO4J_URI") and os.getenv("NEO4J_PASSWORD"):
                logger.info("Using configuration from environment variables")
                return cls.from_env()

            # 查找配置文件
            config_paths = [
                Path.cwd() / "neo4j_config.json",
                Path.cwd() / "config" / "neo4j_config.json",
                Path(__file__).parent.parent.parent / "neo4j_config.json",
            ]

            for config_path in config_paths:
                if config_path.exists():
                    logger.info(f"Using configuration from {config_path}")
                    return cls.from_file(str(config_path))

            # 使用默认值
            logger.warning("Using default Neo4j configuration (bolt://localhost:7687)")
            return cls()

        @staticmethod
        def _load_dotenv():
            """加载 .env 文件"""
            try:
                from dotenv import load_dotenv

                env_paths = [
                    Path.cwd() / ".env",
                    Path(__file__).parent.parent.parent / ".env",
                ]

                for env_path in env_paths:
                    if env_path.exists():
                        logger.debug(f"Loading .env from {env_path}")
                        load_dotenv(env_path, override=True)
                        return
            except ImportError:
                logger.debug("python-dotenv not installed, skipping .env loading")

        @classmethod
        def from_file(cls, config_path: str) -> "Neo4jConfig":
            """从 JSON 配置文件加载"""
            logger.info(f"Loading config from {config_path}")
            with open(config_path, "r") as f:
                config = json.load(f)
            return cls(
                uri=config.get("uri", cls.uri),
                user=config.get("user", cls.user),
                password=config.get("password", cls.password),
                database=config.get("database", cls.database),
            )

        @classmethod
        def from_env(cls) -> "Neo4jConfig":
            """从环境变量加载"""
            return cls(
                uri=os.getenv("NEO4J_URI", cls.uri),
                user=os.getenv("NEO4J_USER", cls.user),
                password=os.getenv("NEO4J_PASSWORD", cls.password),
                database=os.getenv("NEO4J_DATABASE", cls.database),
            )
