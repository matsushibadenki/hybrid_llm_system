# /hybrid_llm_system/agents/worker_agent.py
# サブタスクを実行するワーカーエージェント

import os
import uuid
import traceback
from typing import List, Dict, Any, cast
from llama_cpp.llama_types import ChatCompletionRequestMessage
from domain.schemas import SubTask, ExpertModel
from agents.base_agent import BaseAgent
from diffusers import DiffusionPipeline

class WorkerAgent(BaseAgent):
    """
    割り当てられた単一のサブタスクを実行するエージェント
    LLMと拡散モデルの両方に対応
    """
    def execute(self, task: SubTask, experts: List[ExpertModel], completed_tasks: Dict[int, SubTask]) -> str:
        """
        サブタスクを実行し、結果を文字列で返す
        """
        expert = self._find_expert(task.expert_name, experts)
        
        context = ""
        if task.dependencies:
            context += "先行タスクの結果:\n---\n"
            for dep_id in task.dependencies:
                if dep_id in completed_tasks:
                    result = completed_tasks[dep_id].result
                    context += f"【タスク{dep_id}の結果】:\n{result}\n\n"
            context += "---\n"

        prompt = f"{context}あなたのタスク:\n{task.description}"
        
        if expert.chat_format == "diffusion":
            return self._generate_image(expert, prompt)
        else:
            messages: List[ChatCompletionRequestMessage] = [
                {"role": "system", "content": expert.system_prompt},
                {"role": "user", "content": prompt}
            ]
            return self._query_llm(expert, messages)

    def _generate_image(self, expert: ExpertModel, prompt: str) -> str:
        """拡散モデルを使って画像を生成する"""
        print(f"🎨 画像生成プロンプト: {prompt}")
        try:
            pipeline_instance = self.model_loader.load_expert(expert)

            pipeline = cast(DiffusionPipeline, pipeline_instance)
            
            # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↓修正開始◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
            # mypyがこの呼び出しをエラーと誤認するため、型チェックを部分的に無視させる
            image = pipeline(prompt=prompt).images[0]  # type: ignore[operator]
            # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↑修正終わり◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️

            output_dir = "output/images"
            os.makedirs(output_dir, exist_ok=True)
            
            filename = f"{uuid.uuid4()}.png"
            filepath = os.path.join(output_dir, filename)
            image.save(filepath)

            print(f"🖼️ 画像を保存しました: {filepath}")
            return f"画像を生成し、次のパスに保存しました: {filepath}"
        except Exception as e:
            print(f"❌ 画像生成中にエラーが発生しました: {e}")
            traceback.print_exc()
            return f"画像生成に失敗しました。エラー: {e}"

    def _find_expert(self, name: str, experts: List[ExpertModel]) -> ExpertModel:
        """指定された名前のエキスパートを見つける"""
        for expert in experts:
            if expert.name.lower() == name.lower():
                return expert
        raise ValueError(f"エキスパート '{name}' が見つかりません。")