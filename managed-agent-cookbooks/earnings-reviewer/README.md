# Earnings Reviewer(決算レビューエージェント)— Managed Agent テンプレート

## 概要

決算説明会+開示資料 → モデル更新 → ノートのドラフト。[`earnings-reviewer`](../../plugins/agent-plugins/earnings-reviewer) Cowork プラグインと同一ソース — このディレクトリは `POST /v1/agents` 用の Managed Agent クックブックです。

## デプロイ

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export FACTSET_MCP_URL=... DALOOPA_MCP_URL=...
../../scripts/deploy-managed-agent.sh earnings-reviewer
```

## ステアリングイベント

[`steering-examples.json`](./steering-examples.json) を参照。オーケストレーション層からカバレッジリスト全体へファンアウトします — ティッカーごとに1セッション。

## セキュリティとハンドオフ

トランスクリプトとプレスリリースは信頼できない入力(untrusted)として扱います。3階層の分離:

| 階層 | 信頼できない文書に触れるか | ツール | コネクタ |
|---|---|---|---|
| **`transcript-reader`** | **はい** | `Read`、`Grep` のみ | なし |
| `model-updater` / オーケストレーター | いいえ | `Read`、`Grep`、`Glob`、`Agent` | FactSet、Daloopa(読み取り専用) |
| **`note-writer`**(Write 保持者) | いいえ | `Read`、`Write`、`Edit` | なし |

`transcript-reader` は長さ制限付き・スキーマ検証済みの JSON を返します。`note-writer` は `./out/note-<ticker>.docx` と、更新後のモデル `./out/model-<ticker>.xlsx` を生成します。

**ハンドオフ:** 決算を受けた投資テーゼの変更後に DCF を再構築するには、`model-builder` 宛の `handoff_request` を発行します。`scripts/orchestrate.py` がそれを新しいステアリングイベントとしてルーティングします。
