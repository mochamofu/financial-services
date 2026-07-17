# Valuation Reviewer — Managed Agent テンプレート

## 概要

GP パッケージを取り込み、バリュエーションテンプレートを実行し、LP 向けレポートを準備します。[`valuation-reviewer`](../../plugins/agent-plugins/valuation-reviewer) Cowork プラグインと同一ソース — このディレクトリは `POST /v1/agents` 用の Managed Agent クックブックです。

## デプロイ

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export PORTFOLIO_MCP_URL=...
../../scripts/deploy-managed-agent.sh valuation-reviewer
```

## ステアリングイベント

[`steering-examples.json`](./steering-examples.json) を参照。

## セキュリティとハンドオフ

GP 提供のバリュエーションパッケージは信頼できない入力として扱います。3階層の分離:

| 階層 | 信頼できない文書に触れるか | ツール | コネクタ |
|---|---|---|---|
| **`package-reader`** | **はい** | `Read`、`Grep` のみ | なし |
| `valuation-runner` / オーケストレーター | いいえ | `Read`、`Grep`、`Glob`、`Agent` | portfolio(読み取り専用) |
| **`publisher`**(Write 保持者) | いいえ | `Read`、`Write`、`Edit` | なし |

`package-reader` は長さ制限付き・スキーマ検証済みの JSON を返します。`publisher` は `./out/lp-pack-<fund>.xlsx` を生成します。

**ハンドオフ:** フラグされたポートフォリオ企業を GL Reconciler に渡すには、`gl-reconciler` 宛の `handoff_request` を発行します。`scripts/orchestrate.py` がルーティングします。

**保証されないこと:** LP レポートには、このエージェント外での IR と CCO の承認が必要です。
