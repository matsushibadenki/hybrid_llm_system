# /hybrid_llm_system/domain/schemas.py
# システムのデータ構造定義ファイル

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from llama_cpp import Llama

@dataclass
class ExpertModel:
    """
    各エキスパートモデルの設定と状態を管理するデータクラス
    """
    name: str
    description: str
    model_path: str
    chat_format: str
    system_prompt: str
    keywords: List[str] = field(default_factory=list)
    instance: Optional[Llama] = None
    is_loaded: bool = False

@dataclass
class SubTask:
    """
    分解されたサブタスクを管理するデータクラス
    """
    task_id: int
    description: str
    expert_name: str
    dependencies: List[int] = field(default_factory=list)
    result: Optional[str] = None
    status: str = "pending" # pending, in_progress, completed, failed

@dataclass
class Plan:
    """
    実行計画全体を管理するデータクラス
    """
    original_prompt: str
    tasks: List[SubTask] = field(default_factory=list)