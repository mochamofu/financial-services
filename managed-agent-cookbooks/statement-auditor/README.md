# 計算書監査エージェント(Statement Auditor)— Managed Agent テンプレート

## 概要

配布前の生成済み LP 向け計算書を監査します。[`statement-auditor`](../../plugins/agent-plugins/statement-auditor) Cowork プラグインと同一ソース — このディレクトリは `POST /v1/agents` 用の Managed Agent クックブックです。

## デプロイ

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export NAV_MCP_URL=...
../../scripts/deploy-managed-agent.sh statement-auditor
```

## ステアリングイベント

[`steering-examples.json`](./steering-examples.json) を参照。

## セキュリティとハンドオフ

生成された計算書は信頼できない入力として扱います(上流システムはスコープ外)。3階層の分離:

| 階層 | 信頼できない文書に触れるか | ツール | コネクタ |
|---|---|---|---|
| **`statement-reader`** | **はい** | `Read`、`Grep` のみ | なし |
| `reconciler` / オーケストレーター | いいえ | `Read`、`Grep`、`Glob`、`Agent` | nav(読み取り専用) |
| **`flagger`**(Write 保持者) | いいえ | `Read`、`Write`、`Edit` | なし |

`flagger` は `./out/signoff-<batch>.xlsx` を生成します。

**保証されないこと:** このエージェントが行うのは合格/保留の推奨までであり、配布は人間の承認後に IR が行います。
