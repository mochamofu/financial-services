# GL Reconciler(総勘定元帳照合エージェント)— Managed Agent テンプレート

## 概要

指定した約定日と資産クラスの集合について、総勘定元帳(GL)と補助元帳の間の不一致(ブレイク)を発見し、根本原因を追跡し、コントローラーの承認用に例外レポートを作成します。

[`gl-reconciler`](../../plugins/agent-plugins/gl-reconciler) Cowork プラグインと同一ソース — このディレクトリは `POST /v1/agents` 用の Managed Agent クックブックです。

## デプロイ

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export GL_MCP_URL=...           # read-only GL MCP
export SUBLEDGER_MCP_URL=...    # read-only subledger MCP
../../scripts/deploy-managed-agent.sh gl-reconciler
```

## ステアリングイベント

[`steering-examples.json`](./steering-examples.json) を参照。約定日と資産クラスのリストを与えてセッションを開始します。フォローアップイベントで単一のブレイクを再追跡することもできます。

## セキュリティとハンドオフ

このエージェントはカウンターパーティ/カストディアンの計算書を読み取ります — 外部者が作成した文書であり、敵対的な指示が含まれている可能性があります。テンプレートは、そうした文書内のペイロードがシェル、書き込みツール、社内システムに到達できない構造になっています:

| 階層 | 信頼できない文書に触れるか | ツール | コネクタ |
|---|---|---|---|
| **`reader`** | **はい** | `Read`、`Grep` のみ | なし |
| **オーケストレーター** | いいえ | `Read`、`Grep`、`Glob`、`Agent` | 読み取り専用の GL + 補助元帳 MCP |
| **`resolver`**(Write 保持者) | いいえ | `Read`、`Write`、`Edit` | なし |

`reader` は長さ制限付き・スキーマ検証済みの JSON のみを返します(`scripts/validate.py` で検証)。`critic` は、オーケストレーターがブレイクの集合を `resolver` に渡す前に、各ブレイクを信頼できるソースに対して独立に再検証します。`resolver` は例外レポートを `./out/` に書き出し、外部者のファイルを開くことは決してありません。

**ハンドオフ:** 検証済みのブレイクを Month-End Closer に渡すには、オーケストレーターが最終出力で `month-end-closer` 宛の `handoff_request` を発行します。`scripts/orchestrate.py`(または Temporal/Airflow ワーカー)がそれを新しいステアリングイベントとしてルーティングします。許可リスト+ペイロード検証のパターンはスクリプトを参照してください。

**保証されないこと:** このエージェントはいかなる基幹システム(system of record)にも書き込みません。元帳の調整には、エージェント外での人間の承認が必要です。
