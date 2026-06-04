from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict
import json


@dataclass
class Report:
    """Модель отчета"""
    id: int = None
    title: str = ""
    report_type: str = ""  # 'yearly', 'monthly', 'comparison'
    data: Dict = None
    created_at: datetime = None
    filters: Dict = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.filters is None:
            self.filters = {}
        if self.created_at is None:
            self.created_at = datetime.now()
    
    def to_json(self) -> str:
        """Экспорт в JSON"""
        return json.dumps({
            "id": self.id,
            "title": self.title,
            "report_type": self.report_type,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "filters": self.filters
        }, ensure_ascii=False)