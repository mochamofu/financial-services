# 金融サービス向けプラグイン(Financial Services Plugins)

金融サービス向けの Cowork プラグインおよび Claude Managed Agent テンプレート。各名前付きエージェントは、1つのソースから2つの形態で提供される。

## リポジトリ構造

```
├── plugins/
│   ├── agent-plugins/               #   名前付きエージェント — それぞれ自己完結型プラグイン
│   │   └── <slug>/
│   │       ├── .claude-plugin/plugin.json
│   │       ├── agents/<slug>.md     #   ← 正準のシステムプロンプト(ソースは1つ、ラッパーは2つ)
│   │       └── skills/              #   ← vertical-plugins/ から同期された同梱コピー
│   ├── vertical-plugins/            #   FSI バーティカル — スキルのソース、コマンド、MCP
│   │   └── <vertical>/
│   │       ├── .claude-plugin/plugin.json
│   │       ├── commands/
│   │       ├── skills/
│   │       └── .mcp.json
│   └── partner-built/               #   パートナー製プラグイン(LSEG、S&P Global)
├── managed-agent-cookbooks/         # CMA クックブック(名前付きエージェントごとに1ディレクトリ)
│   └── <slug>/
│       ├── agent.yaml               #   system + skills → ../../plugins/agent-plugins/<slug>/...
│       ├── subagents/*.yaml         #   深さ1のリーフワーカー
│       ├── steering-examples.json
│       └── README.md                #   セキュリティ階層とハンドオフの注記
├── claude-for-msft-365-install/     # Microsoft 365 アドイン用の管理者向けツール(FSI プラグインとは別物)
└── scripts/                         # deploy-managed-agent.sh, check.py, validate.py, orchestrate.py, sync-agent-skills.py
```

コミット前に `python3 scripts/check.py` を実行すること — すべてのマニフェストの lint、`system.file` / `skills.path` / `callable_agents.manifest` の全参照の解決検証を行い、`agent-plugins/<slug>/skills/` のコピーが `vertical-plugins/` のソースからドリフトしていれば失敗する。**スキルの編集は `vertical-plugins/` 側で行い**、その後 `python3 scripts/sync-agent-skills.py` を実行してエージェントバンドルへ伝播させること。

`check.py` は `pre-commit` フックも自動インストールする(`git config core.hooksPath .githooks` — Husky/Node は不使用)。このフックは、変更されたプラグインの `.claude-plugin/plugin.json` の `version` をパッチバンプし、ブランチが `main` よりちょうど1パッチ先になるようにする(コミットごとではなく1回だけバンプ — プラグインの `version` はインストール済みユーザーへの更新配信を制御する)。`version-bump` GitHub Action がバックストップとして PR 上で同じルールを強制する。単一コミットで回避するには `git commit --no-verify`。バンプのロジックは `scripts/version_bump.py` にある。

## 主要ファイル

- `marketplace.json`: マーケットプレイスマニフェスト — 全プラグインをソースパスとともに登録
- `plugin.json`: プラグインメタデータ — 名前、説明、バージョン、コンポーネント検出設定
- `commands/*.md`: `/plugin:command-name` として起動するスラッシュコマンド
- `skills/*/SKILL.md`: 特定タスク向けの詳細な知識とワークフロー
- `*.local.md`: ユーザー固有の設定(gitignore 対象)
- `mcp-categories.json`: プラグイン間で共有される正準の MCP カテゴリ定義

## 開発ワークフロー

1. Markdown ファイルを直接編集する — 変更は即座に反映される
2. コマンドは `/plugin:command-name` 構文でテストする
3. スキルはトリガー条件に一致したときに自動的に起動する
