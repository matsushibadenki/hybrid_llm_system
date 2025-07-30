# /hybrid_llm_system/container/container.py
# DIコンテナの定義ファイル

from dependency_injector import containers, providers
from domain.manager import ModelManager
from services.model_loader import ModelLoaderService
from orchestrator.hierarchical_orchestrator import HierarchicalOrchestrator
from agents.manager_agent import ManagerAgent
from agents.worker_agent import WorkerAgent
from agents.reporter_agent import ReporterAgent
# ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↓修正開始◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
from workspace.global_workspace import GlobalWorkspace
# ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↑修正終わり◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️

class Container(containers.DeclarativeContainer):
    """
    DIコンテナ
    アプリケーションの依存関係を管理します。
    """
    config_path = providers.Configuration()

    # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↓修正開始◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
    # --- Workspace ---
    global_workspace = providers.Singleton(GlobalWorkspace)
    # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↑修正終わり◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️

    # --- Services ---
    model_loader = providers.Singleton(ModelLoaderService)
    
    model_manager = providers.Singleton(
        ModelManager,
        config_path=config_path.model_config_path
    )
    
    # --- Agents ---
    manager_agent = providers.Factory(
        ManagerAgent,
        model_loader=model_loader
    )
    
    worker_agent = providers.Factory(
        WorkerAgent,
        model_loader=model_loader
    )
    
    reporter_agent = providers.Factory(
        ReporterAgent,
        model_loader=model_loader
    )

    # --- Orchestrator ---
    # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↓修正開始◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
    hierarchical_orchestrator = providers.Factory(
        HierarchicalOrchestrator,
        model_manager=model_manager,
        manager_agent=manager_agent,
        worker_agent=worker_agent,
        reporter_agent=reporter_agent,
        global_workspace=global_workspace,
    )
    # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↑修正終わり◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️