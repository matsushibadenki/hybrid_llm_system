# /hybrid_llm_system/domain/manager.py
# エキスパートモデル定義の読み込みと管理

import os
import yaml
from typing import Dict, List
from dotenv import load_dotenv
from domain.schemas import ExpertModel

class ModelManager:
    """
    models.ymlからエキスパートモデルの定義を読み込み、管理するクラス
    """
    def __init__(self, config_path: str):
        load_dotenv()
        self.experts: Dict[str, ExpertModel] = self._load_experts_from_config(config_path)

    def _load_experts_from_config(self, config_path: str) -> Dict[str, ExpertModel]:
        """
        YAML設定ファイルからモデル定義を読み込み、ExpertModelオブジェクトの辞書を生成する
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"モデル設定ファイルが見つかりません: {config_path}")
        except Exception as e:
            raise RuntimeError(f"モデル設定ファイルの読み込みに失敗しました: {e}")

        experts: Dict[str, ExpertModel] = {}
        expert_definitions = config.get("worker_experts", {})

        for name, settings in expert_definitions.items():
            model_path = os.getenv(settings.get("model_path_env", ""), "")
            if not model_path:
                print(f"警告: 環境変数 '{settings.get('model_path_env')}' が未設定のため、エキスパート '{name}' をスキップします。")
                continue
            
            experts[name] = ExpertModel(
                name=settings.get("name", name),
                description=settings.get("description", ""),
                model_path=model_path,
                chat_format=settings.get("chat_format", "default"),
                system_prompt=settings.get("system_prompt", ""),
                keywords=settings.get("keywords", [])
            )
        
        if not experts:
            raise ValueError(".envファイルでモデルパスが1つも有効に設定されていません。")
            
        return experts

    def get_expert(self, name: str) -> ExpertModel:
        expert = self.experts.get(name)
        if not expert:
            raise ValueError(f"エキスパート '{name}' は定義されていません。")
        return expert

    def get_all_experts(self) -> List[ExpertModel]:
        return list(self.experts.values())