# 調査レポート：対AIアクセス制御セキュリティ市場

> 実施日 2026-07-19 / ウェブ検索 40件超・独立エージェント3系統で並列調査。
> 数値はすべて出典付き。確証の弱いものは「未確認」と明記。

---

## 1. 背景・目的

「悪意あるAIエージェント／AIクローラーのアクセスを遮断する月額サブスク型セキュリティソフト」を新規事業として立ち上げられるか。大手セキュリティ企業の成長史から勝ちパターンを抽出し、現在のAI脅威市場の実態・競合と突き合わせ、日本発スモールチームが取るべき事業戦略を導く。

## 2. 論点・サブ論点と仮説

- **論点1**：大手セキュリティ企業はどんな流れで巨大化したか（勝ちパターンの抽出）
- **論点2**：悪意あるAIアクセスの脅威実態と、ボット管理／AIアクセス制御市場の競合・空白
- **論点3**：月額サブスクSaaSとしてのGTM（価格・パッケージ・チャネル）、日本市場特有の事情
- **検証する仮説**：「悪意あるAIアクセスを遮断する月額サブスクは大きく成長する事業になり得る」

---

## 3. 調査結果

### 論点1：セキュリティ大手の成長史 — 勝ちパターン

**第一世代（アンチウイルス）**
- **McAfee**：1987年、VirusScanをBBS経由のシェアウェアで配布。個人は実質無料、法人にサイトライセンスを課金。「個人に使わせ→職場に持ち込ませ→法人が払う」というPLGの原型を確立。電子配布で税引後利益率約45%、1993年でも従業員36人（[Encyclopedia.com](https://www.encyclopedia.com/books/politics-and-business-magazines/network-associates-inc)）。
- **Symantec/Norton**：1990年にPeter Norton Computingを約7,000万ドルで買収→1991年Norton AntiVirus発売。Dell/HP等の**OEMプリインストール**で消費者市場を制覇。1994年LiveUpdate（ネット経由更新）で優位確立、2000年代初頭に全世界1億ユーザー超（[Wikipedia: Norton AntiVirus](https://en.wikipedia.org/wiki/Norton_AntiVirus)）。
- **Trend Micro**：1988年創業。IntelとのOEM（LANDesk Virus Protect）、NovellのネットワークOSバンドル（1993年）で一気に拡大。近年もAWS Marketplace経由ARRが前年比+25%（[Wikipedia: Trend Micro](https://en.wikipedia.org/wiki/Trend_Micro)、[Form 20-F FY2005](https://www.sec.gov/Archives/edgar/data/0001089463/000119312506139949/d20f.htm)）。
- **Kaspersky**：CIHウイルス大流行（1998-99）を機に日欧のAV企業へ検知エンジンをOEM供与、自社ブランド以外でも収益化。2024年売上8.22億ドル（[Kaspersky沿革](https://esg.kaspersky.com/en/about-company/brief-history)）。

**第二世代（クラウド／サブスク）— 既存大手を追い抜いた設計**
- **CrowdStrike**：単一の軽量エージェントを一度入れれば追加モジュールを即時有効化できる設計＝低摩擦のLand & Expand。IPO時DBNR 147%（[S-1/A, 2019](https://www.sec.gov/Archives/edgar/data/1535527/000104746919003508/a2238988zs-1a.htm)）。**FY2026にARR 52.5億ドル**、セキュリティ専業で最速の$5B到達（[FY2026 Q4決算](https://ir.crowdstrike.com/news-releases/news-release-details/crowdstrike-reports-fourth-quarter-and-fiscal-year-2026)）。レガシーAV（Symantec/McAfee）置き換えを明示戦略に（[10-K FY2022](https://www.sec.gov/Archives/edgar/data/1535527/000153552722000006/crwd-20220131.htm)）。
- **Palo Alto Networks**：ハードFW企業から「プラットフォーム化」へ転換。次世代セキュリティARRはFY2026 Q2で63.3億ドル、FY2030に150億ドル目標（[TradingView/Zacks, 2026](https://www.tradingview.com/news/zacks:56296ea2c094b:0-can-platformization-drive-palo-alto-networks-next-growth-phase/)）。
- **Zscaler**：アプライアンス否定のクラウドプロキシ網。ARRは$1B→$2Bをわずか7四半期で倍増、FY2025 Q3で29億ドル（[Cybersecurity Magazine, 2024](https://cybermagazine.com/articles/lifetime-of-achievement-jay-chaudry-ceo-founder-zscaler)）。
- **SentinelOne**：ARR +122%（FY2023 Q2）から+23%（FY2027 Q1）へ減速。**同一カテゴリ2番手はマルチプロダクト化の速度で勝敗が決まる**実例。

**新興ネットワーク／ボット対策系**
- **Cloudflare**：無料＋$20単一プランで約2年→$200プラン→エンタープライズと段階的に上位展開（[Reforge](https://www.reforge.com/blog/cloudflare-ladder-of-growth)）。無料プランは①獲得コストゼロの見込み客プール、②トラフィック規模の経済、③全ユーザーからの脅威データ、の三重機能。ウェブの約20%・3,000万プロパティを収容、売上は2024年16億ドル→2025年21.68億ドル（[Umbrex](https://umbrex.com/resources/company-profiles/cloudflare/)）。
- **DataDome**：フリーミアムではなく「CDN標準機能の上位互換」を営業主導で販売。新規顧客の40%がWAF/CDN標準機能からのアップグレード（[TechCrunch, 2023](https://techcrunch.com/2023/03/30/datadome-raises-42m-series-c-bot-detection/)）。
- **HUMAN Security**：2022年にPerimeterXと合併し、ARR 1億ドル超・顧客500社超のカテゴリ統合（[TechCrunch, 2022](https://techcrunch.com/2022/07/27/human-security-merges-with-perimeterx-to-thwart-bots-and-automated-fraud/)）。

**→ 勝ちパターン（時代を超えて共通）**
1. **無料/安価で配って、価値実感後に法人課金**（McAfee 1987 → Cloudflare → CrowdStrikeのモジュール拡張）
2. **他社の流通・ブランドへの相乗り**（OEMプリインストール／バンドル → 現代はクラウドMarketplace）
3. **脅威イベントを需要の起爆剤に**（CIH流行 → Kasperskyの海外OEM）
4. **データのネットワーク効果**（ユーザー増→脅威サンプル増→検知精度→顧客増）
5. **既存勝者が追随できないアーキテクチャを選ぶ**（自社の収益源と食い合うため模倣が遅れる）

**時代固有**：第一世代=物理流通の一等地争奪、第二世代=ARR/DBNR経営とLand&Expandの製品実装、現在=プラットフォーマーの無料標準機能との共存設計（自らプラットフォーム化するCloudflare型か、専業特化のDataDome型か）。

---

### 論点2：AI脅威の実態と市場の空白

**脅威は複数の独立ソースで定量的に裏付け済み**
- 自動化トラフィックが全Webの51%に達し10年ぶりに人間超え、悪性ボットは37%（[Imperva 2025 Bad Bot Report](https://www.imperva.com/blog/2025-imperva-bad-bot-report-how-ai-is-supercharging-the-bot-threat/)、2024年データ）
- GPTBotトラフィックは2024→2025で**+305%**（[Cloudflare, 2025](https://blog.cloudflare.com/from-googlebot-to-gptbot-whos-crawling-your-site-in-2025/)）
- **agentic AI（自律エージェント）トラフィックは前年比+7,851%**（[HUMAN Security 2026 State of AI Traffic](https://www.humansecurity.com/newsroom/2026-state-of-ai-traffic-cyberthreat-benchmark-report/)、2025年データ）
- AIフェッチャーが単一サイトに**毎分39,000リクエスト**を送り小規模サイトが実質DDoS状態（[Fastly, 2025](https://www.fastly.com/blog/ai-bots-q2-2025-trends-fastlys-threat-insights-report)）
- **なりすまし事例**：Perplexityが宣言済みクローラーをブロックされると未宣言の「Chrome偽装UA」に切替、ASNをローテーションしてrobots.txtとWAFを回避とCloudflareが公表（[Cloudflare, 2025-08](https://blog.cloudflare.com/perplexity-is-using-stealth-undeclared-crawlers-to-evade-website-no-crawl-directives/)。ただしPerplexityは反論しており事実認定に争いあり）
- 企業リーダーの**97%**が12ヶ月以内のAIエージェント起因インシデントを予想する一方、専用予算はセキュリティ予算の**6%のみ**（[Arkose Labs 2026](https://www.arkoselabs.com/latest-news/new-research-skyrocketing-agentic-ai-threat-disparity-funds-allocated-to-defense-press-release/)）＝これから支出が立ち上がる市場

**市場規模**：ボット管理／ボットセキュリティはCAGR **15〜20%**で各社ほぼ一致（MarketsandMarkets 19.2%、Grand View 19.8%等）だが絶対額は2025年で10〜40億ドルと小さめのニッチ。上位のAIセキュリティ市場はCAGR 22〜28%。**遮断単機能で取れるTAMは限定的で、AIエージェント制御・API保護・身元検証を含めた市場定義が必要**。

**競合と価格の三極化**
- CDN/ホスティング組込の**無料〜低額**：Cloudflare無料プラン、Vercel BotID Basic無料
- 専業ベンダーの**月額$3,000〜1万ドル級**：DataDome（$3,490/月〜）、HUMAN、Akamai
- **無料OSS**：Anubis（PoW型。ただし2025年8月にスクレイパーが突破し始めたとCodebergが報告＝持続性に難）

**空白地帯（濃い順）**
- **(b) 日本市場**：AIクローラー/エージェント対策に特化した国内専業ベンダーは検索範囲で確認できず（未確認だが目立つプレイヤー不在）。情報流通は「Cloudflareの機能を代理店が解説」段階。
- **(c) API/社内システム/SaaSへのエージェントアクセス制御**：高度ボットの標的の44%が既にAPI。だがNHI（非人間アイデンティティ）管理戦略を持つ組織は**10%のみ**（Okta）。Okta/Microsoft/CyberArkがGA参入済みだが黎明期。
- **(d) Web Bot Auth（身元証明）**：RFC 9421（HTTP Message Signatures）上にEd25519署名でエージェントの身元を暗号学的に証明する標準。**2026年にIETFでWGがチャーター**、Cloudflare/Amazon/Akamai/OpenAIが支持、AWS WAFが2026年7月対応開始。検証・レジストリ・信頼評価の**実装レイヤーはまだ薄い**。
- **(a) 中間価格帯**：無料（CDN組込）と$3,490/月の間の**月額数万〜数十万円帯が空白**。ただし無料側の性能向上で圧迫されるリスク常在。

---

### 論点3：GTM（価格・チャネル）と日本市場

**価格**：課金軸は「保護対象リクエスト数」の従量＋月額固定が業界標準（席数課金は使われない）。SMBとエンタープライズの価格差は20〜200倍。フリーミアムは「**可視化フリー・制御有料**」の切り方がCloudflareの動きと整合。Cloudflareは2025年7月にPay Per Crawl（HTTP 402でクローラー課金）を発表、2026年に「遮断→選別・課金」へ市場をシフト中（[MIT Tech Review Japan](https://www.technologyreview.jp/s/364720/)）。

**チャネル**：セキュリティ分野で**PLG単独成功例はほぼ皆無**、最終的に組織購買（稟議・セキュリティレビュー）を通る。初期は「開発者向けセルフサーブ（トライアル装置）＋創業者直販（単価と学習）」の二段構え。**AWS Marketplace出品はほぼ必須**（co-sellで案件サイズ+40%、成約+20% — Tackle調べ）。日本は「ベンダー→ディストリビューター→二次代理店/SIer→顧客」の多段流通が標準だが、**注力商品に選ばれないと登録されただけで売られない**（[才流](https://sairu.co.jp/method/7097/)）。直販で「売れる型」を作ってから代理店に渡すのが正順。

**日本市場特有**
- 2025年度の国内サイバーセキュリティ市場は約1.9兆円（+9.2%）、セキュリティソフト市場は+14.1%成長（[IDC Japan](https://my.idc.com/getdoc.jsp?containerId=prAP54054925)）
- だが**中小企業の約6割がセキュリティ投資ゼロ**（[IPA 2024年度実態調査](https://www.ipa.go.jp/security/reports/sme/sme-survey2024.html)）。SMBには「セキュリティ」ではなく「クラウド課金削減／表示速度／無断学習防止」という**実利の言葉**で売る必要
- **20万円課金事故**：Metaのクローラーが画像変換エンドポイントを約250万回叩き従量課金で想定外請求という国内事例（[ai-native.jp](https://www.ai-native.jp/blog/cloudflare-ai-crawler-cost-protection-2026)）＝最強の営業素材
- **AI事業者ガイドライン第1.2版（2026-03-31）**でAIエージェント・フィジカルAIの定義とリスク・対策が追記（[経産省](https://www.meti.go.jp/shingikai/mono_info_service/ai_shakai_jisso/20260331_report.html)）。大企業の調達要件に事実上組み込まれる
- **著作権法30条の4**：AI学習は「情報解析」で原則許諾不要だが、robots.txt等の技術的措置による収集制限が明記され、「ただし書」で権利者利益を不当に害する場合は適用除外（[文化庁 AIと著作権に関する考え方](https://www.bunka.go.jp/seisaku/chosakuken/pdf/94097701_01.pdf)、2024-07）。**技術的措置（＝本製品）を講じること自体に法的な意味がある**
- **補助金**：SECURITY ACTION宣言→デジタル化・AI導入補助金が日本独自のGTM増幅装置（[IPA](https://www.ipa.go.jp/security/security-action/)）

---

## 4. 仮説の総合判断

**「そのままの形では不支持、条件付きで支持」。**

脅威と需要の成長は本物（複数独立ソースで裏付け）だが、「悪意あるAIアクセスを遮断する」**単機能の月額サブスク**は、①CDN大手による遮断機能の無料化・デフォルト化、②検知の消耗戦（Anubis突破が示す）、③市場ニーズの「遮断→選別・課金・身元検証」シフト、の3点で汎用グローバル市場での大成長は困難。

一方、以下の条件を組み合わせれば参入余地がある：
1. **日本市場特化**（専業ベンダー不在、法規制・補助金・商習慣が参入障壁かつ味方）
2. **Web/CDNの外側 — API・SaaS・社内システムへのエージェントアクセス制御**（標的の44%がAPI、NHI戦略保有10%のみ）
3. **Web Bot Auth前提の「身元検証・許可・課金」レイヤー**（2026年WGチャーター直後で実装層が薄い）
4. **中間価格帯**（無料CDN機能と$3,490/月の間）

→ この4条件を製品に落とし込んだのが本リポジトリの **ToriiGate**。事業計画は [business-plan.md](./business-plan.md) 参照。

---

## 付録：調査ソース分類

**独自ウェブ調査で新たに取得した主要ファクト（出典・年は本文中に明記）**
- agentic AIトラフィック+7,851%（HUMAN 2026）、GPTBot+305%（Cloudflare 2025）、自動化51%（Imperva 2025）
- Web Bot Auth IETF WGチャーター（2026）、AWS WAF対応（2026-07）
- AI事業者ガイドライン第1.2版のAIエージェント追記（2026-03）、著作権法30条の4とrobots.txt（文化庁2024-07）
- 国内SMBの6割が投資ゼロ（IPA 2024）、20万円課金事故（2026）

**主要な未確認事項**
- 日本国内のボット管理市場の単独規模、国内専業ベンダーの完全な不在（検索で発見できなかっただけの可能性）
- DataDome/HUMAN/Akamaiの日本での実勢価格、Cloudflare Enterprise Bot Managementの正式価格
- 大手セキュリティ各社の一部初期数値（NortonのOEMシェア等、単一二次ソース由来）
