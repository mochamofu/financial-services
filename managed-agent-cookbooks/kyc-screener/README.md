# KYC Screener(KYC スクリーニングエージェント)— Managed Agent テンプレート

## 概要

オンボーディング書類をパースし、ルールエンジンを実行し、制裁/PEP スクリーニングを行い、不備をフラグします。[`kyc-screener`](../../plugins/agent-plugins/kyc-screener) Cowork プラグインと同一ソース — このディレクトリは `POST /v1/agents` 用の Managed Agent クックブックです。

## デプロイ

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export SCREENING_MCP_URL=...
../../scripts/deploy-managed-agent.sh kyc-screener
```

## ステアリングイベント

[`steering-examples.json`](./steering-examples.json) を参照。

## セキュリティとハンドオフ

オンボーディング書類は信頼できない入力として扱います。3階層の分離:

| 階層 | 信頼できない文書に触れるか | ツール | コネクタ |
|---|---|---|---|
| **`doc-reader`** | **はい** | `Read`、`Grep` のみ | なし |
| `rules-engine` / オーケストレーター | いいえ | `Read`、`Grep`、`Glob`、`Agent` | screening(読み取り専用) |
| **`escalator`**(Write 保持者) | いいえ | `Read`、`Write`、`Edit` | なし |

`doc-reader` は長さ制限付き・スキーマ検証済みの JSON を返します。`escalator` は `./out/escalation-<packet>.xlsx` を生成します。

**保証されないこと:** このエージェントが行うのはリスク格付けの推奨までであり、決定はコンプライアンスオフィサーが行います。
