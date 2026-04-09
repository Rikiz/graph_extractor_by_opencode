from abc import ABC, abstractmethod
from typing import List
from ..models.entities import BackendApi, GatewayRoute, FrontendUrl, MappingRule


class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: str, repo: str) -> List:
        pass

    def get_file_content(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def get_file_lines(self, file_path: str) -> List[str]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.readlines()
