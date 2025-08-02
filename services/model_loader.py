# /hybrid_llm_system/services/model_loader.py
# LLMと拡散モデルのロード・アンロードを担当するサービス

from typing import Optional, Any, Union
from llama_cpp import Llama
from domain.schemas import ExpertModel
import torch
from diffusers import DiffusionPipeline, AutoencoderKL

class ModelLoaderService:
    """
    エキスパートモデルのロードとアンロード（スワッピング）を管理する
    """
    def __init__(self) -> None:
        self.currently_loaded_expert: Optional[ExpertModel] = None

    def load_expert(self, expert: ExpertModel) -> Union[Llama, DiffusionPipeline]:
        if self.currently_loaded_expert and self.currently_loaded_expert.name == expert.name:
            if expert.instance:
                print(f"✅ エキスパート '{expert.name}' は既にロード済みです。")
                if isinstance(expert.instance, Llama):
                    print("🔄 LLMの内部コンテキストをリセットします。")
                    expert.instance.reset()
                return expert.instance

        if self.currently_loaded_expert:
            self.unload_expert(self.currently_loaded_expert)

        print(f"🔄 思考回路を切り替え中... エキスパート '{expert.name}' をロードします。")

        try:
            instance: Union[Llama, DiffusionPipeline]
            if expert.chat_format == "diffusion":
                if not expert.model_id:
                    raise ValueError("拡散モデルのmodel_idが設定されていません。")
                
                device = "cpu"
                if torch.backends.mps.is_available():
                    device = "mps"
                elif torch.cuda.is_available():
                    device = "cuda"
                print(f"使用デバイス: {device}")
                
                vae = AutoencoderKL.from_pretrained(
                    "madebyollin/sdxl-vae-fp16-fix", 
                    torch_dtype=torch.float16
                )
                pipe = DiffusionPipeline.from_pretrained(
                    expert.model_id,
                    vae=vae,
                    torch_dtype=torch.float16,
                    variant="fp16",
                    use_safetensors=True
                )
                instance = pipe.to(device)
                print(f"✅ 拡散モデル '{expert.name}' の準備が完了しました。")
            else:
                if not expert.model_path:
                    raise ValueError("LLMのmodel_pathが設定されていません。")
                
                # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↓修正開始◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
                # クラッシュ対策としてパラメータをさらに安全な値に変更
                instance = Llama(
                    model_path=expert.model_path,
                    n_gpu_layers=0,
                    n_ctx=4096,
                    n_batch=256,      # 安定性のためバッチサイズを削減
                    use_mmap=False,   # メモリマップは引き続き無効
                    verbose=True,     # llama.cppからの詳細ログを有効化
                    chat_format=expert.chat_format
                )
                # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↑修正終わり◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
                print(f"✅ LLM '{expert.name}' の準備が完了しました。 (フォーマット: {expert.chat_format})")

            expert.instance = instance
            expert.is_loaded = True
            self.currently_loaded_expert = expert
            return instance

        except Exception as e:
            expert.instance = None
            expert.is_loaded = False
            self.currently_loaded_expert = None
            raise RuntimeError(f"エキスパート '{expert.name}' のロード中にエラーが発生: {e}")

    def unload_expert(self, expert: Optional[ExpertModel]) -> None:
        if expert and expert.instance:
            print(f"🧹 エキスパート '{expert.name}' をアンロードし、メモリを解放します。")
            if expert.chat_format == "diffusion":
                if torch.cuda.is_available():
                    del expert.instance
                    torch.cuda.empty_cache()
                elif torch.backends.mps.is_available():
                    del expert.instance
                    torch.mps.empty_cache()

            expert.instance = None
            expert.is_loaded = False
            if self.currently_loaded_expert and self.currently_loaded_expert.name == expert.name:
                self.currently_loaded_expert = None