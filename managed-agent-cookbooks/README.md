# 金融サービス向け Managed Agent テンプレート

このリポジトリのすべてのエージェントは**2つの形態**で提供されます。アナリストが今日からインストールできる Cowork プラグイン(リポジトリルートのバーティカルディレクトリを参照)と、プラットフォームチームが自社ワークフローエンジンの背後にデプロイする Claude Managed Agent テンプレートです。**同じエージェント、同じスキル — 実行面(サーフェス)を選ぶだけ。** 以下の各ディレクトリはデプロイマニフェストであり、対応するプラグインの正準のシステムプロンプトとスキルを参照しているため、真実のソース(source of truth)は1つです。

`../scripts/deploy-managed-agent.sh <slug>` を実行すると、スキルのアップロード、リーフワーカーの作成、解決済み設定での `POST /v1/agents` が行われます。各テンプレートには [`steering-examples.json`](./pitch-agent/steering-examples.json) と、セキュリティ階層およびハンドオフを説明するエージェントごとの README が付属します。

| エージェント | バーティカルプラグイン | Cowork タイル | CMA ステアリングイベント | リーフワーカー |
|---|---|---|---|---|
| [`pitch-agent`](./pitch-agent/) | investment-banking | コンプス、先行事例、LBO → ブランド仕様のピッチデック | `Build pitch book: <target> / <acquirer>, thesis: <text>` | researcher · modeler · **deck-writer** |
| [`market-researcher`](./market-researcher/) | equity-research | セクターやテーマ → 概観、競争環境、ピア比較、アイデアのショートリスト | `Primer: <sector or theme>, angle: <text>` | sector-reader · comps-spreader · **note-writer** |
| [`earnings-reviewer`](./earnings-reviewer/) | equity-research | 決算説明会+開示資料 → モデル更新 → ノートのドラフト | `Process earnings: <ticker> <period>` | transcript-reader · model-updater · **note-writer** |
| [`meeting-prep-agent`](./meeting-prep-agent/) | wealth-management | すべての顧客ミーティング前のブリーフィング資料 | `Briefing pack for <client-id>, meeting <event-id>` | profiler · news-reader · **pack-writer** |
| [`model-builder`](./model-builder/) | financial-analysis | DCF、LBO、3表連動モデル、コンプス — ファイルとして作成 | `Build <dcf\|lbo\|3-stmt> for <ticker>, assumptions: {...}` | data-puller · **builder** · auditor |
| [`gl-reconciler`](./gl-reconciler/) | financial-analysis | ブレイクを発見し、根本原因を追跡し、承認フローに回付 | `Reconcile GL vs subledger, trade date <D>, classes: <list>` | reader · critic · **resolver** |
| [`kyc-screener`](./kyc-screener/) | financial-analysis | オンボーディング書類をパースし、ルールを実行し、不備をフラグ | `Screen onboarding packet <id>` | doc-reader · rules-engine · **escalator** |
| [`valuation-reviewer`](./valuation-reviewer/) | private-equity | GP パッケージを取り込み、バリュエーションを実行し、LP 向けレポートを準備 | `Review portco valuations for fund <X> as of <date>` | package-reader · valuation-runner · **publisher** |
| [`month-end-closer`](./month-end-closer/) | financial-analysis | 未払計上、ロールフォワード、差異コメンタリー | `Close <entity> for period <YYYY-MM>` | ledger-reader · rollforward · **poster** |
| [`statement-auditor`](./statement-auditor/) | private-equity | 配布前の LP 向け計算書を監査 | `Tie out statement batch <id> against <fund> NAV pack` | statement-reader · reconciler · **flagger** |

**太字**のリーフ = `Write` を持つ唯一のワーカー。

## マニフェストと API の対応

`agent.yaml` ファイルは実際の `POST /v1/agents` のフィールド名を使いつつ、デプロイスクリプトが解決するいくつかの簡便記法を提供します。

| マニフェストの記法 | 解決結果 |
|---|---|
| `system: {file: ../../plugins/agent-plugins/<slug>/agents/<slug>.md, append: "..."}` | `system: "<インライン化された内容 + append>"` |
| `system: {text: "..."}` | `system: "<text>"` |
| `skills: [{from_plugin: ../../plugins/agent-plugins/<slug>}]` | そのディレクトリ配下の `skills/*` をすべてアップロード → `[{type: custom, skill_id: ...}, ...]` |
| `skills: [{path: ../../...}]` | `skills: [{type: custom, skill_id: <アップロード済み ID>}]` |
| `callable_agents: [{manifest: ./subagents/x.yaml}]` | `callable_agents: [{type: agent, id: <作成済み ID>, version: latest}]` |

> **リサーチプレビュー:** `callable_agents`(マルチエージェント委譲)がサポートするのは**1階層の委譲のみ**です。オーケストレーターはワーカーを呼び出せますが、ワーカーはさらなるサブエージェントを呼び出せません。

## エージェント間ハンドオフ

名前付きエージェント同士が直接呼び合うことはありません。あるエージェントが別のエージェントを必要とする場合、出力に `handoff_request` を含めて発行します。[`../scripts/orchestrate.py`](../scripts/orchestrate.py)(または Temporal/Airflow/Guidewire のイベントバス)がそれを新しいステアリングイベントとして対象セッションにルーティングします。リファレンススクリプトはターゲットをハードコードの許可リストで制限し、ペイロードをスキーマ検証します — 脅威モデルについてはスクリプト冒頭のコメントを参照してください。
