# ミーティング準備エージェント(Meeting Prep Agent)— Managed Agent テンプレート

## 概要

すべての顧客ミーティング前のブリーフィング資料。[`meeting-prep-agent`](../../plugins/agent-plugins/meeting-prep-agent) Cowork プラグインと同一ソース — このディレクトリは `POST /v1/agents` 用の Managed Agent クックブックです。

## デプロイ

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export CRM_MCP_URL=... CAPIQ_MCP_URL=...
../../scripts/deploy-managed-agent.sh meeting-prep-agent
```

## ステアリングイベント

[`steering-examples.json`](./steering-examples.json) を参照。通常はワークフローエンジンがカレンダーイベントから起動します。

## セキュリティとハンドオフ

顧客提供の書類や受信メールは信頼できない入力として扱います。3階層の分割:

| 階層 | 信頼できない文書に触れるか | ツール | コネクタ |
|---|---|---|---|
| `profiler` | いいえ | `Read`、`Grep` | CRM、CapIQ(読み取り専用) |
| **`news-reader`** | **はい** | `Read`、`Grep` のみ | なし |
| **`pack-writer`**(Write 保持者) | いいえ | `Read`、`Write`、`Edit` | なし |

`pack-writer` は `./out/briefing-<client>.pptx` を生成します。顧客提供のコンテンツを直接開くことはありません。

**保証されないこと:** この資料はアドバイザー向けであり、顧客向けではありません。顧客への直接送付は行いません。
