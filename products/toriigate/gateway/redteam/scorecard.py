#!/usr/bin/env python3
"""Evaluation scorecard — measures every gate metric and prints pass/fail
against its threshold, plus which business gate is currently unlocked.

The point is to make "評価" objective and repeatable instead of a matter
of memory: run this, get the numbers, compare to the thresholds agreed in
docs/verification-plan.md, and record the output in the ledger.

    python3 -m redteam.scorecard
    python3 -m redteam.scorecard --json      # machine-readable

Metrics that this harness *cannot* measure are reported explicitly as
UNMEASURED rather than silently omitted — real-traffic validity, load
behavior, and third-party pentest are the gaps that decide sellability,
and hiding them behind green synthetic numbers is the failure mode this
file exists to prevent.
"""

from __future__ import annotations

import argparse
import base64
import json
import random
import statistics
import time
import warnings

from toriigate.core import RequestContext
from toriigate.engine import Gateway
from toriigate.policy import Policy

from redteam import fuzz as fuzzmod
from redteam.attacks import FULL_BROWSER_HEADERS
from redteam.run_assessment import assess_attacks, assess_false_positives

warnings.simplefilter("ignore")

# Tiering is by *evasion mechanism*, not by name. Anything whose traffic is
# a full browser mimic (complete headers, human-like paths, rotating or
# single clean IP) belongs in the sophisticated tier, because that is the
# documented heuristic limit. perplexity_stealth sits here because 8 of its
# 9 requests are exactly that — the undeclared browser-mimic phase after a
# declared crawler gets blocked; only its declared phase is catchable.
SOPHISTICATED = {"full_mimic_1ip", "distributed_mimic", "honeypot_avoider",
                 "perplexity_stealth"}

# Proposed thresholds. Tune these with the customer/context — they are
# starting points, not laws. See docs/verification-plan.md.
THRESHOLDS = {
    "fp_rate": ("誤検知率（正規トラフィック）", 0.0, "<=", "blocker"),
    "detection_known": ("既知型・雑な攻撃の検知率", 0.95, ">=", "blocker"),
    "detection_with_botauth": ("高度偽装（署名必須ポリシー適用時）", 0.95, ">=", "blocker"),
    "fuzz_failures": ("ファジングで漏れた例外", 0, "<=", "blocker"),
    "latency_p95_ms": ("判定オーバーヘッド p95", 5.0, "<=", "warn"),
}


def measure_detection() -> dict:
    attacks = assess_attacks()
    known = [a for a in attacks if a["key"] not in SOPHISTICATED]
    soph = [a for a in attacks if a["key"] in SOPHISTICATED]

    def weighted(rows):
        # Request-weighted, not a mean of scenario rates: a 40-request
        # scenario must not count the same as a 5-request one.
        total = sum(r["total"] for r in rows)
        return round(sum(r["stopped"] for r in rows) / total, 4) if total else 0.0

    def unweighted(rows):
        return (round(sum(r["detection_rate"] for r in rows) / len(rows), 4)
                if rows else 0.0)

    return {
        "detection_known": weighted(known),
        "detection_known_unweighted": unweighted(known),
        "detection_sophisticated_heuristics_only": weighted(soph),
        "per_scenario": {a["key"]: a["detection_rate"] for a in attacks},
    }


def measure_false_positives() -> dict:
    fps = assess_false_positives()
    total = sum(f["total"] for f in fps)
    wrong = sum(f["false_positives"] for f in fps)
    return {
        "fp_rate": round(wrong / total, 5) if total else 0.0,
        "fp_count": wrong,
        "legit_requests": total,
        "offending_scenarios": [f["key"] for f in fps if f["false_positives"]],
    }


