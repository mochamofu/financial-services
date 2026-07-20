# ToriiGate 品質テスト 合否チェックリスト

各項目を実施し、実測結果を記入して合否を判定する。**block と challenge はどちらも
HTTP 403** なので、区別はダッシュボード（`/_torii/dashboard`）のカテゴリ／アクション欄で確認する。

## A. 誤検知（善を通せるか）— ここが最重要

| # | テスト | 期待 | 実測 | 合否 |
|---|---|---|---|---|
| A1 | Win#1 の Chrome/Edge で回遊 | `human` / allow・普通に表示 | | ☐ |
| A2 | Mac の Safari で回遊 | `human` / allow | | ☐ |
| A3 | スマホ実機（同一Wi-Fi）で閲覧 | `human` / allow | | ☐ |
| A4 | Googlebot を**正規レンジ**から（※後述, 任意） | `search_engine` / allow | | ☐ |

**A で1件でも allow 以外なら要調査**（正規ユーザーを弾くのは事業的に致命的）。

## B. 検知（悪を止められるか）

| # | テスト（attack スクリプトが実行） | 期待 | 実測 | 合否 |
|---|---|---|---|---|
| B1 | curl / python-requests | 403 challenge | | ☐ |
| B2 | GPTBot なりすまし（IP不一致） | 403 block（spoofed_bot） | | ☐ |
| B3 | ClaudeBot / Bytespider | 403 block（ai_training_crawler） | | ☐ |
| B4 | Googlebot 名乗り（IP不一致） | 403 block（spoofed_bot） | | ☐ |
| B5 | 未知の非ブラウザ UA | 403 challenge（unknown_bot） | | ☐ |
| B6 | /.env・/wp-login 等プローブ | 403 block（malicious） | | ☐ |
| B7 | ハニーポット /.well-known/torii-trap | 403 block（malicious） | | ☐ |
| B8 | ブラウザ風の高速連打（60発） | 403（レート超過で bot に再分類） | | ☐ |

## C. AIエージェント（本命）

| # | テスト | 期待 | 実測 | 合否 |
|---|---|---|---|---|
| C1 | Codex にサイト取得を指示 | 何らかの検知（UA・カテゴリを記録） | | ☐ |
| C2 | Z.ai にサイト取得を指示 | 同上（Codex と挙動比較） | | ☐ |
| C3 | エージェントが challenge を突破できるか | 単純フェッチャーなら不可＝実質ブロック | | ☐ |
| C4 | エージェントは /robots.txt を尊重するか | 記録（する/しない） | | ☐ |

> C は「正解」より**観察が目的**。UA・分類・突破可否・robots順守を記録すると、
> 実世界のAIアクセスの生データになる。

## D. 運用面

| # | テスト | 期待 | 実測 | 合否 |
|---|---|---|---|---|
| D1 | `/_torii/dashboard` が更新される | 3秒ごとに数字が増える | | ☐ |
| D2 | `/_torii/metrics` が Prometheus 形式 | `toriigate_requests_total{...}` | | ☐ |
| D3 | `/_torii/healthz` | 200 / `{"status":"ok"}` | | ☐ |
| D4 | `/robots.txt` が生成される | GPTBot 等の Disallow が並ぶ | | ☐ |
| D5 | monitor モードでは遮断されない | 全て通過するがカテゴリは記録 | | ☐ |

## E. ログ診断（デプロイ不要）

| # | テスト | 期待 | 実測 | 合否 |
|---|---|---|---|---|
| E1 | 実 nginx/Apache ログを logscan | 露出レポートが出る | | ☐ |
| E2 | 同梱サンプルを logscan | 自動化76.9% 等の例が再現 | | ☐ |

---

### 総合判定の考え方
- **A（誤検知）が全部 allow** かつ **B が期待どおり** → 「既知型に対する一次防壁」として機能。
- **C で本物のエージェントが止まる**（or 挙動を把握できる）→ 製品の中核仮説が実地で確認できた。
- ただし本テストは**本気の回避（完全ブラウザ偽装＋分散IP）や大規模負荷は対象外**。
  そこは未検証のままである点を忘れないこと（[../docs/security-assessment.md](../docs/security-assessment.md)）。
