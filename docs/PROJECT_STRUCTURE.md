# プロジェクト構造（ツリー概要）

このドキュメントは、`openaiagents` リポジトリのディレクトリ/ファイル構成と責務をまとめたものです（READMEとは別に、コードを読む人向けの“地図”として使う想定）。

## 全体像（トップレベル）

- **`app/`**: アプリ本体（FastAPI + 各サービス/エージェント/モデル定義）
- **`tests/`**: テスト（pytest）
- **`scripts/`**: 動作確認・実行用スクリプト
- **`templates/`**: PPTX生成用テンプレート
- **`artifacts/`**: 実行時に生成される成果物（画像/PPTX/ログ等）
- **`pyproject.toml`**: 依存関係・ツール設定（ruff/mypy等）
- **`Makefile`**: セットアップ/開発サーバ/テスト/静的解析コマンドの集約

## `app/`（アプリ本体）

FastAPIのエンドポイント定義と、画像生成/PPTX/ワークフロー等のユースケース実装が入ります。

### 主要ファイル

- **`app/main.py`**
  - FastAPIアプリ生成（`create_app()`）とルーティング定義
  - 例: `/health`, `/images/generate`, `/pptx/render`, `/pptx/explain`, `/workflow/run`, `/agent/run`

### サブディレクトリ

- **`app/core/`**: 横断的な基盤
  - **`config.py`**: 設定（env）読み込みと `Settings`
    - `OPENAI_API_KEY`, `OPENAI_ORGANIZATION_ID`, `OPENAI_PROJECT_ID`, `OPENAI_IMAGE_MODEL`, `ARTIFACT_DIR`, `LOG_LEVEL` など
  - **`logging.py`**: ロギング設定（richログ等）

- **`app/models/`**: APIスキーマ（Pydantic）
  - **`schemas.py`**: リクエスト/レスポンスの型定義
    - `ImageGenerateRequest` は **extra許可**で、将来の画像パラメータもパススルー可能

- **`app/services/`**: 機能単位のサービス層（I/Oとユースケース実装）
  - **`image_service.py`**: 画像生成ユースケース
    - APIキー無しならダミー画像生成
    - APIキーありならOpenAIへリクエスト→PNG保存（`artifacts/images/<trace_id>/image.png`）
  - **`openai_client.py`**: OpenAI呼び出しの最小クライアント（httpx）
    - `OpenAI-Organization` / `OpenAI-Project` ヘッダ対応
    - OpenAIの400本文をサーフェスして原因調査しやすくする
  - **`pptx_service.py`**: PPTX生成/操作
  - **`workflow_service.py`**: ワークフロー（DAG）実行

- **`app/agents/`**: エージェント/ツール呼び出し周り
  - **`agent_runner.py`**: エージェント実行・ツール統合のエントリ
  - **`tools.py`**: エージェントが使うツール群（画像生成、PPTXなどへの接続点）

- **`app/utils/`**: 補助関数
  - **`convert.py`**: 変換処理（例: PPTX→画像など、環境依存を含む）

## `tests/`（テスト）

- **`test_health.py`**: `/health` の疎通
- **`test_images.py`**: `/images/generate` が拡張パラメータ（未知フィールド含む）を422にせず受けること等
- **`test_pptx.py`**: PPTX生成と解説の基本動作
- **`test_workflow.py`**: ワークフロー実行ログが作られること

## `artifacts/`（生成物）

実行時に自動で作られる成果物置き場です（原則コミット対象外の扱いで運用）。

- **`artifacts/images/<trace_id>/image.png`**: 生成画像（ダミー含む）
- **`artifacts/deck-<trace_id>.pptx`**: 生成したPPTX
- **`artifacts/slides/<trace_id>/...`**: PPTX→PNG変換結果（環境依存）
- **`artifacts/traces/`**: 実行トレース（JSON）
- **`artifacts/workflows/`**: ワークフロー実行ログ（JSON）

## `scripts/`（スクリプト）

- **`demo_requests.sh`**: curlで一通りAPIを叩くデモ（health→images→pptx→workflow）
- **`run.sh`**: 起動補助（環境により）

## `templates/`（テンプレート）

- **`template.pptx`**: PPTX生成のベーステンプレ