def measure_botauth_mitigation() -> dict:
    """The honest counterpart to the 0% heuristic result: does requiring a
    Web Bot Auth signature on a sensitive path stop the same attack?"""
    from toriigate import botauth
    if not botauth.HAVE_ED25519:
        return {"detection_with_botauth": None,
                "note": "cryptography 未インストールのため未測定"}
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey)
    from cryptography.hazmat.primitives.serialization import (
        Encoding, PublicFormat)
    priv = Ed25519PrivateKey.generate()
    pub = base64.b64encode(priv.public_key().public_bytes(
        Encoding.Raw, PublicFormat.Raw)).decode()
    reg = botauth.AgentRegistry()
    reg.register(botauth.RegisteredAgent("sc-key", pub, "Scorecard", "SC"))
    policy = Policy.from_dict({"path_rules": [{"prefix": "/api/",
        "category_actions": {"human": "challenge", "unknown_bot": "block",
                             "scraper": "block", "verified_agent": "allow"}}]})
    gw = Gateway(policy=policy, secret=b"scorecard", agent_registry=reg)

    rng = random.Random(4242)
    stopped = total = 0
    for _ in range(20):
        ip = f"45.{rng.randrange(1,255)}.{rng.randrange(1,255)}.{rng.randrange(1,255)}"
        h = dict(FULL_BROWSER_HEADERS); h["host"] = "example.jp"
        d = gw.evaluate(RequestContext(method="GET", path="/api/data",
                                       client_ip=ip, headers=h))
        total += 1
        stopped += d.action.value not in ("allow", "log_only")

    h = dict(FULL_BROWSER_HEADERS); h["host"] = "example.jp"
    h.update(botauth.sign_request(priv, "sc-key", "GET", "example.jp",
                                  "/api/data"))
    legit = gw.evaluate(RequestContext(method="GET", path="/api/data",
                                       client_ip="45.9.9.9", headers=h))
    return {
        "detection_with_botauth": round(stopped / total, 4) if total else 0.0,
        "verified_agent_passes": legit.action.value == "allow",
    }


def measure_latency(n: int = 3000) -> dict:
    """Gateway decision overhead only — no origin I/O, single process.

    Distinct client IPs per sample so the rate-limit path does not skew
    the measurement toward the (cheaper) throttle branch.
    """
    gw = Gateway(policy=Policy(), secret=b"scorecard")
    rng = random.Random(7)
    samples = []
    uas = [FULL_BROWSER_HEADERS["user-agent"], "GPTBot/1.2", "curl/8.5.0",
           "Mozilla/5.0 (compatible; Googlebot/2.1)"]
    for i in range(n):
        h = dict(FULL_BROWSER_HEADERS)
        h["user-agent"] = uas[i % len(uas)]
        h["host"] = "example.jp"
        ctx = RequestContext(
            method="GET", path="/articles/1",
            client_ip=f"10.{rng.randrange(1,255)}.{rng.randrange(1,255)}."
                      f"{rng.randrange(1,255)}",
            headers=h)
        t0 = time.perf_counter()
        gw.evaluate(ctx)
        samples.append((time.perf_counter() - t0) * 1000)
    samples.sort()
    pct = lambda p: round(samples[min(len(samples) - 1,
                                      int(len(samples) * p))], 4)
    return {
        "latency_samples": n,
        "latency_p50_ms": pct(0.50),
        "latency_p95_ms": pct(0.95),
        "latency_p99_ms": pct(0.99),
        "latency_mean_ms": round(statistics.fmean(samples), 4),
        "throughput_est_rps": int(1000 / statistics.fmean(samples)),
    }


def measure_fuzz(iterations: int = 3000) -> dict:
    failures = []
    for target in fuzzmod.TARGETS:
        failures.extend(fuzzmod.run(target, iterations=iterations, seed=2026))
    return {"fuzz_failures": len(failures),
            "fuzz_iterations_per_target": iterations,
            "fuzz_targets": len(fuzzmod.TARGETS)}


