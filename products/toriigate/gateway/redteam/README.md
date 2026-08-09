# ToriiGate レッドチーム評価ハーネス

セキュリティ製品の品質は「悪を止められるか(検知)」と「善を通せるか(誤検知)」の
両方で測る。このハーネスは両方を同じ土俵で採点し、再現可能な数値を出す。

```bash
cd gateway
python3 -m redteam.run_assessment --pow \
    --json assessment.json --md metrics.md
```

## 構成

| ファイル | 役割 |
|---|---|
| `attacks.py` | 10種の敵対的トラフィック生成器(UA偽装/IPローテーション/Perplexity型ステルス切替/トラップ回避 等)。各シナリオは「正しいゲートウェイなら止めるべきか」を宣言する |
| `legit.py` | 誤検知スイート。人間・Googlebot・Bingbot・AI検索・AIユーザーエージェント — **止めてはいけない**トラフィック |
| `run_assessment.py` | ライブのゲートウェイに両方を流し、検知率・誤検知率・PoWコストを採点してJSON/MDを出力 |

## 評価の3層(このハーネスがカバーするのは②③)

1. 機能正しさ(単体) → `tests/`(pytest 49件)
2. **敵対的/レッドチーム**(悪を止められるか) → 本ハーネス `attacks.py`
3. **誤検知**(善を通せるか) → 本ハーネス `legit.py`
4. コード自体の安全性(製品が悪用されないか) → 独立監査 + `/security-review`

結果の解釈と推奨は [`../../docs/security-assessment.md`](../../docs/security-assessment.md) にまとめている。

> 注：`run_assessment.py` はエンジンをインプロセスで駆動して多数のベクトルを高速・
> 決定的に評価する。ソケット越しのE2E経路は `tests/test_proxy_e2e.py` で別途検証済み。
