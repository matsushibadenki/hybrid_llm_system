# /hybrid_llm_system/orchestrator/hierarchical_orchestrator.py
# 階層型タスク分解を実行するオーケストレーター

from typing import Dict, List, Set
from domain.manager import ModelManager
from domain.schemas import SubTask, Plan
from agents.manager_agent import ManagerAgent
from agents.worker_agent import WorkerAgent
from agents.reporter_agent import ReporterAgent

class HierarchicalOrchestrator:
    """
    Manager-Worker-Reporterモデルに基づき、思考プロセス全体を管理する。
    """
    def __init__(
        self,
        model_manager: ModelManager,
        manager_agent: ManagerAgent,
        worker_agent: WorkerAgent,
        reporter_agent: ReporterAgent,
    ):
        self.model_manager = model_manager
        self.manager_agent = manager_agent
        self.worker_agent = worker_agent
        self.reporter_agent = reporter_agent

    def process_task(self, prompt: str) -> str:
        """
        ユーザーの要求を処理し、最終的な回答を生成する
        """
        print(f"▶️  タスク開始: {prompt}")
        experts = self.model_manager.get_all_experts()

        # 1. Plan: マネージャーによる計画立案
        print("\n--- Step 1: 思考プランニング (Manager) ---")
        plan = self.manager_agent.execute(prompt, experts)
        if not plan.tasks:
            return "エラー: 思考プランの生成に失敗しました。"
        
        print("📝 思考プランを生成しました。")
        for task in plan.tasks:
            dep_str = f" (depends on: {task.dependencies})" if task.dependencies else ""
            print(f"   - Task {task.task_id}: [{task.expert_name.upper()}] {task.description}{dep_str}")

        # レポータータスクを特定
        reporter_task = next((t for t in plan.tasks if t.expert_name == 'reporter'), None)
        worker_tasks = [t for t in plan.tasks if t.expert_name != 'reporter']

        # 2. Execute: ワーカーによるタスク実行
        print("\n--- Step 2: サブタスク実行 (Workers) ---")
        completed_tasks: Dict[int, SubTask] = {}
        
        # 依存関係を解決しながらタスクを完了するまで実行
        pending_tasks = worker_tasks[:]
        max_loops = len(pending_tasks) + 5  # 無限ループ防止
        current_loop = 0
        while pending_tasks and current_loop < max_loops:
            executable_tasks = [
                t for t in pending_tasks
                if all(dep_id in completed_tasks for dep_id in t.dependencies)
            ]

            if not executable_tasks:
                # 実行可能なタスクがない場合はループを終了（エラーケース）
                print("❌ 実行可能なタスクがありません。依存関係が循環している可能性があります。")
                break
            
            for task in executable_tasks:
                task.status = "in_progress"
                print(f"\n▶️  Task {task.task_id} ({task.expert_name.upper()}) を開始: {task.description}")
                try:
                    result = self.worker_agent.execute(task, experts, completed_tasks)
                    task.result = result
                    task.status = "completed"
                    completed_tasks[task.task_id] = task
                    print(f"✅ Task {task.task_id} が完了しました。")
                except Exception as e:
                    task.status = "failed"
                    task.result = f"エラー: {e}"
                    completed_tasks[task.task_id] = task # 失敗しても完了リストには追加
                    print(f"❌ Task {task.task_id} でエラーが発生しました: {e}")
                
                pending_tasks.remove(task) # 処理済みタスクをリストから削除
            
            current_loop += 1

        if pending_tasks:
             return "エラー: 全てのワーカータスクを完了できませんでした。"

        # 単純なタスク（レポータータスクなし）の場合は、最後のワーカーの結果を返す
        if not reporter_task:
            if completed_tasks:
                last_task = max(completed_tasks.values(), key=lambda t: t.task_id)
                return last_task.result or "タスクは完了しましたが、結果がありませんでした。"
            return "タスクが実行されませんでした。"

        # 3. Report: リポーターによる最終報告
        print("\n--- Step 3: 最終報告の生成 (Reporter) ---")
        reporter_task.status = 'completed'
        completed_tasks[reporter_task.task_id] = reporter_task # 最終報告のため完了リストに追加
        final_report = self.reporter_agent.execute(plan, experts)
        
        return final_report