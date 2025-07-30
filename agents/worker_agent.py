# /hybrid_llm_system/agents/worker_agent.py
# サブタスクを実行するワーカーエージェント

from typing import List, Dict, Any
from domain.schemas import SubTask, ExpertModel
from agents.base_agent import BaseAgent

class WorkerAgent(BaseAgent):
    """
    割り当てられた単一のサブタスクを実行するエージェント
    """
    def execute(self, task: SubTask, experts: List[ExpertModel], completed_tasks: Dict[int, SubTask]) -> str:
        """
        サブタスクを実行し、結果を文字列で返す
        """
        expert = self._find_expert(task.expert_name, experts)
        
        # 依存関係のあるタスクの結果をコンテキストとして追加
        context = ""
        if task.dependencies:
            context += "先行タスクの結果:\n---\n"
            for dep_id in task.dependencies:
                if dep_id in completed_tasks:
                    result = completed_tasks[dep_id].result
                    context += f"【タスク{dep_id}の結果】:\n{result}\n\n"
            context += "---\n"

        prompt = f"{context}あなたのタスク:\n{task.description}"
        
        messages = [
            {"role": "system", "content": expert.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        return self._query_llm(expert, messages)

    def _find_expert(self, name: str, experts: List[ExpertModel]) -> ExpertModel:
        """指定された名前のエキスパートを見つける"""
        for expert in experts:
            if expert.name.lower() == name.lower():
                return expert
        raise ValueError(f"エキスパート '{name}' が見つかりません。")