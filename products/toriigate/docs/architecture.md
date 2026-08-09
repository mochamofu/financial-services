# ToriiGate アーキテクチャ図

ワークフローの全体像。図は GitHub 上でそのまま描画される。
視覚的にまとまった1枚版は、この内容を図解にしたものを別途参照。

---

## 1. 実行時フロー：リクエストが門をくぐる順序

1リクエストごとに上から順に評価し、どこかで振り分けられたらその場で
ゲートウェイが応答する（原本サーバには届かない）。**この順序自体が防御**で、
たとえばチャレンジ通過証を持つ相手でも罠パスは門2で止まる。

```mermaid
flowchart TD
    C(["クライアント<br/>人間 / ボット / AIエージェント"]) --> G1

    G1{"1. ブロックリスト<br/>運用者が拒否したIP"}
    G1 -->|該当| B1["block 403"]
    G1 -->|通過| G2

    G2{"2. トラップ判定<br/>ハニーポット / 脆弱性プローブ"}
    G2 -->|該当| B2["block 403<br/>＋累犯記録"]
    G2 -->|通過| G3

    G3{"3. 通過証<br/>チャレンジ済み cookie"}
    G3 -->|有効| R1{"レート制限"}
    G3 -->|なし| G4

    G4{"4. 許可リスト<br/>IP / UA"}
    G4 -->|該当| R1
    G4 -->|通過| G5

    G5{"5. Web Bot Auth 署名検証<br/>RFC 9421 / Ed25519"}
    G5 -->|署名が有効| R1
    G5 -->|署名なし / 無効| G6

    G6["6. 多層検知＋ポリシー適用<br/>署名辞書・IPレンジ照合・ヘッダ指紋・挙動"]
    G6 --> A{"アクション決定"}

    A -->|学習クローラー / なりすまし / 悪性| B3["block 403"]
    A -->|スクレイパー / 未知ボット| CH["challenge<br/>Proof-of-Work"]
    A -->|課金対象| PAY["402 Payment Required"]
    A -->|遅延で消耗| TP["tarpit"]
    A -->|正常| R1

    R1 -->|上限内| OK(["原本サーバへ転送 200"])
    R1 -->|上限超過| TH["throttle 429"]

    CH -->|解けたら通過証を発行| C
```

> `mode: monitor` の場合、上記のうち allow 以外はすべて `log_only` に置き換わり、
> **遮断せず記録だけ**を行う。本番投入前に必ずこのモードで誤検知を計測する。

## 2. 検知の層と、その限界

| 層 | 何を捕まえるか | 強度 |
|---|---|---|
| ① トラップ | 罠パス・脆弱性探索（robots.txt 無視の証拠） | 決定的 |
| ② 身元 | UA 署名辞書 × 公開IPレンジ照合 → **なりすまし検知** | 強い |
| ③ ヘッダ指紋 | ブラウザを名乗るのに標準ヘッダを欠く（実通信時のみ有効） | 中 |
| ④ 挙動 | 短時間の大量アクセス・累犯IP記憶（Redis でフリート共有） | 中 |
| ⑤ 署名検証 | Web Bot Auth。推測でなく証明。**正規を通し詐称を弾く** | 決定的 |

**正直な限界**：完全なブラウザ偽装＋IPを毎回変える分散スクレイパーは ①〜④ では
**検知率0%**（内部レッドチームで実測）。これは識別情報ベースのボット検知に共通する
原理的限界。重要パスで **⑤ を必須**にすると同じ攻撃が **20/20 遮断**に反転する。
詳細は [security-assessment.md](./security-assessment.md)。

## 3. 構成とデプロイ

```mermaid
flowchart LR
    subgraph EDGE["エッジ（どちらか一方を選ぶ）"]
        PX["リバースプロキシ<br/>既存構成の前段に1コマンド"]
        MW["ASGI ミドルウェア<br/>FastAPI / Starlette / Django に1行"]
    end

    subgraph CORE["ゲートウェイ本体"]
        EN["engine<br/>判定の統合"]
        SC["scoring<br/>多層検知"]
        PO["policy<br/>テナント別ポリシー"]
        CHm["challenge<br/>Proof-of-Work"]
        BA["botauth<br/>署名検証"]
    end

    subgraph STATE["状態（水平スケール）"]
        MEM["MemoryStore<br/>単一プロセス既定"]
        RD[("Redis<br/>フリート共有")]
    end

    subgraph OBS["可観測性"]
        DASH["ダッシュボード"]
        MET["Prometheus メトリクス"]
        LOG["構造化ログ JSON"]
        USE["従量メータリング"]
    end

    FEED["脅威フィード更新<br/>公開IPレンジを日次取得"] -.-> SC
    PX --> EN
    MW --> EN
    EN --> SC & PO & CHm & BA
    SC --> MEM & RD
    EN --> DASH & MET & LOG & USE
    EN --> ORG(["原本サーバ / アプリ"])
```

環境変数：`TORII_SECRET`（本番必須）、`TORII_REDIS_URL`（複数ワーカー時）、
`TORII_LOG=json`。詳細は [deployment.md](./deployment.md)。

## 4. 品質テストと事業投入の流れ

「守れる」と約束する前に現状を見せる。この順序が誤認販売を防ぎ、
同時に実トラフィックのデータを集める。

```mermaid
flowchart TD
    subgraph TEST["品質テスト（testkit/）"]
        T1["A. 誤検知<br/>実ブラウザ・実機 → 全て allow か"]
        T2["B. 検知<br/>スクレイパー・なりすまし・プローブ"]
        T3["C. AIエージェント実物<br/>Codex / Z.ai の挙動を記録"]
        T4["D. 運用面<br/>監視・ヘルスチェック"]
        T1 --> T2 --> T3 --> T4
    end

    subgraph SELL["顧客への入り方"]
        S1["STEP1 ログ診断<br/>無料・デプロイ不要・防御を約束しない"]
        S2["STEP2 monitor モード<br/>遮断せず誤検知率を実測（2〜4週間）"]
        S3["STEP3 enforce<br/>合意の上で遮断を有効化 → 有料"]
        S1 --> S2 --> S3
    end

    subgraph CH2["チャネルの段階"]
        C1["0→10社<br/>創業者直販・設定代行込み"]
        C2["10→100社<br/>MSP再販＋補助金"]
        C3["100社→<br/>ディストリビューター"]
        C1 --> C2 --> C3
    end

    T4 --> S1
    S3 --> C1
```

テスト手順の詳細は [../testkit/README.md](../testkit/README.md)、
合否記録は [../testkit/CHECKLIST.md](../testkit/CHECKLIST.md)。
事業側の詳細は [gtm-japan.md](./gtm-japan.md)。

## 5. 現在地

**できている**：多層検知エンジン／7種のアクション／Web Bot Auth 署名検証／
2つの導入形態／Docker・Redis 水平スケール／監視・構造化ログ・ヘルスチェック／
脅威フィード自動更新／レッドチーム評価＋独立コード監査（Critical 修正済）／
ログ診断ツール／テストキット／従量メータリング／市場調査・事業計画・GTM・信頼資料。

**まだ無い**：課金の実配線／マルチテナント管理・セルフサーブ／TLS・JA4 指紋と挙動ML／
ISMS・SOC2／負荷試験・第三者ペンテスト／そして最大の空白である
**実トラフィックでの検証**（現在の検知数値はすべて合成トラフィックによる内部実測）。

→ 位置づけは「**資金調達・パイロットに耐えるMVP**」であり
「**販売できる製品**」ではない。残作業は [product-roadmap.md](./product-roadmap.md)。
