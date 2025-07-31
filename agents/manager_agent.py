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
        self.manager_expert_name = "Transformer"

    def _create_performance_summary(self, workspace: GlobalWorkspace) -> str:
        # (この関数に変更はありません)
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
        manager_expert = self._find_expert(self.manager_expert_name, experts)
        expert_descriptions = self._format_expert_descriptions(experts)

        system_prompt = f"""
あなたはAIプロジェクトマネージャーです。ユーザーの要求を分析し、実行計画をJSON形式で立案してください。

### 指示
- **単純なタスク**: 挨拶や簡単な質問には、タスクを1つだけ生成し、担当者は「{self.manager_expert_name}」にしてください。
- **複雑なタスク**: 複数のステップが必要な場合は、タスクを分解し、最適なエキスパートを割り当ててください。
- **最終報告**: 複数のタスクがある場合、最後には必ず担当者が「Reporter」のタスクを追加してください。
- **出力形式**: **絶対にJSON形式のみで出力してください。説明文や前置きは一切不要です。**
"""
        
        performance_summary = self._create_performance_summary(workspace)
        system_prompt += performance_summary
        
        if validation_error:
            system_prompt += f"""
**【最重要】前回の計画の修正指示**
前回の計画には以下の構造的な問題がありました。このエラーを解決する、論理的に正しい新しい計画を生成してください。
- **検証エラー:** {validation_error}
"""

        if failed_plan:
            failure_context = "\n**【最重要】前回の計画の失敗**\n前回の計画は実行に失敗しました。失敗情報を分析し、ユーザーの元の要求を達成するための新しい計画を立案してください。同じ失敗を繰り返さないように、根本原因を考えて代替アプローチを提案してください。\n"
            failure_context += "--- 失敗したタスクの情報 ---\n"
            for task in failed_plan.tasks:
                if task.status == 'failed':
                    failure_context += f"- タスクID {task.task_id} ({task.expert_name}): {task.description}\n"
                    failure_context += f"  - 失敗理由: {task.result}\n"
            failure_context += "----------------------------\n"
            system_prompt += failure_context
        
        system_prompt += f"""
### 利用可能なエキスパート
{expert_descriptions}

### JSON出力フォーマット
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
            # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↓修正開始◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
            # より堅牢なJSON抽出ロジックに変更
            start_index = raw_response.find('{')
            end_index = raw_response.rfind('}')
            if start_index != -1 and end_index != -1 and start_index < end_index:
                plan_json_str = raw_response[start_index:end_index+1]
            else:
                plan_json_str = raw_response # 抽出失敗時はそのまま試す
            # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↑修正終わり◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️

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