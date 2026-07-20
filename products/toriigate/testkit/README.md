# ToriiGate 品質テスト手順書（3台＋AIエージェント）

手元の実機（Mac 1 / Windows 2）と契約中のコーディングエージェント（Codex / Z.ai）で、
**実トラフィックによる挙動テスト**を行うための手順書とツール一式。合成テストでは
埋められない「実世界で試す」を実行し、[CHECKLIST.md](./CHECKLIST.md) で合否を記録する。

```
testkit/
├── serve.sh / serve.ps1     # ワンコマンド起動（原本サーバ＋ゲートウェイ）
├── attack.sh / attack.ps1   # 攻撃バッテリー（スクレイパー/なりすまし/連打）
├── site/                    # デモ用メディアサイト（原本）
├── policies/                # monitor.json / strict.json
├── CHECKLIST.md             # 合否チェックリスト（記入式）
└── README.md                # この手順書
```

---

## 0. 全体像と役割分担

| 機体 | 役割 | 使うもの |
|---|---|---|
| **Mac** | ゲートウェイ＋原本のホスト | `serve.sh` |
| **Windows #1** | 正規の人間（ブラウザ閲覧） | Chrome / Edge |
| **Windows #2** | 攻撃者（自動化クライアント） | `attack.ps1` |
| **Codex / Z.ai** | 本物のAIエージェント | §4 のトンネル |

**前提**: 全機体が同一 Wi-Fi/LAN にいること（クラウド側から来るエージェントは §4 のトンネル）。
コアは Python 標準ライブラリのみ＝**pip 不要**。Python 3.10+ が各機体に入っていること。

---

## 1. Step 1 — ゲートウェイ起動（Mac）

```bash
# 自分のリポジトリを取得（初回のみ）
git clone https://github.com/mochamofu/financial-services.git
cd financial-services
git checkout claude/ai-threat-security-software-t1ejgo

# テストキットを起動（原本:3000 と ToriiGate:8080 が同時に立つ）
cd products/toriigate/testkit
chmod +x serve.sh attack.sh   # 初回のみ
./serve.sh
```

起動すると Mac の LAN IP（例 `192.168.1.50`）とアクセス先が表示される。
ブラウザで **`http://<Mac-IP>:8080/_torii/dashboard`** を開いておく（テスト中ずっと見る）。

> 初回に macOS が「python が受信接続を許可するか」を尋ねたら **許可**。
> ポートを変えたい場合は `PORT=9000 ./serve.sh`。

## 2. Step 2 — 人間テスト（Windows #1 / Mac / スマホ）

ブラウザで `http://<Mac-IP>:8080/` を開き、記事リンクをクリックして回遊する。

- **期待**: 普通に表示され、ダッシュボードで `human / allow` が増える。
- スマホ（同一Wi-Fi）や Mac の Safari でも試す。→ [CHECKLIST.md](./CHECKLIST.md) の **A**。
- **これが「誤検知0%」の実地検証**。実ブラウザは Accept ヘッダを送るので human と判定される。
  1件でも allow 以外になったら要調査（正規ユーザーを弾くのは事業上最悪）。

## 3. Step 3 — 攻撃者テスト（Windows #2）

Windows #2 の PowerShell で（`<Mac-IP>` は Step 1 で表示された IP）:

```powershell
cd <クローンした場所>\products\toriigate\testkit
.\attack.ps1 -Gateway http://<Mac-IP>:8080
```

スクレイパー・なりすまし・学習クローラー・プローブ・レート連打を順に実行し、
各 HTTP ステータスを表示する。→ [CHECKLIST.md](./CHECKLIST.md) の **B**。

- **block も challenge も 403**。区別はダッシュボードの**カテゴリ／アクション欄**で確認。
- 連打の最後は **429（throttle）** になるはず。
- Mac/Linux から攻撃する場合は `./attack.sh http://<Mac-IP>:8080`。

## 4. Step 4 — ★AIエージェントテスト（Codex / Z.ai）＝本命

この製品が本当に狙う相手。エージェントに次のように指示する:

> 「`http://<URL>/` を取得して内容を要約して」／「このサイトの記事を全部スクレイピングして」

