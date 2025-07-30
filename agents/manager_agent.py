# /hybrid_llm_system/agents/manager_agent.py
# 思考プランを立案するマネージャーエージェント

import json
import re
from typing import List, Dict, Any, Optional
from llama_cpp.llama_types import ChatCompletionRequestMessage
from domain.schemas import Plan, SubTask, ExpertModel
from agents.base_agent import BaseAgent
from services.model_loader import ModelLoaderService
from workspace.global_workspace import GlobalWorkspace

class ManagerAgent(BaseAgent):
    """
    ユーザーの要求を分析し、サブタスクのリスト（Plan）を生成するエージェント
    """
    def __init__(self, model_loader: ModelLoaderService):
        super().__init__(model_loader)
        self.manager_expert_name = "Jamba"

    def _create_performance_summary(self, workspace: GlobalWorkspace) -> str:
        """思考履歴からエキスパートの成功・失敗回数を集計して文字列を生成する"""
        success_counts: Dict[str, int] = {}
        failure_counts: Dict[str, int] = {}

        for thought in workspace.thought_process:
            if thought["type"] == "task_result":
                expert_name = thought["source"].split(":")[-1]
                status = thought["content"].get("status")
                if status == "completed":
                    success_counts[expert_name] = success_counts.get(expert_name, 0) + 1
                elif status == "failed":
                    failure_counts[expert_name] = failure_counts.get(expert_name, 0) + 1
        
        if not success_counts and not failure_counts:
            return ""

        summary = "\n**過去のエキスパートの実行実績:**\n"
        all_expert_names = set(success_counts.keys()) | set(failure_counts.keys())
        for name in sorted(list(all_expert_names)):
            s_count = success_counts.get(name, 0)
            f_count = failure_counts.get(name, 0)
            summary += f"- {name}: 成功 {s_count}回, 失敗 {f_count}回\n"
        
        return summary

    def execute(
        self,
        prompt: str,
        experts: List[ExpertModel],
        workspace: GlobalWorkspace,
        failed_plan: Optional[Plan] = None,
        validation_error: Optional[str] = None
    ) -> Plan:
        """
        プロンプトと利用可能なエキスパートリストから実行計画を生成する。
        失敗した計画や検証エラーが与えられた場合、それを修正する。
        """
        manager_expert = self._find_expert(self.manager_expert_name, experts)
        expert_descriptions = self._format_expert_descriptions(experts)

        system_prompt = f"""
あなたは非常に優秀なAIプロジェクトマネージャーです。ユーザーの要求を分析し、それを達成するための実行計画をJSON形式で立案してください。

**指示:**
1.  **要求分析**: ユーザーの要求が単純な挨拶や短い質疑応答の場合、タスクは1つだけにし、`expert_name`は`jamba`に設定してください。
2.  **タスク分解**: ユーザーの要求が複雑な場合のみ、複数のサブタスクに分解してください。
3.  **エキスパート選定**: 各サブタスクに最も適した専門家を割り当ててください。**過去の実行実績も参考にしてください。**
4.  **依存関係**: 依存関係は`dependencies`に先行タスクの`task_id`リストを指定してください。
5.  **最終報告**: 複雑なタスクの最後には必ず`expert_name`が`reporter`のタスクを配置してください。
6.  **出力形式**: 出力は**JSON形式のみ**とし、説明などの余計なテキストは絶対に含めないでください。
"""
        performance_summary = self._create_performance_summary(workspace)
        system_prompt += performance_summary
        
        # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↓修正開始 (正しいロジックを復元)◾️◾️◾◾️◾️◾️◾️◾️◾️◾️
        if validation_error:
            system_prompt += f"""
**重要: 計画の構造的欠陥の修正**
前回の計画には以下の構造的な問題がありました。このエラーを解決し、論理的に正しい新しい計画を生成してください。
- **検証エラー:** {validation_error}
"""

        if failed_plan:
            failure_context = "\n**重要: 計画の実行失敗**\n前回の計画は実行に失敗しました。以下の失敗情報を分析し、ユーザーの元の要求を達成するための新しい計画を立案してください。同じ失敗を繰り返さないように、根本的な原因を考えて代替アプローチを提案してください。\n"
            failure_context += "--- 失敗したタスクの情報 ---\n"
            for task in failed_plan.tasks:
                if task.status == 'failed':
                    failure_context += f"- タスクID {task.task_id} ({task.expert_name}): {task.description}\n"
                    failure_context += f"  - 失敗理由: {task.result}\n"
            failure_context += "----------------------------\n"
            system_prompt += failure_context
        # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↑修正終わり (正しいロジックを復元)◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
        
        system_prompt += f"""
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
    }}
  ]
}}
"""
        user_prompt = f"以下の要求に対する実行計画をJSON形式で作成してください:\n\n{prompt}"
        
        messages: List[ChatCompletionRequestMessage] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        raw_response = self._query_llm(manager_expert, messages)
        
        original_prompt_for_plan = prompt
        if failed_plan:
            original_prompt_for_plan = failed_plan.original_prompt

        try:
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if json_match:
                plan_json_str = json_match.group(0)
            else:
                plan_json_str = raw_response

            plan_data = json.loads(plan_json_str)
            tasks = [SubTask(**task_data) for task_data in plan_data.get("tasks", [])]
            return Plan(original_prompt=original_prompt_for_plan, tasks=tasks)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"❌ JSONパースエラー: {e}\nRaw Response:\n{raw_response}")
            return self._create_fallback_plan(original_prompt_for_plan, experts)

    def _find_expert(self, name: str, experts: List[ExpertModel]) -> ExpertModel:
        for expert in experts:
            if expert.name.lower() == name.lower():
                return expert
        raise ValueError(f"エキスパート '{name}' が見つかりません。")

    def _format_expert_descriptions(self, experts: List[ExpertModel]) -> str:
        return "\n".join([f"- {e.name}: {e.description}" for e in experts if e.name.lower() != "reporter"])

    def _create_fallback_plan(self, prompt: str, experts: List[ExpertModel]) -> Plan:
        default_expert = self._find_expert(self.manager_expert_name, experts)
        task = SubTask(
            task_id=1,
            description=f"ユーザーの要求に直接応答する: {prompt}",
            expert_name=default_expert.name,
            dependencies=[]
        )
        return Plan(original_prompt=prompt, tasks=[task])