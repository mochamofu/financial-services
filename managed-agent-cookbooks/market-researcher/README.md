# 市場調査エージェント(Market Researcher)— Managed Agent テンプレート

## 概要

セクターやテーマ → 業界概観 → 競争環境 → ピア比較 → アイデアのショートリスト → リサーチノート。[`market-researcher`](../../plugins/agent-plugins/market-researcher) Cowork プラグインと同一ソース — このディレクトリは `POST /v1/agents` 用の Managed Agent クックブックです。

## デプロイ

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export CAPIQ_MCP_URL=... FACTSET_MCP_URL=...
../../scripts/deploy-managed-agent.sh market-researcher
```

## ステアリングイベント

[`steering-examples.json`](./steering-examples.json) を参照。リサーチキューのイベントから起動するか、カバレッジマップ全体へファンアウトします。

## セキュリティとハンドオフ

サードパーティのレポートや発行体の資料は信頼できない入力として扱います。3階層の分離:

| 階層 | 信頼できない文書に触れるか | ツール | コネクタ |
|---|---|---|---|
| **`sector-reader`** | **はい** | `Read`、`Grep` のみ | なし |
| `comps-spreader` / オーケストレーター | いいえ | `Read`、`Grep`、`Glob`、`Agent` | CapIQ、FactSet(読み取り専用) |
| **`note-writer`**(Write 保持者) | いいえ | `Read`、`Write`、`Edit` | なし |

`sector-reader` は長さ制限付き・スキーマ検証済みの JSON を返します。`note-writer` は `./out/primer-<sector>.docx`(スライドが要求された場合は `.pptx` も)を生成します。

**ハンドオフ:** アイデアのショートリストに挙がった個別銘柄をモデル化するには、`model-builder` 宛の `handoff_request` を発行します。`scripts/orchestrate.py` がそれを新しいステアリングイベントとしてルーティングします。
