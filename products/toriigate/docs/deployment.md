# ToriiGate デプロイ / 運用ガイド

本番運用に必要な設定・スケール・監視・脅威フィード更新をまとめる。

## 1. 導入形態を選ぶ

| 形態 | 使いどころ | コマンド |
|---|---|---|
| リバースプロキシ | CDN移行なしで既存サイトの前段に | `python3 -m toriigate.proxy --origin http://app:3000` |
| ASGIミドルウェア | FastAPI/Starlette/Django ASGIに1行組込 | `ToriiGateMiddleware(app, Gateway(...))` |
| Docker | コンテナ運用・オーケストレーション | `docker compose up --build` |

## 2. 必須の環境変数

| 変数 | 必須 | 説明 |
|---|---|---|
| `TORII_SECRET` | **本番で必須** | チャレンジトークン/pass cookie の署名鍵。未設定だとプロセス毎にランダム生成され、複数ワーカーでcookieが検証失敗し正規ユーザーがチャレンジループに陥る(警告を出す) |
| `TORII_REDIS_URL` | 複数ワーカー時に必須 | 例 `redis://redis:6379/0`。レート窓・累犯記憶をフリート全体で共有。未設定ならプロセス内メモリ |
| `TORII_LOG` | 任意 | `json` で1決定=1行の構造化ログをstdoutへ(ELK/Datadog/CloudWatch向け) |
| `TORII_ORIGIN` / `TORII_PORT` / `TORII_POLICY` | 任意 | プロキシの起動パラメータ(CLI引数の代替) |

## 3. 水平スケール(重要)

レート制限と累犯検知は**クライアント単位のカウンタ**。ロードバランサ配下でN台の
ゲートウェイが各自のメモリだけを見ると、攻撃者は実質 N倍 の上限を得てしまう。
`TORII_REDIS_URL` を設定すると状態がRedisに集約され、**フリート全体で上限が効く**。

```
TORII_SECRET=<stable>  TORII_REDIS_URL=redis://redis:6379/0 \
  python3 -m toriigate.proxy --origin http://app:3000
```

`docker compose up --scale gateway=3` で複数ワーカーでも上限が保たれることを確認できる。
(`toriigate/state.py` の `StateStore` 抽象。`MemoryStore`＝既定、`RedisStore`＝共有。)

## 4. TLS終端 / プロキシ配下の設定(なりすまし防止)

`X-Forwarded-For` / `X-Real-IP` はクライアントが偽装できる。**前段のLB/プロキシを
明示的に信頼リストに入れたときだけ**これらを信用する。空なら常にソケットのpeer IPを使う。

```yaml
# policy.yaml
trusted_proxies: ["10.0.0.0/8"]   # LB/TLS終端の送信元CIDRのみ
```

これを設定しないと、`X-Real-IP` 偽装で検証済みクローラーになりすませてしまう
(セキュリティ評価 C-1)。逆に、標準的な nginx 等を前段に置くのにこれを設定しないと、
全ユーザーがプロキシIPに収束してレート制限に巻き込まれる(F-5)。**前段がある本番では必須。**

## 5. 監視(Prometheus)

`/_torii/metrics` を Prometheus でスクレイプ。

```
toriigate_requests_total{category="ai_training_crawler",action="block"}  N
toriigate_requests_total{category="human",action="allow"}               N
toriigate_decision_latency_seconds_bucket{le="0.001"}                    N
toriigate_uptime_seconds                                                 N
```

推奨アラート例:
- ブロック率の急騰(新種の攻撃、または誤検知の兆候)
- `decision_latency` のSLO逸脱(過負荷)
- allow に対する human 比率の急落(ボット波)

ヘルスチェック:`/_torii/healthz`(liveness)・`/_torii/readyz`(readiness)。

`admin_token` を設定すると `/_torii/stats`・`/dashboard`・`/metrics` に認証が必要になる
(ヘッダ `X-Torii-Admin-Token` または `?token=`)。本番では設定すること(C-7)。

## 6. 脅威フィード(IPレンジ)の自動更新 — 運用必須

なりすまし検知は公開IPレンジの鮮度が命。同梱シードはスナップショットにすぎず、
古いままだと**正規のGooglebot等を誤ってSPOOF判定=遮断**しかねない(F-1)。
日次で更新すること。

```
# cron / sidecar で日次実行
python3 -m toriigate.threatfeed --out /etc/toriigate/ranges.json
```

起動時に読み込む:

```python
from toriigate import netranges
netranges.load_ranges("/etc/toriigate/ranges.json")
```

フェッチ失敗や空応答のソースは**前回値を保持**し、決してレンジを空にしない。
不正なCIDRは検証で弾く。

## 7. 本番チェックリスト

- [ ] `TORII_SECRET` を安定値で設定した
- [ ] 複数ワーカーなら `TORII_REDIS_URL` を設定した
- [ ] 前段プロキシがあるなら `trusted_proxies` を設定した
- [ ] `admin_token` を設定し、管理エンドポイントを保護した
- [ ] `threatfeed` を日次cronに登録した
- [ ] `/_torii/metrics` を監視に接続し、ブロック率・レイテンシにアラートを張った
- [ ] `mode: monitor` でシャドー運用し、誤検知率を実トラフィックで計測してから `enforce` に切替えた
- [ ] ポリシーの `challenge.difficulty` / レート閾値 / TTL を自社トラフィックに合わせて調整した

> シャドー運用(`mode: monitor`)は本番投入前に**必ず**行うこと。実トラフィックでの
> 誤検知率を測らずに `enforce` にすると、正規ユーザーやSEOクローラーを弾く事故になる。
