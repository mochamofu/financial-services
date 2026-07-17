# Pitch Agent(ピッチ資料作成エージェント)— Managed Agent テンプレート

## 概要

コンプス、先行事例、LBO → ブランド仕様のピッチデックまでエンドツーエンド。[`pitch-agent`](../../plugins/agent-plugins/pitch-agent) Cowork プラグインと同一ソース — このディレクトリは `POST /v1/agents` 用の Managed Agent クックブックです。

## デプロイ

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export CAPIQ_MCP_URL=... DALOOPA_MCP_URL=...
../../scripts/deploy-managed-agent.sh pitch-agent
```

## ステアリングイベント

[`steering-examples.json`](./steering-examples.json) を参照。

## セキュリティとハンドオフ

タスク分解型の分割です — 信頼できない入力への対処というより(データは CapIQ/Daloopa の MCP から来ます)、並列性と成果物の分離が目的です。`Write` を持つワーカーはちょうど1つです:

| リーフ | ツール | コネクタ |
|---|---|---|
| `researcher` | `Read`、`Grep` | CapIQ、Daloopa(読み取り専用) |
| `modeler` | `Read`、`Bash`(サンドボックス化) | CapIQ、Daloopa(読み取り専用) |
| **`deck-writer`**(Write 保持者) | `Read`、`Write`、`Edit` | なし |

成果物は `pptx-author` / `xlsx-author` を通じて `./out/pitch-<target>.pptx` と `./out/model.xlsx` に出力されます。

**ハンドオフ:** 投資テーゼの変更後にモデルを再構築するには、オーケストレーターが `model-builder` 宛の `handoff_request` を発行します。`scripts/orchestrate.py`(またはワークフローエンジン)がそれを新しいステアリングイベントとしてルーティングします。許可リスト+ペイロード検証のパターンはスクリプトを参照してください。
