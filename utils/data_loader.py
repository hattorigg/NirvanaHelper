import json
import os
import random
from typing import Any, Optional

class DataLoader:
    """Загружает JSON-файлы и кеширует их в памяти"""
    
    _cache: dict = {}
    
    @classmethod
    def load(cls, filepath: str) -> Any:
        """Загружает JSON-файл (или берёт из кеша)"""
        if filepath not in cls._cache:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    cls._cache[filepath] = json.load(f)
            else:
                cls._cache[filepath] = [] if filepath.endswith('.json') else {}
        return cls._cache[filepath]
    
    @classmethod
    def get_random(cls, filepath: str) -> Optional[Any]:
        """Возвращает случайный элемент из списка"""
        data = cls.load(filepath)
        if isinstance(data, list) and data:
            return random.choice(data)
        elif isinstance(data, dict) and data:
            return random.choice(list(data.values()))
        return None
    
    @classmethod
    def save(cls, filepath: str, data: Any) -> None:
        """Сохраняет данные в JSON-файл"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        cls._cache[filepath] = data
