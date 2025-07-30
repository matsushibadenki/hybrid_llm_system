# /hybrid_llm_system/agents/manager_agent.py
# 思考プランを立案するマネージャーエージェント

import json
import re
from typing import List, Dict, Any
from domain.schemas import Plan, SubTask, ExpertModel
from agents.base_agent import BaseAgent
from services.model_loader import ModelLoaderService

class ManagerAgent(BaseAgent):
    """
    ユーザーの要求を分析し、サブタスクのリスト（Plan）を生成するエージェント
    """
    def __init__(self, model_loader: ModelLoaderService):
        super().__init__(model_loader)
        # マネージャー役としてJambaを固定で利用
        self.manager_expert_name = "Jamba"

    def execute(self, prompt: str, experts: List[ExpertModel]) -> Plan:
        """
        プロンプトと利用可能なエキスパートリストから実行計画を生成する
        """
        manager_expert = self._find_expert(self.manager_expert_name, experts)
        expert_descriptions = self._format_expert_descriptions(experts)

        system_prompt = f"""
あなたは非常に優秀なAIプロジェクトマネージャーです。ユーザーの要求を分析し、それを達成するための実行計画をJSON形式で立案してください。

**指示:**
1.  **要求分析**: ユーザーの要求が単純な挨拶や短い質疑応答（例：「こんにちは」「ありがとう」）の場合、**タスクは1つだけ**にしてください。そのタスクの`expert_name`は`jamba`に設定してください。
2.  **タスク分解**: ユーザーの要求が複雑な場合（複数のステップや専門知識が必要な場合）のみ、要求を複数のサブタスクに分解してください。
3.  **エキスパート選定**: 各サブタスクに最も適した専門家（エキスパート）を割り当ててください。
4.  **依存関係**: タスク間に依存関係がある場合は、'dependencies'に先行するタスクの'task_id'（整数）のリストを指定してください。
5.  **最終報告タスク**: 複雑なタスクの場合、計画の**最後**には必ず`expert_name`が`reporter`のタスクを配置し、それまでの全タスクの結果を統合して最終報告を作成するように指示してください。
6.  **出力形式**: 出力は**JSON形式のみ**とし、説明などの余計なテキストは絶対に含めないでください。

**利用可能なエキスパート:**
{expert_descriptions}

**JSON出力フォーマット:**
{{
  "tasks": [
    {{
      "task_id": 1,
      "description": "（具体的なタスク内容）",
      "expert_name": "（エキスパート名）",
      "dependencies": []
    }},
    {{
      "task_id": 2,
      "description": "（具体的なタスク内容）",
      "expert_name": "（エキスパート名）",
      "dependencies": [1]
    }}
  ]
}}
"""

        user_prompt = f"以下の要求に対する実行計画をJSON形式で作成してください:\n\n{prompt}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        raw_response = self._query_llm(manager_expert, messages)
        
        try:
            # LLMの出力からJSON部分のみを抽出
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if json_match:
                plan_json_str = json_match.group(0)
            else:
                plan_json_str = raw_response

            plan_data = json.loads(plan_json_str)
            tasks = [SubTask(**task_data) for task_data in plan_data.get("tasks", [])]
            return Plan(original_prompt=prompt, tasks=tasks)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"❌ JSONパースエラー: {e}\nRaw Response:\n{raw_response}")
            return self._create_fallback_plan(prompt, experts)

    def _find_expert(self, name: str, experts: List[ExpertModel]) -> ExpertModel:
        """指定された名前のエキスパートを見つける"""
        for expert in experts:
            if expert.name.lower() == name.lower():
                return expert
        raise ValueError(f"エキスパート '{name}' が見つかりません。")

    def _format_expert_descriptions(self, experts: List[ExpertModel]) -> str:
        """エキスパートリストを説明文字列に変換する"""
        # reporterは内部役割なのでリストから除外
        return "\n".join([f"- {e.name}: {e.description}" for e in experts if e.name != "reporter"])

    def _create_fallback_plan(self, prompt: str, experts: List[ExpertModel]) -> Plan:
        """JSONパース失敗時のための単純なプランを作成する"""
        default_expert = self._find_expert(self.manager_expert_name, experts)
        task = SubTask(
            task_id=1,
            description=f"ユーザーの要求に直接応答する: {prompt}",
            expert_name=default_expert.name,
            dependencies=[]
        )
        return Plan(original_prompt=prompt, tasks=[task])