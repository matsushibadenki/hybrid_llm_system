# /hybrid_llm_system/services/model_loader.py
# LLMモデルのメモリへのロード・アンロードを担当するサービス

from typing import Optional
from llama_cpp import Llama
from domain.schemas import ExpertModel

class ModelLoaderService:
    """
    エキスパートモデルのロードとアンロード（スワッピング）を管理する
    """
    def __init__(self) -> None:
        self.currently_loaded_expert: Optional[ExpertModel] = None

    def load_expert(self, expert: ExpertModel) -> Llama:
        # Jamba(chatml)の場合、常に再読み込みする
        if expert.chat_format == "chatml":
            if self.currently_loaded_expert and self.currently_loaded_expert.name == expert.name:
                print(f"🔄 Jamba(ChatML)モデルの状態をリフレッシュするため、再ロードします。")
            self.unload_expert(self.currently_loaded_expert)
        
        # Jamba以外で、すでにロード済みの場合はインスタンスを再利用
        elif self.currently_loaded_expert and self.currently_loaded_expert.name == expert.name:
            if expert.instance:
                print(f"✅ エキスパート '{expert.name}' は既にロード済みです。")
                return expert.instance
        
        # 別のモデルがロードされている場合はアンロード
        elif self.currently_loaded_expert:
            self.unload_expert(self.currently_loaded_expert)

        print(f"🔄 思考回路を切り替え中... エキスパート '{expert.name}' をロードします。")
        try:
            instance = Llama(
                model_path=expert.model_path,
                n_gpu_layers=0,  # 安定性のためCPU実行を維持
                n_ctx=8192,
                n_batch=512,
                verbose=False,
                chat_format=expert.chat_format
            )
            expert.instance = instance
            expert.is_loaded = True
            self.currently_loaded_expert = expert
            print(f"✅ エキスパート '{expert.name}' の準備が完了しました。 (フォーマット: {expert.chat_format})")
            return instance
        except Exception as e:
            expert.instance = None
            expert.is_loaded = False
            self.currently_loaded_expert = None
            raise RuntimeError(f"エキスパート '{expert.name}' のロード中にエラーが発生: {e}")

    def unload_expert(self, expert: Optional[ExpertModel]) -> None:
        if expert and expert.instance:
            print(f"🧹 エキスパート '{expert.name}' をアンロードし、メモリを解放します。")
            expert.instance = None
            expert.is_loaded = False
            if self.currently_loaded_expert and self.currently_loaded_expert.name == expert.name:
                self.currently_loaded_expert = None