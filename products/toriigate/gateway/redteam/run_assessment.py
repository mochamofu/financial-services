#!/usr/bin/env python3
"""Run the adversarial + false-positive assessment against a live gateway
and emit results as JSON (stdout) plus a markdown metrics fragment.

    python3 -m redteam.run_assessment            # default policy
    python3 -m redteam.run_assessment --json out.json --md metrics.md

Each scenario runs against a FRESH gateway so a technique is scored in
isolation (its own within-scenario volume still accumulates, which is
the point for the distributed/high-volume cases).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time

from toriigate.core import RequestContext
from toriigate.engine import Gateway
from toriigate.policy import Policy
from toriigate import challenge as ch

from redteam.attacks import ATTACK_SCENARIOS
from redteam.legit import LEGIT_SCENARIOS

STOPPED_ACTIONS = {"block", "challenge", "throttle", "tarpit", "monetize"}


def _run_scenario(scn, host="example.jp"):
    gw = Gateway(policy=Policy(), secret=b"assessment")
    rows = []
    for label, headers, ip, path in scn.traffic():
        h = dict(headers)
        h.setdefault("host", host)
        ctx = RequestContext(method="GET", path=path, client_ip=ip,
                             headers=h)
        d = gw.evaluate(ctx)
        rows.append({
            "label": label, "ip": ip, "path": path,
            "category": d.verdict.category.value,
            "action": d.action.value,
            "stopped": d.action.value in STOPPED_ACTIONS,
            "score": d.verdict.score,
        })
    return rows


def assess_attacks():
    out = []
    for scn in ATTACK_SCENARIOS:
        rows = _run_scenario(scn)
        stopped = sum(r["stopped"] for r in rows)
        total = len(rows)
        out.append({
            "key": scn.key, "title": scn.title, "note": scn.note,
            "total": total, "stopped": stopped,
            "detection_rate": round(stopped / total, 3) if total else 0.0,
            "sample_actions": sorted({r["action"] for r in rows}),
            "sample_categories": sorted({r["category"] for r in rows}),
        })
    return out


def assess_false_positives():
    out = []
    for scn in LEGIT_SCENARIOS:
        rows = _run_scenario(scn)
        wrongly = sum(r["stopped"] for r in rows)
        total = len(rows)
        out.append({
            "key": scn.key, "title": scn.title,
            "total": total, "false_positives": wrongly,
            "fp_rate": round(wrongly / total, 3) if total else 0.0,
            "sample_actions": sorted({r["action"] for r in rows}),
            "offenders": [r["label"] for r in rows if r["stopped"]],
        })
    return out


def measure_pow_cost(difficulties=(12, 16, 18, 20)):
    """Quantify the proof-of-work economics: iterations + wall time to
    solve at each difficulty. This is what a scraper pays per challenge."""
    out = []
    for d in difficulties:
        token = ch.make_challenge_token(b"assessment", "203.0.113.5", d)
        t0 = time.perf_counter()
        # Count iterations by re-implementing the inner loop with a counter.
        nonce = 0
        while True:
            digest = hashlib.sha256(f"{token}:{nonce}".encode()).digest()
            if ch._leading_zero_bits(digest) >= d:
                break
            nonce += 1
            if nonce > 20_000_000:
                break
        ms = (time.perf_counter() - t0) * 1000
        out.append({"difficulty": d, "iterations": nonce,
                    "solve_ms": round(ms, 1)})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="write full results JSON here")
    ap.add_argument("--md", help="write markdown metrics fragment here")
    ap.add_argument("--pow", action="store_true",
                    help="include proof-of-work cost measurement (slow)")
    args = ap.parse_args(argv)

    attacks = assess_attacks()
    fps = assess_false_positives()
    pow_cost = measure_pow_cost() if args.pow else []

    # Aggregate: separate "careless/known" from the sophisticated mimics.
    sophisticated = {"full_mimic_1ip", "distributed_mimic", "honeypot_avoider"}
    careless = [a for a in attacks if a["key"] not in sophisticated]
    soph = [a for a in attacks if a["key"] in sophisticated]

    def avg(rows, field):
        return round(sum(r[field] for r in rows) / len(rows), 3) if rows else 0

    summary = {
        "attack_scenarios": len(attacks),
        "detection_careless_avg": avg(careless, "detection_rate"),
        "detection_sophisticated_avg": avg(soph, "detection_rate"),
        "fp_scenarios": len(fps),
        "fp_rate_avg": avg(fps, "fp_rate"),
        "fp_total": sum(f["false_positives"] for f in fps),
    }

    results = {"summary": summary, "attacks": attacks,
               "false_positives": fps, "pow_cost": pow_cost}

    print(json.dumps(results, ensure_ascii=False, indent=2))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(results, fh, ensure_ascii=False, indent=2)

    if args.md:
        with open(args.md, "w", encoding="utf-8") as fh:
            fh.write(_markdown(results))
    return results


def _markdown(r):
    L = ["### 攻撃シナリオ別 検知率\n",
         "| シナリオ | 件数 | 検知 | 検知率 | 主なアクション | 備考 |",
         "|---|---|---|---|---|---|"]
    for a in r["attacks"]:
        L.append(f"| {a['title']} | {a['total']} | {a['stopped']} | "
                 f"**{a['detection_rate']*100:.0f}%** | "
                 f"{', '.join(a['sample_actions'])} | {a['note']} |")
    L += ["\n### 誤検知(False Positive)スイート\n",
          "| 正規トラフィック | 件数 | 誤遮断 | 誤検知率 | アクション |",
          "|---|---|---|---|---|"]
    for f in r["false_positives"]:
        L.append(f"| {f['title']} | {f['total']} | {f['false_positives']} | "
                 f"**{f['fp_rate']*100:.0f}%** | "
                 f"{', '.join(f['sample_actions'])} |")
    if r["pow_cost"]:
        L += ["\n### Proof-of-Work コスト(1チャレンジあたり)\n",
              "| 難易度(先頭0ビット) | 反復回数 | 解決時間 |",
              "|---|---|---|"]
        for p in r["pow_cost"]:
            L.append(f"| {p['difficulty']} | {p['iterations']:,} | "
                     f"{p['solve_ms']} ms |")
    s = r["summary"]
    L += ["\n### サマリ\n",
          f"- 既知型/careless攻撃の平均検知率: **{s['detection_careless_avg']*100:.0f}%**",
          f"- 高度な偽装(完全ブラウザ偽装・分散)の平均検知率: **{s['detection_sophisticated_avg']*100:.0f}%**",
          f"- 誤検知率(正規トラフィック): **{s['fp_rate_avg']*100:.0f}%** "
          f"(誤遮断 {s['fp_total']} 件)"]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
