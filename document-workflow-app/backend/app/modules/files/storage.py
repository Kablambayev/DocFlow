from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings


class StorageProvider(ABC):
    @abstractmethod
    def save(self, file_content: bytes, storage_key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def open(self, storage_key: str) -> BinaryIO:
        raise NotImplementedError

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        raise NotImplementedError


class LocalStorageProvider(StorageProvider):
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.root_path.mkdir(parents=True, exist_ok=True)

    def _resolve(self, storage_key: str) -> Path:
        path = (self.root_path / storage_key).resolve()
        root = self.root_path.resolve()
        if root not in path.parents and path != root:
            raise ValueError("Invalid storage key")
        return path

    def save(self, file_content: bytes, storage_key: str) -> None:
        path = self._resolve(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(file_content)

    def open(self, storage_key: str) -> BinaryIO:
        return self._resolve(storage_key).open("rb")

    def delete(self, storage_key: str) -> None:
        path = self._resolve(storage_key)
        if path.exists():
            path.unlink()

    def exists(self, storage_key: str) -> bool:
        return self._resolve(storage_key).exists()

    def path_for(self, storage_key: str) -> Path:
        return self._resolve(storage_key)


def get_storage_provider() -> StorageProvider:
    if settings.file_storage_provider != "local":
        raise ValueError(f"Unsupported file storage provider: {settings.file_storage_provider}")
    return LocalStorageProvider(settings.local_storage_path)