# Things this harness structurally cannot answer.
UNMEASURED = [
    ("実トラフィックでの妥当性", "実顧客のmonitorモード運用（2〜4週）",
     "最大の空白。合成トラフィックでは代替不能"),
    ("本気の回避への耐性", "第三者ペネトレーションテスト",
     "資源を投じた分散偽装は署名必須ポリシー以外では止まらない"),
    ("負荷時の挙動", "負荷試験（同時接続・持続スループット）",
     "本harnessは単一プロセスの判定コストのみ測定"),
    ("運用の実地耐久", "パイロット顧客での連続稼働",
     "メモリ/接続リークは長時間稼働でしか出ない"),
]


def evaluate(metrics: dict) -> list:
    rows = []
    for key, (label, threshold, op, kind) in THRESHOLDS.items():
        value = metrics.get(key)
        if value is None:
            rows.append((label, "—", threshold, "UNMEASURED", kind))
            continue
        passed = value <= threshold if op == "<=" else value >= threshold
        rows.append((label, value, threshold,
                     "PASS" if passed else "FAIL", kind))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(prog="redteam.scorecard")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fuzz-iterations", type=int, default=3000)
    ap.add_argument("--latency-samples", type=int, default=3000)
    args = ap.parse_args(argv)

    metrics = {}
    metrics.update(measure_false_positives())
    metrics.update(measure_detection())
    metrics.update(measure_botauth_mitigation())
    metrics.update(measure_latency(args.latency_samples))
    metrics.update(measure_fuzz(args.fuzz_iterations))

    rows = evaluate(metrics)
    blockers = [r for r in rows if r[3] == "FAIL" and r[4] == "blocker"]

    if args.json:
        print(json.dumps({
            "metrics": metrics,
            "evaluation": [{"metric": r[0], "value": r[1], "threshold": r[2],
                            "result": r[3], "kind": r[4]} for r in rows],
            "blockers": len(blockers),
            "unmeasured": [{"area": a, "how": h, "why": w}
                           for a, h, w in UNMEASURED],
        }, ensure_ascii=False, indent=2))
        return 1 if blockers else 0

    print("=" * 72)
    print("  ⛩️  ToriiGate 評価スコアカード")
    print("=" * 72)
    print(f"  {'指標':<34} {'実測':>10} {'閾値':>8}   判定")
    print("  " + "-" * 68)
    for label, value, threshold, result, kind in rows:
        v = f"{value:.4f}" if isinstance(value, float) else str(value)
        mark = {"PASS": "✅", "FAIL": "❌", "UNMEASURED": "⚠️ "}[result]
        tag = "" if kind == "blocker" else "（警告のみ）"
        print(f"  {label:<34} {v:>10} {threshold:>8}   {mark} {result}{tag}")

    print("\n  参考値（閾値なし・情報として記録する）")
    print(f"    高度偽装（ヒューリスティックのみ）  "
          f"{metrics['detection_sophisticated_heuristics_only']:.2f}"
          f"  ← 原理的限界。署名必須ポリシーで対処する前提")
    print(f"    判定 p50 / p99                     "
          f"{metrics['latency_p50_ms']:.3f}ms / {metrics['latency_p99_ms']:.3f}ms")
    print(f"    単一プロセス処理能力の目安          "
          f"約 {metrics['throughput_est_rps']:,} req/s（判定のみ）")
    print(f"    正規トラフィック検証数              "
          f"{metrics['legit_requests']} 件中 誤遮断 {metrics['fp_count']} 件")

    print("\n  この harness では測れないもの（未検証の空白）")
    for area, how, why in UNMEASURED:
        print(f"    ⬜ {area}")
        print(f"       → {how}")
        print(f"         {why}")

    print("\n" + "=" * 72)
    if blockers:
        print(f"  ❌ ブロッカー {len(blockers)} 件。次の段階に進んではいけない。")
    else:
        print("  ✅ 合成テストの範囲では全ブロッカー通過。")
        print("     ただし上記「未検証の空白」が埋まるまで、")
        print("     『防御できる製品』として有料販売してはいけない。")
    print("  評価の使い方: docs/verification-plan.md の事業ゲート表と突き合わせる")
    print("=" * 72)
    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
