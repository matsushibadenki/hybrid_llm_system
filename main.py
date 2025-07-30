# /hybrid_llm_system/main.py
# ブレイン・シミュレーション・システムのメインファイル (新アーキテクチャ版)

import readline
from container.container import Container
from orchestrator.hierarchical_orchestrator import HierarchicalOrchestrator

def main() -> None:
    """
    メイン関数
    """
    print("--- 思考シミュレーション・システム (v3 - Hierarchical) を初期化しています ---")
    try:
        # DIコンテナを初期化
        container = Container()
        container.config_path.from_dict({
            'model_config_path': './config/models.yml'
        })
        
        # オーケストレーターを取得
        orchestrator: HierarchicalOrchestrator = container.hierarchical_orchestrator()

    except Exception as e:
        print(f"❌ エラー: 初期化に失敗しました。 - {e}")
        print("設定ファイル(models.yml, .env)やモデルのパスを確認してください。")
        return

    print("--- 初期化が完了しました ---")
    print("対話を開始します。終了するには 'exit' または 'quit' と入力してください。")

    while True:
        try:
            question: str = input("> ")

            if question.lower() in ["exit", "quit"]:
                print("システムを終了します。")
                break

            if not question.strip():
                continue

            print("\n--- 思考中... ---")
            response: str = orchestrator.process_task(question)
            print("\n--- 回答 ---")
            print(response)
            print("\n")

        except KeyboardInterrupt:
            print("\nシステムを終了します。")
            break
        except Exception as e:
            print(f"致命的なエラーが発生しました: {e}")

if __name__ == "__main__":
    main()