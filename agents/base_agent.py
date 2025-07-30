# /hybrid_llm_system/agents/base_agent.py
# 全エージェントの基底クラス

from abc import ABC, abstractmethod
from typing import List, Any, Optional
from llama_cpp import Llama
from llama_cpp.llama_types import ChatCompletionRequestMessage
from domain.schemas import ExpertModel
from services.model_loader import ModelLoaderService

class BaseAgent(ABC):
    """
    すべてのエージェントの基本となる抽象基底クラス
    """
    def __init__(self, model_loader: ModelLoaderService):
        self.model_loader = model_loader

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """エージェントの主処理を実行するメソッド"""
        pass

    def _query_llm(self, expert: ExpertModel, messages: List[ChatCompletionRequestMessage]) -> str:
        """LLMに問い合わせを実行する共通メソッド"""
        llm: Llama = self.model_loader.load_expert(expert)
        
        output: Any = llm.create_chat_completion(
            messages=messages,
            max_tokens=4096,
            temperature=0.2,
        )
        
        response_text: Optional[str] = None
        if isinstance(output, dict) and "choices" in output and output["choices"]:
            choice = output["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                content = choice["message"]["content"]
                if content is not None:
                    response_text = content.strip()

        if response_text:
            return response_text
        
        raise RuntimeError(f"エキスパート '{expert.name}' から有効な応答を得られませんでした。 Response: {output}")