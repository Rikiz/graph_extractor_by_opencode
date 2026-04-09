"""
Multi-repo code graph builder and cross-repo call analyzer.

Two-phase system:
  Phase 1: Build single-repo graphs (independent)
  Phase 2: Analyze cross-repo calls (depends on Phase 1)
"""

from .core.graph_builder import GraphBuilder
from .core.repo_manager import RepoGroup
from .core.cross_analyzer import CrossAnalyzer
from .writer.neo4j_writer import Neo4jWriter
from .config.neo4j_config import Neo4jConfig

__version__ = "1.0.0"

__all__ = ["GraphBuilder", "RepoGroup", "CrossAnalyzer", "Neo4jWriter", "Neo4jConfig"]
