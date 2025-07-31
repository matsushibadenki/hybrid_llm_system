# /hybrid_llm_system/jamba_test.py
# Jambaモデルの動作を最小構成でテストするためのスクリプト (mypy対応版)
# (エラー詳細表示のための修正版)

import sys
import os
from llama_cpp import Llama
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from llama_cpp.llama_types import ChatCompletionRequestMessage

def main() -> None:
    """
    Jambaモデルの最小環境テストを実行するメイン関数
    """
    print("--- Jambaモデルの最小環境テストを開始します ---")
    
    model_path: Optional[str] = None
    try:
        load_dotenv()
        model_path = os.getenv("JAMBA_MODEL_PATH")

        if not model_path:
            print("❌ エラー: .envファイルにJAMBA_MODEL_PATHが設定されていません。")
            return

        if not os.path.exists(model_path):
            print(f"❌ エラー: モデルファイルが見つかりません。パスを確認してください: {model_path}")
            return

        print(f"モデルパス: {model_path}")

        # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↓修正開始◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
        # モデルの初期化 (CPU実行、詳細ログ有効)
        llm = Llama(
            model_path=model_path,
            n_ctx=4096,      # コンテキストサイズを小さめに設定
            n_gpu_layers=0,  # CPUで実行
            verbose=True,    # 詳細なログを出力する
            chat_format="chatml"
        )
        # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↑修正終わり◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
        print("✅ モデルの初期化に成功しました。")

        messages: List[ChatCompletionRequestMessage] = [
            {"role": "system", "content": "あなたは、誠実で優秀なAIアシスタントです。"},
            {"role": "user", "content": "こんにちは"}
        ]

        print("\n--- 応答を生成します... ---")
        
        response: Any = llm.create_chat_completion(
            messages=messages,
            max_tokens=256,
            temperature=0.7
        )
        
        print("\n--- 応答の生成に成功しました！ ---")

        if "choices" in response and response["choices"]:
            choice = response["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                content: Optional[str] = choice["message"]["content"]
                if content is not None:
                    print("\n[モデルからの応答]")
                    print(content.strip())
                else:
                    print("応答メッセージにテキストが含まれていません。")
            else:
                print("応答メッセージの形式が正しくありません。")
        else:
            print("応答内容が空か、予期しない形式です。")
            print(f"受信したデータ: {response}")

    except Exception as e:
        print(f"\n❌ テスト中に予期せぬエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

    print("\n--- テストを終了します ---")

if __name__ == "__main__":
    main()