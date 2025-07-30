# /hybrid_llm_system/agents/reporter_agent.py
# 最終報告を生成するリポーターエージェント

from typing import List, Dict
from domain.schemas import Plan, ExpertModel, SubTask
from agents.base_agent import BaseAgent

class ReporterAgent(BaseAgent):
    """
    完了した全タスクの結果を統合し、最終的な報告書を生成するエージェント
    """
    def execute(self, plan: Plan, experts: List[ExpertModel]) -> str:
        """
        実行計画の全結果を要約し、最終的な回答を生成する
        """
        reporter_expert = self._find_reporter_expert(experts)
        
        context = f"ユーザーの元の要求: {plan.original_prompt}\n\n"
        context += "以下は、各エキスパートが実行したサブタスクとその結果です:\n---\n"
        for task in sorted(plan.tasks, key=lambda t: t.task_id):
            if task.status == "completed":
                context += f"【タスク{task.task_id}: {task.description} (担当: {task.expert_name})】\n"
                context += f"結果: {task.result}\n\n"
        context += "---\n"

        prompt = "上記の情報に基づき、ユーザーの元の要求に対する包括的で、首尾一貫した最終報告書を作成してください。"
        
        messages = [
            {"role": "system", "content": reporter_expert.system_prompt},
            {"role": "user", "content": prompt}
        ]

        return self._query_llm(reporter_expert, messages)

    def _find_reporter_expert(self, experts: List[ExpertModel]) -> ExpertModel:
        """レポーター役として最適なエキスパートを見つける"""
        for expert in experts:
            if expert.name.lower() == "reporter":
                return expert
        # フォールバックとしてJambaまたは最初のモデルを使用
        for expert in experts:
            if expert.name.lower() == "jamba":
                return expert
        if not experts:
            raise ValueError("利用可能なエキスパートがいません。")
        return experts[0]