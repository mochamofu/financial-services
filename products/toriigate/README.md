# ⛩️ ToriiGate — AI Access Gateway

**悪意あるAIエージェント／AIクローラーのアクセスを、見える化し・選別し・止め・課金する、月額サブスク型ゲートウェイ。**

鳥居は「くぐってよい者とそうでない者を分ける結界」。AIボットが全Webトラフィックの過半を占め、自律型エージェントのトラフィックが前年比+7,851%で急増する時代([出典](./docs/market-research.md))に、あなたのサイト・API・社内システムの入口に立つ結界です。

これは事業構想の実証として作った **動くMVP** です。市場調査・事業計画・プロダクトが揃っています。

- 🗺️ [**アーキテクチャ図（実行時フロー・構成・テストと事業の流れ）**](./docs/architecture.md)
- 📊 [市場調査（全出典付き）](./docs/market-research.md)
- 📈 [事業計画（価格・GTM・競合）](./docs/business-plan.md)
- 🗾 [**日本市場GTMプレイブック（誰に・どこに・どう売るか）**](./docs/gtm-japan.md)
- 🧭 [プロダクト・ロードマップ（MVP→製品）](./docs/product-roadmap.md)
- 🎤 [1枚要約（営業・投資家向け）](./docs/pitch.md)
- 🛡️ [セキュリティ評価レポート（レッドチーム＋誤検知＋コード監査＋ファジング）](./docs/security-assessment.md)
- 🔁 [**多モデル検証プロトコル（そのまま貼れるレビュープロンプト付き）**](./docs/review-protocol.md)
- 🤝 [信頼・コンプライアンス資料パック（データ取扱い・整備状況・質問票）](./docs/trust-and-compliance.md)
- 🚀 [デプロイ／運用ガイド](./docs/deployment.md)
- 🛠️ 動くゲートウェイ → `gateway/`（レッドチームハーネス → `gateway/redteam/`）

## 無料診断（デプロイ不要・防御を約束しない安全な入口）

見込み客が自分のアクセスログを渡すだけで「どのAIボットがどれだけ来ているか」を可視化:

```bash
cd gateway
python3 -m toriigate.logscan /var/log/nginx/access.log --html exposure.html
# JSONログなら --format json
# 試すだけなら同梱のサンプル: redteam/fixtures/sample_access.txt
python3 -m toriigate.logscan redteam/fixtures/sample_access.txt
```

デプロイもトラフィック傍受も不要。**"守れる"とは一切約束せず、現状の露出だけを見せる**
ので、最初の一歩(実トラフィックの実態把握)を安全に踏める。

---

## 30秒で動かす

```bash
cd gateway
python3 demo.py          # 依存ゼロ。多種のトラフィックを判定して表示
```

出力例（人間は通し、なりすましGPTBotと学習クローラーは遮断、スクレイパーはチャレンジ、ハニーポット/脆弱性プローブは悪性判定）：

```
✅  ALLOW     [human] score=5
⛔  BLOCK     [spoofed_bot] score=92   GPTBot from WRONG ip
⛔  BLOCK     [ai_training_crawler]    ClaudeBot
🧩  CHALLENGE [scraper] score=60       curl
⛔  BLOCK     [malicious] score=98      honeypot (robots.txt無視)
```

## 既存サイトの前に立てる（CDN移行不要）

```bash
cd gateway
python3 -m toriigate.proxy --origin http://localhost:3000 --port 8080
# → http://localhost:8080/_torii/dashboard で可視化ダッシュボード
```

## 既存アプリに1行で組み込む（FastAPI / Starlette / Django ASGI）

```python
from toriigate import Gateway, Policy
from toriigate.asgi import ToriiGateMiddleware

app = ToriiGateMiddleware(app, Gateway(Policy.load("config/policy.example.yaml")))
```

---

## 何をするのか

| 層 | 検知するもの |
|---|---|
| **トラップ** | ハニーポットパス（robots.txt無視の証拠）、脆弱性プローブ（`.env`, `wp-login` 等） |
| **身元** | UA署名 × 公開IPレンジ照合 → GPTBot等の**なりすましを検知** |
| **フィンガープリント** | ブラウザを詐称するが標準ヘッダを欠く自動化ツール |
| **振る舞い** | リクエストレート、累犯IPの記憶 |
| **署名検証** | **Web Bot Auth (RFC 9421 / Ed25519)** — 正当なエージェントを暗号学的に許可 |

## 本番運用（プロダクション対応）

MVPの検知エンジンに加え、「売れる製品」の運用基盤を備える（詳細は
[deployment.md](./docs/deployment.md)）:

