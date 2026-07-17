# Claude for Financial Services(金融サービス向け Claude)

投資銀行、株式リサーチ、プライベートエクイティ、ウェルスマネジメントなど、金融サービスで最もよく見られるワークフロー向けのリファレンスエージェント、スキル、データコネクタ集です。

ここにあるものはすべて、**1つのソースから2通りの方法**で利用できます。[Claude Cowork](https://claude.com/product/cowork) プラグインとしてインストールするか、[Claude Managed Agents API](https://docs.claude.com/en/api/managed-agents) を通じて自社のワークフローエンジンの背後にデプロイするかを選べます。同じシステムプロンプト、同じスキル — 実行場所はあなたが選択します。

> [!IMPORTANT]
> このリポジトリの内容は、投資・法務・税務・会計に関する助言を構成するものではありません。これらのエージェントは、モデル、メモ、リサーチノート、勘定照合といったアナリストの成果物のドラフトを作成するものであり、資格を持つ専門家によるレビューを前提としています。投資推奨の実行、取引の執行、リスクの引き受け、元帳への記帳、オンボーディングの承認は行いません。すべてのアウトプットは人間の承認(サインオフ)待ちの状態で提示されます。アウトプットの検証、および貴社に適用される法令・規制の遵守は、利用者の責任となります。

リポジトリの内容:

- **[エージェント](#エージェント)** — 名前付きのエンドツーエンドなワークフローエージェント(Pitch Agent、Market Researcher、GL Reconciler など)。各エージェントは Cowork プラグイン**および** `/v1/agents` 経由でデプロイする [Claude Managed Agent テンプレート](./managed-agent-cookbooks)の両方の形で提供されます。
- **[バーティカルプラグイン](#バーティカルプラグイン)** — 基盤となるスキル、スラッシュコマンド、データコネクタを金融サービス(FSI)の業務領域ごとにまとめたバンドル。フルエージェントは不要で `/comps`、`/dcf`、`/earnings` とコネクタだけが欲しい場合は、こちらを単体でインストールできます。

## エージェント

各エージェントは、実行するワークフローにちなんで命名されています。これらは出発点です。自分の業務に合うものをインストールし、プロンプト、スキル、コネクタを貴社のやり方に合わせてチューニングしてください。

各エージェントプラグインは**自己完結型**です — 使用するスキルを同梱しているため、エージェントをインストールするだけで利用できます。

| 業務機能 | エージェント | 何をするか |
|---|---|---|
| **カバレッジ&アドバイザリー** | **[Pitch Agent(ピッチ資料作成エージェント)](./plugins/agent-plugins/pitch-agent)** | 類似会社比較、先行事例、LBO → ブランド仕様のピッチデックまでエンドツーエンドで作成 |
| | **[Meeting Prep Agent(ミーティング準備エージェント)](./plugins/agent-plugins/meeting-prep-agent)** | すべての顧客ミーティング前にブリーフィング資料を用意 |
| **リサーチ&モデリング** | **[Market Researcher(市場調査エージェント)](./plugins/agent-plugins/market-researcher)** | セクターやテーマ → 業界概観、競争環境、ピア比較、アイデアのショートリスト |
| | **[Earnings Reviewer(決算レビューエージェント)](./plugins/agent-plugins/earnings-reviewer)** | 決算説明会+開示資料 → モデル更新 → ノートのドラフト |
| | **[Model Builder(モデル構築エージェント)](./plugins/agent-plugins/model-builder)** | DCF、LBO、3表連動モデル、コンプス — Excel 上でライブ作成 |
| **ファンドアドミン&財務オペレーション** | **[Valuation Reviewer(バリュエーションレビューエージェント)](./plugins/agent-plugins/valuation-reviewer)** | GP パッケージを取り込み、バリュエーションテンプレートを実行し、LP 向けレポートを準備 |
| | **[GL Reconciler(総勘定元帳照合エージェント)](./plugins/agent-plugins/gl-reconciler)** | 不一致(ブレイク)を発見し、根本原因を追跡し、承認フローに回付 |
| | **[Month-End Closer(月次決算エージェント)](./plugins/agent-plugins/month-end-closer)** | 未払計上、ロールフォワード、差異コメンタリー |
| | **[Statement Auditor(計算書監査エージェント)](./plugins/agent-plugins/statement-auditor)** | 配布前の LP 向け計算書を監査 |
| **オペレーション&オンボーディング** | **[KYC Screener(KYC スクリーニングエージェント)](./plugins/agent-plugins/kyc-screener)** | オンボーディング書類をパースし、ルールエンジンを実行し、不備をフラグ |

Managed Agent としてのデプロイ — `agent.yaml`、リーフワーカーのサブエージェント、ステアリングイベントの例、エージェントごとのセキュリティノート — については **[managed-agent-cookbooks/](./managed-agent-cookbooks)** を参照してください。

## リポジトリ構成

```
plugins/
  agent-plugins/               # 名前付きエージェント — それぞれ自己完結型プラグイン
  vertical-plugins/            # FSI 業務領域ごとのスキル+コマンドのバンドル、MCP コネクタ
  partner-built/               # パートナー製プラグイン(LSEG、S&P Global)
managed-agent-cookbooks/       # Claude Managed Agent クックブック — エージェントごとに1ディレクトリ
claude-for-msft-365-install/   # Claude Microsoft 365 アドインをプロビジョニングする管理者向けツール
scripts/                       # deploy-managed-agent.sh · check.py · validate.py · orchestrate.py · sync-agent-skills.py
```

## はじめに

### Cowork

Cowork で **Settings → Plugins → Add plugin** を開き、次のいずれかを実行します。

- **このリポジトリの URL を貼り付ける** — `https://github.com/anthropics/financial-services` — その後、マーケットプレイスの一覧から必要なエージェントとバーティカルを選択する、または
- **zip をアップロードする** — `plugins/` 配下の任意のディレクトリ(例: `plugins/agent-plugins/pitch-agent/`)を zip 化してドロップします。

### Claude Code

```bash
# マーケットプレイスを追加
claude plugin marketplace add anthropics/financial-services

# コアのスキル+コネクタ(最初にインストール)
claude plugin install financial-analysis@claude-for-financial-services

# 名前付きエージェント — 必要なものを選択
claude plugin install pitch-agent@claude-for-financial-services
claude plugin install gl-reconciler@claude-for-financial-services
claude plugin install market-researcher@claude-for-financial-services

# バーティカルのスキルバンドル
claude plugin install investment-banking@claude-for-financial-services
claude plugin install equity-research@claude-for-financial-services
```

インストールすると、エージェントは Cowork のディスパッチに表示され、スキルは関連する場面で自動的に発動し、スラッシュコマンドがセッション内で使えるようになります(`/comps`、`/dcf`、`/earnings`、`/ic-memo` など)。

### Claude Managed Agents

```bash
export ANTHROPIC_API_KEY=sk-ant-...
scripts/deploy-managed-agent.sh gl-reconciler
```

[`managed-agent-cookbooks/`](./managed-agent-cookbooks) 配下の各テンプレートは、対応するプラグインと同じシステムプロンプトとスキルを参照しています。デプロイスクリプトは、ファイル参照を解決し、スキルをアップロードし、リーフワーカーのサブエージェントを作成し、オーケストレーターを `/v1/agents` に POST します。エージェント間の `handoff_request` イベントを自前のオーケストレーション層でルーティングするリファレンスイベントループについては [`scripts/orchestrate.py`](./scripts/orchestrate.py) を参照してください。

> **リサーチプレビュー:** サブエージェントへの委譲(`callable_agents`)はプレビュー機能です。セキュリティとハンドオフのガイダンスは各エージェントの README を参照してください。

## 全体の構成

| | 何であるか | 置き場所 |
|---|---|---|
| **エージェント** | ワークフローをエンドツーエンドで担う自己完結型プラグイン — システムプロンプトと使用するスキルのセット。Cowork と Managed Agent ラッパーの両方が同じディレクトリを参照します。 | `plugins/agent-plugins/<slug>/` |
| **スキル** | Claude が関連する場面で自動的に参照する、ドメイン知識・慣行・手順。バーティカル側で一度だけ作成され、各エージェントは必要なものの同期コピーを同梱します。 | `plugins/vertical-plugins/<vertical>/skills/`(ソース) · `plugins/agent-plugins/<slug>/skills/`(同梱コピー) |
| **コマンド** | 明示的に起動するスラッシュアクション(`/comps`、`/earnings`、`/ic-memo`)。 | `plugins/vertical-plugins/<vertical>/commands/` |
| **コネクタ** | Claude を自社データ(ターミナル、リサーチプラットフォーム、ドキュメントストア)につなぐ [MCP サーバー](https://modelcontextprotocol.io/)。 | `plugins/vertical-plugins/financial-analysis/.mcp.json` |
| **Managed Agent ラッパー** | ヘッドレスデプロイ用の `agent.yaml`+深さ1のサブエージェント+ステアリング例。 | `managed-agent-cookbooks/<slug>/` |

すべてファイルベースです — Markdown と JSON のみで、ビルドステップはありません。

## バーティカルプラグイン

まずは **financial-analysis** から始めてください — 共通のモデリングスキルとすべてのデータコネクタを含みます。必要なワークフローに応じてバーティカルを追加します。

| プラグイン | 追加される内容 |
|---|---|
| **[financial-analysis](./plugins/vertical-plugins/financial-analysis)** *(コア)* | コンプス、DCF、LBO、3表連動モデル、デック QC、Excel 監査。全11のデータコネクタ。 |
| **[investment-banking](./plugins/vertical-plugins/investment-banking)** | CIM、ティーザー、プロセスレター、買い手候補リスト、合併モデル、ディールトラッキング。 |
| **[equity-research](./plugins/vertical-plugins/equity-research)** | 決算ノート、新規カバレッジ、モデル更新、投資テーゼとカタリストのトラッキング。 |
| **[private-equity](./plugins/vertical-plugins/private-equity)** | ソーシング、スクリーニング、デューデリチェックリスト、投資委員会メモ、ポートフォリオモニタリング。 |
| **[wealth-management](./plugins/vertical-plugins/wealth-management)** | 顧客レビュー、ファイナンシャルプラン、リバランス、レポーティング、タックスロスハーベスティング(TLH)。 |
| **[fund-admin](./plugins/vertical-plugins/fund-admin)** | GL 照合、ブレイク追跡、未払計上、ロールフォワード、差異コメンタリー、NAV 突合。 |
| **[operations](./plugins/vertical-plugins/operations)** | KYC 書類のパースとルールグリッド評価。 |
| **[lseg](./plugins/partner-built/lseg)** *(パートナー)* | LSEG データによる債券レラティブバリュー、スワップカーブ、FX キャリー、オプションボラティリティ、マクロ金利モニタリング。 |
| **[sp-global](./plugins/partner-built/spglobal)** *(パートナー)* | S&P Capital IQ によるティアシート、決算プレビュー、ファンディングダイジェスト。 |

## MCP 連携

すべてのコネクタは **financial-analysis** コアプラグインに集約され、他のプラグインから共有されます。

| プロバイダー | URL |
|---|---|
| [Daloopa](https://www.daloopa.com/) | `https://mcp.daloopa.com/server/mcp` |
| [Morningstar](https://www.morningstar.com/) | `https://mcp.morningstar.com/mcp` |
| [S&P Global](https://www.spglobal.com/) | `https://kfinance.kensho.com/integrations/mcp` |
| [FactSet](https://www.factset.com/) | `https://mcp.factset.com/mcp` |
| [Moody's](https://www.moodys.com/) | `https://api.moodys.com/genai-ready-data/m1/mcp` |
| [MT Newswires](https://www.mtnewswires.com/) | `https://vast-mcp.blueskyapi.com/mtnewswires` |
| [Aiera](https://www.aiera.com/) | `https://mcp-pub.aiera.com` |
| [LSEG](https://www.lseg.com/) | `https://api.analytics.lseg.com/lfa/mcp` |
| [PitchBook](https://pitchbook.com/) | `https://premium.mcp.pitchbook.com/mcp` |
| [Chronograph](https://www.chronograph.pe/) | `https://ai.chronograph.pe/mcp` |
| [Egnyte](https://www.egnyte.com/) | `https://mcp-server.egnyte.com/mcp` |
| [Box](https://www.box.com/home) | `https://mcp.box.com` |

> MCP へのアクセスには、プロバイダーのサブスクリプションまたは API キーが必要な場合があります。

## Claude for Microsoft 365 — インストールツール

Microsoft 365 アドイン経由で Excel、PowerPoint、Word、Outlook 内で Claude を利用している場合、[`claude-for-msft-365-install/`](./claude-for-msft-365-install) は、Anthropic の API ではなく**自社のクラウド**(Vertex AI、Bedrock、または社内 LLM ゲートウェイ)に対してアドインをプロビジョニングするための管理者向けツールです。

これは(Cowork プラグインではなく)Claude Code プラグインで、IT 管理者を対象に、カスタマイズしたアドインマニフェストの生成、Azure 管理者同意の付与、Microsoft Graph 経由でのユーザー別ルーティング設定の書き込みをガイドします。インストール方法:

```bash
claude plugin install claude-for-msft-365-install@claude-for-financial-services
/claude-for-msft-365-install:setup
```

これは上記のエージェント・バーティカルプラグインとは別物です — テナントにアドインをデプロイするための導入路であり、デプロイ後にその中で動くのがここにあるエージェントとスキルです。

## 自社仕様へのカスタマイズ

これらはリファレンステンプレートです — 貴社の業務のやり方に合わせてチューニングすることで、より良くなります。

- **コネクタの差し替え** — `.mcp.json` を自社のデータプロバイダーや社内システムに向けます。
- **自社コンテキストの追加** — 自社の用語、プロセス、フォーマット基準をスキルファイルに記載します。
- **自社テンプレートの持ち込み** — `/ppt-template` で自社ブランドの PowerPoint レイアウトを Claude に学習させます。
- **エージェントのスコープ調整** — `agents/<slug>.md` を編集して、チームの実際のワークフローに合わせます。
- **独自エージェントの追加** — まだカバーされていないワークフロー向けに、この構造をコピーして作成します。

## スキル&コマンドリファレンス

<details>
<summary><b>financial-analysis</b> — コアのモデリング、Excel、デック QC</summary>

| スキル | コマンド | 説明 |
|---|---|---|
| comps-analysis | `/comps` | トレーディングマルチプルを用いた類似会社比較分析 |
| dcf-model | `/dcf` | WACC と感応度分析を含む DCF バリュエーション |
| lbo-model | `/lbo` | レバレッジド・バイアウト(LBO)モデル |
| 3-statement-model | `/3-statement-model` | 3表連動財務モデルテンプレートへのデータ投入 |
| audit-xls | `/debug-model` | Excel モデル監査 — 数式トレース、ハードコード検出、バランスチェック |
| clean-data-xls | — | Excel 上の表形式データの正規化とクリーニング |
| deck-refresh | — | デック全体の埋め込みチャート/テーブルの再リンクと更新 |
| competitive-analysis | `/competitive-analysis` | 競争環境と市場ポジショニング |
| ib-check-deck | — | プレゼン資料の誤り・整合性の QC |
| pptx-author | — | `.pptx` ファイルをヘッドレスで生成(Managed Agent モード) |
| xlsx-author | — | `.xlsx` ファイルをヘッドレスで生成(Managed Agent モード) |
| ppt-template-creator | `/ppt-template` | 再利用可能な PPT テンプレートスキルの作成 |
| skill-creator | — | 新しいスキルを作成するためのガイド |

</details>

<details>
<summary><b>investment-banking</b> — ディール資料とエグゼキューション</summary>

| スキル | コマンド | 説明 |
|---|---|---|
| strip-profile | `/one-pager` | ピッチブック用の1ページ企業プロファイル |
| pitch-deck | — | ピッチデックテンプレートへのデータ投入 |
| datapack-builder | — | CIM や開示資料からのデータパック作成 |
| cim-builder | `/cim` | 企業概要書(CIM)のドラフト作成 |
| teaser | `/teaser` | 匿名の1ページ企業ティーザー |
| buyer-list | `/buyer-list` | 戦略的買い手・金融買い手のユニバース |
| merger-model | `/merger-model` | EPS 希薄化/増加(accretion/dilution)の M&A 分析 |
| process-letter | `/process-letter` | 入札要領およびプロセス関連の書簡 |
| deal-tracker | `/deal-tracker` | 進行中ディール、マイルストーン、アクションアイテムのトラッキング |

</details>

<details>
<summary><b>equity-research</b> — カバレッジとレポート発行</summary>

| スキル | コマンド | 説明 |
|---|---|---|
| earnings-analysis | `/earnings` | 決算発表後の四半期アップデートレポート |
| earnings-preview | `/earnings-preview` | 決算前のシナリオ分析と注目指標 |
| initiating-coverage | `/initiate` | 機関投資家品質の新規カバレッジレポート |
| model-update | `/model-update` | 新データによる財務モデルの更新 |
| morning-note | `/morning-note` | モーニングミーティングノートとトレードアイデア |
| sector-overview | `/sector` | 業界概観とテーマ別レポート |
| thesis-tracker | `/thesis` | 投資テーゼの維持と更新 |
| catalyst-calendar | `/catalysts` | カバレッジ全体の今後のカタリストのトラッキング |
| idea-generation | `/screen` | 銘柄スクリーニングとアイデアソーシング |

</details>

<details>
<summary><b>private-equity</b> — ソーシングからポートフォリオ運営まで</summary>

| スキル | コマンド | 説明 |
|---|---|---|
| deal-sourcing | `/source` | 企業の発掘、CRM チェック、創業者向けアウトリーチのドラフト |
| deal-screening | `/screen-deal` | 持ち込み CIM・ティーザーの迅速な合否判定 |
| dd-checklist | `/dd-checklist` | ワークストリーム別のデューデリジェンスチェックリスト |
| dd-meeting-prep | `/dd-prep` | マネジメントプレゼンやエキスパートコールの準備 |
| unit-economics | `/unit-economics` | ARR コホート、LTV/CAC、ネットリテンション、収益の質 |
| returns-analysis | `/returns` | IRR/MOIC の感応度テーブル |
| ic-memo | `/ic-memo` | 投資委員会メモのドラフト作成 |
| portfolio-monitoring | `/portfolio` | ポートフォリオ企業の KPI と差異のトラッキング |
| value-creation-plan | `/value-creation` | クロージング後の100日プランと EBITDA ブリッジ |
| ai-readiness | `/ai-readiness` | ポートフォリオ企業の AI 対応度の評価 |

</details>

<details>
<summary><b>wealth-management</b> — アドバイザー業務</summary>

| スキル | コマンド | 説明 |
|---|---|---|
| client-review | `/client-review` | パフォーマンスとトーキングポイントを揃えた顧客ミーティング準備 |
| financial-plan | `/financial-plan` | 退職、教育、相続、キャッシュフローの見通し |
| portfolio-rebalance | `/rebalance` | アロケーションのドリフト分析と税効率を考慮したリバランス |
| client-report | `/client-report` | 顧客向けパフォーマンスレポート |
| investment-proposal | `/proposal` | 見込み顧客向けの投資提案書 |
| tax-loss-harvesting | `/tlh` | TLH 機会の特定とウォッシュセールの管理 |

</details>

## コントリビューション

ここにあるものはすべて Markdown と YAML です。フォークして、編集して、PR を出してください。新規コンテンツの追加方法:

- 新しいスキル → `plugins/vertical-plugins/<vertical>/skills/` 配下に追加し、`python3 scripts/sync-agent-skills.py` を実行して、そのスキルを同梱するエージェントへ伝播させます。
- 新しいエージェント → `plugins/agent-plugins/<slug>/`(`agents/<slug>.md` + `skills/` を含む)と、対応する `managed-agent-cookbooks/<slug>/` を作成します。
- プッシュ前に `python3 scripts/check.py` を実行してください — すべてのマニフェストの lint、クロスファイル参照の解決検証を行い、同梱スキルがバーティカルのソースからドリフトしている場合は失敗します。

## ライセンス

[Apache License 2.0](./LICENSE)
