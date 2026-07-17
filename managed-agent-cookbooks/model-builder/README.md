# モデル構築エージェント(Model Builder)— Managed Agent テンプレート

## 概要

DCF、LBO、3表連動モデル、コンプス — ファイル成果物として作成。[`model-builder`](../../plugins/agent-plugins/model-builder) Cowork プラグインと同一ソース — このディレクトリは `POST /v1/agents` 用の Managed Agent クックブックです。

## デプロイ

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export CAPIQ_MCP_URL=... DALOOPA_MCP_URL=...
../../scripts/deploy-managed-agent.sh model-builder
```

## ステアリングイベント

[`steering-examples.json`](./steering-examples.json) を参照。

## セキュリティとハンドオフ

タスク分解型の分割です — 入力は信頼できる MCP から来るため、分割の目的は成果物の分離と再検証にあります。`Write` を持つワーカーはちょうど1つです:

| リーフ | ツール | コネクタ |
|---|---|---|
| `data-puller` | `Read`、`Grep` | CapIQ、Daloopa(読み取り専用) |
| **`builder`**(Write 保持者) | `Read`、`Write`、`Edit`、`Bash`(サンドボックス化) | なし |
| `auditor` | `Read`、`Grep` | なし |

`builder` が `./out/model.xlsx` を書き出した後、`auditor` が数値の突合とバランスを再チェックします。

**ハンドオフ:** `earnings-reviewer` や `pitch-agent` から呼び出される場合、呼び出し元エージェントの `handoff_request` が `scripts/orchestrate.py` によってここへルーティングされます。
