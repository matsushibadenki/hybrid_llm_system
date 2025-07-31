# /hybrid_llm_system/domain/schemas.py
# システムのデータ構造定義ファイル

from dataclasses import dataclass, field
# ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↓修正開始◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
from typing import List, Optional, Dict, Any, Union, TYPE_CHECKING
from llama_cpp import Llama

# TYPE_CHECKINGブロックはmypy実行時にのみインポートされる
if TYPE_CHECKING:
    from diffusers import DiffusionPipeline
# ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↑修正終わり◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️

@dataclass
class ExpertModel:
    """
    各エキスパートモデルの設定と状態を管理するデータクラス
    """
    name: str
    description: str
    model_path: Optional[str] # GGUFモデルのパス
    model_id: Optional[str]   # 拡散モデルのHugging Face ID
    chat_format: str
    system_prompt: str
    keywords: List[str] = field(default_factory=list)
    # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↓修正開始◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
    # 循環インポートを避けるため、型を文字列で指定
    instance: Optional[Union[Llama, "DiffusionPipeline"]] = None
    # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↑修正終わり◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
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