**接続方法（重要）**:
- **エージェントが手元マシンでコマンド実行するタイプ**（ローカルの curl/python を叩く）
  → `<URL>` に **`http://<Mac-IP>:8080/`**（LAN IP）を渡す。
- **クラウド側から取得するタイプ**（Codex/Z.ai は多くこちら）
  → Mac でトンネルを張り、公開 URL を渡す:
  ```bash
  cloudflared tunnel --url http://localhost:8080     # または  ngrok http 8080
  ```
  出てきた `https://xxxx.trycloudflare.com` をエージェントに渡す。

**観察ポイント**（→ [CHECKLIST.md](./CHECKLIST.md) の **C**、ダッシュボードで確認）:
1. **どんな UA で来るか**（python-requests? node-fetch? 独自? ヘッドレスChrome?）
2. **どう処理されたか**（単純フェッチャー → challenge で JS を解けず実質ブロック＝「AIエージェントを止めた」実証。ヘッドレスブラウザで JS 実行できると突破するかも）
3. **/robots.txt を尊重するか**（`http://<URL>/robots.txt` を見せて挙動を記録）
4. **Codex と Z.ai で挙動が違う**はず。差分がそのまま実世界データ。

## 5. Step 5 — monitor モード＆ログ診断（本番前の正しい手順）

**monitor モード**（遮断せず観察だけ。本番投入前は必ずこれから）:
```bash
# Ctrl-C で一度止めてから
POLICY=policies/monitor.json ./serve.sh
```
→ 何も止めず、enforce なら何をしたかだけを記録。誤検知率を実データで測ってから enforce へ。

**より厳しいポリシー**を試す:
```bash
POLICY=policies/strict.json ./serve.sh
```

**ログ診断**（デプロイ不要。実サイトのログがあれば最良）:
```bash
cd ../gateway
python3 -m toriigate.logscan /path/to/your/nginx/access.log --html exposure.html
python3 -m toriigate.logscan redteam/fixtures/sample_access.txt   # 同梱サンプル
```

## 6. 結果の見方

| URL | 内容 |
|---|---|
| `/_torii/dashboard` | ライブ可視化（3秒更新・カテゴリ別・直近イベント） |
| `/_torii/stats` | 集計 JSON |
| `/_torii/metrics` | Prometheus 形式メトリクス |
| `/_torii/healthz` | ヘルスチェック |
| `/robots.txt` | ゲートウェイが生成する robots.txt |

---

## 7. これで分かること／分からないこと（正直に）

**分かる**: 実ブラウザ・実ツール・**実AIエージェント**に対する分類とアクション、実ブラウザでの
誤検知有無、ダッシュボード/メトリクスの動作。← 合成テストの弱点を埋める本命。

**分からない（未検証のまま）**:
- **本気の回避**: 完全ブラウザ偽装＋分散IPは内部レッドチームでも 0%＝すり抜ける（[../docs/security-assessment.md](../docs/security-assessment.md)）。
- **大規模負荷時の性能**（このプロキシはデモ向けの簡易サーバ）。
- **本番堅牢性・第三者ペンテスト**。

つまり本テストは「**既知型・実クライアント・実AIエージェントに対して正しく動くか**」を確かめるもので、
「販売できる製品品質の証明」ではない。そこは [../docs/product-roadmap.md](../docs/product-roadmap.md) の残作業。

## 8. トラブルシューティング

| 症状 | 対処 |
|---|---|
| 他機から繋がらない | 同一LANか確認 / Mac のファイアウォールで python の受信を許可 / IP を再確認（`ipconfig getifaddr en0`） |
| `No module named toriigate` | `products/toriigate/gateway` から実行しているか確認（serve.sh は自動で cd する） |
| `python3` が無い（Windows） | `python` を使う（serve.ps1 は `python`）。未導入なら python.org から導入 |
| ダッシュボードが 401 | `admin_token` を設定したポリシーを使っている。ヘッダ `X-Torii-Admin-Token` が必要 |
| Web Bot Auth を試したい | `pip install cryptography`（署名検証の高度テスト。別途手順が要る場合は相談を） |
| クラウドのエージェントから届かない | §4 のトンネル（cloudflared/ngrok）で公開 URL を渡す |
