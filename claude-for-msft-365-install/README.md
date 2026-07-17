# Claude for Office — 直接クラウド接続セットアップ

Claude Office アドインが Anthropic の API ではなく自社のクラウド(Vertex AI、Bedrock、または LLM ゲートウェイ)を呼び出すように設定するための管理者向けツールです。

## インストール

```bash
claude plugin marketplace add anthropics/financial-services
claude plugin install claude-for-msft-365-install@claude-for-financial-services
```

その後、セッション内で: `/claude-for-msft-365-install:setup`

## 更新

プラグインの最新バージョンを取得します:

```bash
claude plugin update claude-for-msft-365-install@claude-for-financial-services
```

適用するにはセッションを再起動してください。新しいオプションでマニフェストを再生成する必要がある場合のみ、`/claude-for-msft-365-install:setup` を再実行します。

## ブートストラップ

ユーザーごとの MCP サーバー、スキル、動的な設定を配布するには、ブートストラップエンドポイントをホストし、アドインをそこに向けます:

```bash
claude plugin marketplace add anthropics/financial-services   # 未追加の場合のみ
claude plugin install claude-for-msft-365-install@claude-for-financial-services
```

その後、セッション内で: `/claude-for-msft-365-install:bootstrap`

## コマンド

| コマンド | 何をするか |
|---|---|
| `/claude-for-msft-365-install:setup` | 対話式ウィザード — クラウドリソースのプロビジョニング、管理者同意、マニフェストの書き出し |
| `/claude-for-msft-365-install:manifest` | カスタマイズしたアドインマニフェスト XML の生成 |
| `/claude-for-msft-365-install:consent` | アドインのアプリ登録に対する Azure 管理者同意 URL |
| `/claude-for-msft-365-install:update-user-attrs` | Microsoft Graph の拡張属性経由でユーザー別設定を書き込み |
| `/claude-for-msft-365-install:bootstrap` | ブートストラップエンドポイントの構築 — ユーザーごとの MCP サーバー、スキル、動的設定 |
| `/claude-for-msft-365-install:debug` | デプロイ問題の診断 — 古い設定、接続失敗、アドインの欠落 |
