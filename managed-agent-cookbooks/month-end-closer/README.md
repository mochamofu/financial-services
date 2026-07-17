# Month-End Closer(月次決算エージェント)— Managed Agent テンプレート

## 概要

未払計上、ロールフォワード、差異コメンタリー。[`month-end-closer`](../../plugins/agent-plugins/month-end-closer) Cowork プラグインと同一ソース — このディレクトリは `POST /v1/agents` 用の Managed Agent クックブックです。

## デプロイ

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export GL_MCP_URL=...
../../scripts/deploy-managed-agent.sh month-end-closer
```

## ステアリングイベント

[`steering-examples.json`](./steering-examples.json) を参照。

## セキュリティとハンドオフ

裏付けとなる請求書やベンダーの計算書は信頼できない入力として扱います。3階層の分離:

| 階層 | 信頼できない文書に触れるか | ツール | コネクタ |
|---|---|---|---|
| **`ledger-reader`** | **はい** | `Read`、`Grep` のみ | なし |
| `rollforward` / オーケストレーター | いいえ | `Read`、`Grep`、`Glob`、`Agent` | internal-gl(読み取り専用) |
| **`poster`**(Write 保持者) | いいえ | `Read`、`Write`、`Edit` | なし |

`poster` は `./out/close-package-<entity>-<period>.xlsx` を生成します。仕訳(JE)ドラフトはステージングされるのみで、GL には記帳されません。

**ハンドオフ:** `gl-reconciler` から検証済みブレイクを含む `handoff_request` イベントを受け取り、決算コメンタリーに織り込みます。
