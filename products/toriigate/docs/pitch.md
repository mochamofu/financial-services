# ToriiGate — 1枚要約（営業・投資家向け）

**⛩️ AIエージェント／AIクローラーのアクセスを、見える化し、選別し、止め、課金する。**

## 問題
AIボットはいま全Webトラフィックの過半（自動化51%、[Imperva 2025](https://www.imperva.com/blog/2025-imperva-bad-bot-report-how-ai-is-supercharging-the-bot-threat/)）。**自律型エージェントのトラフィックは前年比+7,851%**（[HUMAN 2026](https://www.humansecurity.com/newsroom/2026-state-of-ai-traffic-cyberthreat-benchmark-report/)）。単一サイトに毎分3.9万リクエストという実質DDoSも（[Fastly 2025](https://www.fastly.com/blog/ai-bots-q2-2025-trends-fastlys-threat-insights-report)）。国内では**AIクローラーで従量課金が跳ね20万円の想定外請求**という事故も起きている。だが企業の**97%が脅威を予想しつつ、対策予算はわずか6%**（[Arkose 2026](https://www.arkoselabs.com/latest-news/new-research-skyrocketing-agentic-ai-threat-disparity-funds-allocated-to-defense-press-release/)）。

## なぜ今の製品では守れないか
- Cloudflare等の遮断は**CDN移行が前提** — API・社内システムは守れない（高度ボットの標的の44%は既にAPI）
- 専業ベンダーは**月額$3,490〜** — 日本の中堅・SMBには高すぎる
- 無料OSS（Anubis）は**数ヶ月でスクレイパーに突破**され持続しない
- 日本語で・国内商習慣で・法令の言葉で売る専業ベンダーが**不在**

## ToriiGateの解
CDN移行なしで、既存アプリに**1行**（ASGIミドルウェア）または**前段プロキシ1コマンド**で導入。
- **多層検知**：ハニーポット・なりすまし（UA署名×公開IPレンジ）・ブラウザ詐称・振る舞い
- **段階的対応**：許可 / 遮断 / PoWチャレンジ / レート制限 / タールピット / **402課金** / 監視のみ
- **Web Bot Auth（RFC 9421）**：Ed25519署名で正当なエージェントを暗号学的に検証 — 「遮断」から「選別・課金」への市場シフトを先取り
- **可視化ダッシュボード**＋**robots.txt自動生成**（トラップ連動）

## 市場
ボット管理市場はCAGR **15〜20%**、上位のAIセキュリティ市場は22〜28%。国内サイバーセキュリティ市場は約1.9兆円（+9.2%）。

## ビジネスモデル
可視化**無料** → 月額 **¥29,800**（Starter）→ ¥98,000（Business）→ Enterprise個別。課金はリクエスト従量＋固定。将来はpay-per-crawlの徴収レベニューシェアを追加。

## GTM
創業者直販＋設定代行 → SMBセルフサーブ＋補助金（デジタル化・AI導入補助金）＋準MSP（Web制作会社）→ AWS Marketplace co-sell＋ディストリビューター。

## なぜ勝てるか
セキュリティ大手の勝ちパターン（無料で配って法人課金／他社流通に相乗り／データのネットワーク効果／**大手が追随できない設計**）を、**大手が手薄な「日本 × Webの外側 × 身元検証」**に集中適用する。正面衝突しない局地戦。

*本要約は公開情報に基づく事業構想であり、投資勧誘・法的助言ではありません。*