- **メトリクス**：`/_torii/metrics`（Prometheus）＋ **ヘルスチェック** `/_torii/healthz` `/readyz`
- **構造化ログ**：`TORII_LOG=json` で1決定=1行（ELK/Datadog/CloudWatch向け）
- **水平スケール**：`TORII_REDIS_URL` でレート/累犯状態をフリート共有（`StateStore`）
- **脅威フィード自動更新**：`python3 -m toriigate.threatfeed`（IPレンジの日次更新）
- **Docker**：`docker compose up --build` で gateway＋origin＋Redis が起動
- **管理エンドポイント認証**：`admin_token`、TLS終端配下の `trusted_proxies`

判定に応じた**段階的アクション**：`allow` / `block(403)` / `challenge`（Proof-of-Workで人間は一瞬・大量自動化は非経済的に）/ `throttle(429)` / `tarpit` / `monetize(402 = pay-per-crawl)` / `monitor`（検知のみ）。

ポリシーはテナントごとにYAML/JSONで定義（[注釈付き例](./gateway/config/policy.example.yaml)）。既定は「SEO・AI検索・ユーザー代理エージェントは通し、学習クローラー・なりすまし・悪性は止める」— [Perplexity論争](./docs/market-research.md)のような誤遮断を避ける設計です。

## なぜこの形なのか（1段落で）

「AIアクセス遮断」を単機能でグローバルに売ると、Cloudflareらの無料化・デフォルト化に潰されます([調査の結論](./docs/market-research.md#4-仮説の総合判断))。ToriiGateは大手セキュリティの勝ちパターン（無料で配って法人課金／他社流通に相乗り／データのネットワーク効果／**大手が追随できない設計**）を、大手が手薄な **「日本市場 × Web/CDNの外側（API・社内）× 身元検証（Web Bot Auth）× 無料と$3,490/月の価格空白」** に集中適用します。正面衝突しない局地戦です。

## プロジェクト構成

```
toriigate/
├── README.md
├── docs/
│   ├── market-research.md   # 全出典付き市場調査
│   ├── business-plan.md     # 価格・GTM・競合ポジショニング
│   └── pitch.md             # 1枚要約
└── gateway/                 # 動くMVP（依存最小・テスト49件）
    ├── demo.py              # オフライン判定デモ
    ├── pyproject.toml
    ├── config/policy.example.yaml
    ├── toriigate/
    │   ├── core.py          # 型（RequestContext, Decision, ...）
    │   ├── signatures.py    # 既知クローラー/エージェント/プローブ辞書
    │   ├── netranges.py     # 公開IPレンジ（なりすまし検証）
    │   ├── scoring.py       # 多層検知エンジン
    │   ├── policy.py        # テナントポリシー
    │   ├── challenge.py     # Proof-of-Workチャレンジ
    │   ├── botauth.py       # Web Bot Auth (RFC 9421 / Ed25519)
    │   ├── engine.py        # 全体を束ねるGateway
    │   ├── events.py        # ダッシュボード用イベントログ
    │   ├── dashboard.py     # 単一ファイルHTMLダッシュボード
    │   ├── robotsgen.py     # ポリシーからrobots.txt生成
    │   ├── plans.py         # サブスクプラン定義
    │   ├── asgi.py          # ASGIミドルウェア導入形態
    │   └── proxy.py         # リバースプロキシ導入形態
    └── tests/               # pytest（49件）
```

## テスト・品質ゲート

```bash
cd gateway
pip install pytest                  # 任意: PyYAML, cryptography, bandit
./quality.sh                        # テスト＋ファジング＋レッドチーム評価＋静的解析
python3 -m pytest -q                # テストのみ
python3 -m redteam.fuzz             # 攻撃者到達パーサーのファジング
python3 -m redteam.run_assessment   # 検知率・誤検知率の実測
```

`quality.sh` が緑になってから、[多モデル検証プロトコル](./docs/review-protocol.md)で
別ベンダーのモデルに敵対的レビューをさせる、という二段構えを想定している。

コア（検知・ポリシー・チャレンジ・プロキシ・ASGI）は**Python標準ライブラリのみ**。`cryptography` はWeb Bot Auth署名検証に、`PyYAML` はYAMLポリシーに使う任意依存で、無い場合はその機能だけ無効化して動作します。

---

> ⚠️ 本リポジトリは事業構想の実証です。調査数値・価格・法令解釈（著作権法30条の4、AI事業者ガイドライン等）は公開情報に基づくもので、投資判断・法的助言ではありません。実運用・事業化の前に専門家の確認を要します。
