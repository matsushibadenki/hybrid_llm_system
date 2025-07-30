# /hybrid_llm_system/jamba_test.py
# Jambaモデルの動作を最小構成でテストするためのスクリプト (mypy対応版)

import sys
import os
from llama_cpp import Llama
from typing import List, Dict, Any

# プロジェクトのルートパスをsys.pathに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from config.settings import Settings

def main() -> None:
    """
    Jambaモデルの最小環境テストを実行するメイン関数
    """
    print("--- Jambaモデルの最小環境テストを開始します ---")
    
    model_path = ""
    try:
        settings = Settings()
        model_path = settings.model_paths.get("jamba", "")

        if not model_path:
            print("❌ エラー: .envファイルにJAMBA_MODEL_PATHが設定されていません。")
            return

        print(f"モデルパス: {model_path}")

        llm = Llama(
            model_path=model_path,
            n_ctx=8192,
            n_gpu_layers=-1,
            verbose=False,
        )
        print("✅ モデルの初期化に成功しました。")

        print("\n--- 直接プロンプト注入を試みます ---")
        prompt = "AIの未来について、創造的で楽観的な物語を書いてください。"
        instruction_prompt = f"[INST] {prompt} [/INST]"
        
        # mypyエラーを回避するため、戻り値の型をAnyに指定
        response: Any = llm(
            prompt=instruction_prompt,
            max_tokens=1024,
            stop=["[INST]", "[/INST]"],
            temperature=0.7
        )
        
        print("\n--- 応答の生成に成功しました！ ---")

        if "choices" in response and response["choices"]:
            choice = response["choices"][0]
            if "text" in choice and choice["text"] is not None:
                content: str = choice["text"]
                print("\n[モデルからの応答]")
                print(content.strip())
            else:
                print("応答メッセージにテキストが含まれていません。")
        else:
            print("応答内容が空か、予期しない形式です。")
            print(f"受信したデータ: {response}")

    except FileNotFoundError:
        print(f"\n❌ エラー: モデルファイルが見つかりません。パスを確認してください: {model_path}")
    except Exception as e:
        print(f"\n❌ テスト中にエラーが発生しました: {e}")

    print("\n--- テストを終了します ---")

if __name__ == "__main__":
    main()