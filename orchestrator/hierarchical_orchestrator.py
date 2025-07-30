# /hybrid_llm_system/orchestrator/hierarchical_orchestrator.py
# 階層型タスク分解を実行するオーケストレーター (最終修正版)

from typing import Dict, List, Optional, Tuple, Set
from domain.manager import ModelManager
from domain.schemas import SubTask, Plan, ExpertModel
from agents.manager_agent import ManagerAgent
from agents.worker_agent import WorkerAgent
from agents.reporter_agent import ReporterAgent
from workspace.global_workspace import GlobalWorkspace

class HierarchicalOrchestrator:
    """
    Manager-Worker-Reporterモデルに基づき、思考プロセス全体を管理する。
    自己修正フィードバックループと計画検証機能を持つ。
    """
    def __init__(
        self,
        model_manager: ModelManager,
        manager_agent: ManagerAgent,
        worker_agent: WorkerAgent,
        reporter_agent: ReporterAgent,
        global_workspace: GlobalWorkspace,
    ):
        self.model_manager = model_manager
        self.manager_agent = manager_agent
        self.worker_agent = worker_agent
        self.reporter_agent = reporter_agent
        self.global_workspace = global_workspace

    def _validate_plan(self, plan: Plan, experts: List[ExpertModel]) -> Tuple[bool, str]:
        if not plan.tasks:
            return False, "計画にタスクが含まれていません。"
        task_ids = {task.task_id for task in plan.tasks}
        expert_names = {expert.name.lower() for expert in experts} | {"reporter"}
        for task in plan.tasks:
            if task.expert_name.lower() not in expert_names:
                return False, f"タスク {task.task_id} に割り当てられたエキスパート '{task.expert_name}' が存在しません。"
            for dep_id in task.dependencies:
                if dep_id not in task_ids:
                    return False, f"タスク {task.task_id} の依存先タスクID {dep_id} が計画内に存在しません。"
        path: Set[int] = set()
        visited: Set[int] = set()
        task_map = {task.task_id: task for task in plan.tasks}
        def has_cycle(task_id: int) -> bool:
            path.add(task_id)
            task_dependencies = task_map.get(task_id, SubTask(0, "", "", [])).dependencies
            for dep_id in task_dependencies:
                if dep_id in path:
                    return True
                if dep_id not in visited:
                    if has_cycle(dep_id):
                        return True
            path.remove(task_id)
            visited.add(task_id)
            return False
        for task_id in task_ids:
            if task_id not in visited:
                if has_cycle(task_id):
                    return False, "タスクの依存関係が循環しています。"
        return True, "計画は妥当です。"

    def process_task(self, prompt: str) -> str:
        print(f"▶️  タスク開始: {prompt}")
        experts = self.model_manager.get_all_experts()
        
        expert_names = [e.name for e in experts]
        system_prompts = {e.name: e.system_prompt for e in experts}
        self.global_workspace.initialize(expert_names, system_prompts)
        self.global_workspace.set_initial_prompt(prompt)

        max_retries = 3
        current_plan: Optional[Plan] = None
        validation_error: Optional[str] = None
        
        for attempt in range(max_retries):
            if attempt == 0:
                print("\n--- Step 1: 思考プランニング (Manager) ---")
                try:
                    current_plan = self.manager_agent.execute(prompt, experts, self.global_workspace)
                    self.global_workspace.add_thought(
                        "manager_agent", "initial_plan", [t.__dict__ for t in current_plan.tasks]
                    )
                except Exception as e:
                    return f"エラー: 初期計画の生成中に致命的なエラーが発生しました - {e}"
            else:
                print(f"\n--- リトライ試行 {attempt + 1}/{max_retries}: 思考プランを再構築します ---")
                try:
                    current_plan = self.manager_agent.execute(
                        prompt,
                        experts,
                        self.global_workspace,
                        failed_plan=current_plan,
                        validation_error=validation_error
                    )
                    self.global_workspace.add_thought(
                        "manager_agent", f"revised_plan_attempt_{attempt}", [t.__dict__ for t in current_plan.tasks]
                    )
                    validation_error = None
                except Exception as e:
                    return f"エラー: 計画の修正中に致命的なエラーが発生しました - {e}"

            if not current_plan or not current_plan.tasks:
                 return "エラー: 思考プランの生成に失敗しました。"

            is_valid, error_message = self._validate_plan(current_plan, experts)
            if not is_valid:
                print(f"❌ 計画の検証に失敗しました: {error_message}")
                validation_error = error_message
                self.global_workspace.add_thought("orchestrator", "validation_failed", error_message)
                if attempt < max_retries - 1:
                    continue
                else:
                    return f"エラー: 最大リトライ回数に達しました。計画の構造的な問題を解決できませんでした。({error_message})"
            
            self.global_workspace.add_thought("orchestrator", "validation_passed", "Plan is valid.")
            print("✅ 計画は妥当です。実行を開始します。")

            print(f"\n--- 試行 {attempt + 1}/{max_retries}: 計画を実行します ---")
            for task in current_plan.tasks:
                dep_str = f" (depends on: {task.dependencies})" if task.dependencies else ""
                print(f"   - Task {task.task_id}: [{task.expert_name.upper()}] {task.description}{dep_str}")

            worker_tasks = [t for t in current_plan.tasks if t.expert_name != 'reporter']
            completed_tasks: Dict[int, SubTask] = {}
            pending_tasks = worker_tasks[:]
            
            print("\n--- Step 2: サブタスク実行 (Workers) ---")
            has_failed = False
            
            max_loops = len(pending_tasks) + 5
            current_loop = 0
            while pending_tasks and current_loop < max_loops:
                executable_tasks = [t for t in pending_tasks if all(dep_id in completed_tasks for dep_id in t.dependencies)]

                if not executable_tasks:
                    print("❌ 実行可能なタスクがありません。依存関係が循環しているか、先行タスクが失敗した可能性があります。")
                    has_failed = True
                    break
                
                for task in executable_tasks:
                    task.status = "in_progress"
                    print(f"\n▶️  Task {task.task_id} ({task.expert_name.upper()}) を開始: {task.description}")
                    try:
                        result = self.worker_agent.execute(task, experts, completed_tasks)
                        task.result = result
                        task.status = "completed"
                        print(f"✅ Task {task.task_id} が完了しました。")
                    except Exception as e:
                        task.status = "failed"
                        task.result = f"タスク実行エラー: {e}"
                        print(f"❌ Task {task.task_id} でエラーが発生しました: {e}")
                        has_failed = True
                    
                    completed_tasks[task.task_id] = task
                    self.global_workspace.add_thought(f"expert:{task.expert_name}", "task_result", task.__dict__)
                    pending_tasks.remove(task)
                
                if has_failed:
                    break
                current_loop += 1
            
            all_worker_tasks_dict = {t.task_id: t for t in worker_tasks}
            all_worker_tasks_dict.update(completed_tasks)
            reporter_tasks_list = [t for t in current_plan.tasks if t.expert_name == 'reporter']
            current_plan.tasks = list(all_worker_tasks_dict.values()) + reporter_tasks_list

            if not has_failed and not pending_tasks:
                print("\n✅ 全てのワーキングタスクが正常に完了しました。")
                reporter_task = next((t for t in current_plan.tasks if t.expert_name == 'reporter'), None)
                if not reporter_task:
                    if completed_tasks:
                        last_task = max(completed_tasks.values(), key=lambda t: t.task_id)
                        final_answer = last_task.result or "タスクは完了しましたが、結果がありませんでした。"
                        self.global_workspace.set_final_answer(final_answer)
                        return final_answer
                    return "タスクが実行されませんでした。"
                
                print("\n--- Step 3: 最終報告の生成 (Reporter) ---")
                final_report = self.reporter_agent.execute(current_plan, experts)
                self.global_workspace.set_final_answer(final_report)
                return final_report

            else:
                print("\n❌ 計画の実行中にタスクが失敗しました。")
                if attempt >= max_retries - 1:
                    return "エラー: 最大リトライ回数に達しました。タスクを完了できませんでした。"
        
        return "エラー: 予期せぬ状態で処理が終了しました。"