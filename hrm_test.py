# /hybrid_llm_system/hrm_test.py
# HRMモデルの動作を最小構成でテストするためのスクリプト (mypy対応版)

import sys
import os
from llama_cpp import Llama
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from llama_cpp.llama_types import ChatCompletionRequestMessage # 追加

def main() -> None:
    """
    HRMモデルの最小環境テストを実行するメイン関数
    """
    print("--- HRMモデルの最小環境テストを開始します ---")
    
    model_path: Optional[str] = None
    try:
        # .envファイルから環境変数を読み込み
        load_dotenv()
        model_path = os.getenv("HRM_MODEL_PATH")

        if not model_path:
            print("❌ エラー: .envファイルにHRM_MODEL_PATHが設定されていません。")
            return
            
        if not os.path.exists(model_path):
            print(f"❌ エラー: モデルファイルが見つかりません。パスを確認してください: {model_path}")
            return

        print(f"モデルパス: {model_path}")

        # モデルの初期化 (chatmlフォーマット)
        llm = Llama(
            model_path=model_path,
            n_ctx=8192,
            n_gpu_layers=-1,
            verbose=False,
            chat_format="chatml"
        )
        print("✅ モデルの初期化に成功しました。")

        # チャット形式のプロンプトを作成
        messages: List[ChatCompletionRequestMessage] = [ # 型を修正
            {"role": "system", "content": "You are a logical reasoner. Think step by step to solve the problem."},
            {"role": "user", "content": "There are three suspects, A, B, and C. A says 'B is the culprit.' B says 'C is the culprit.' C says 'I am not the culprit.' Only one person is telling the truth, and there is only one culprit. Who is the culprit? Please explain your reasoning step by step."}
        ]

        print("\n--- 応答を生成します... ---")
        
        # チャット補完APIを呼び出し
        response: Any = llm.create_chat_completion(
            messages=messages,
            max_tokens=1024,
            temperature=0.2
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

    print("\n--- テストを終了します ---")

if __name__ == "__main__":
    main()