"""Subscription tiers (billing itself lives in the SaaS control plane).

Pricing strategy (see docs/business-plan.md): sit in the vacant band
between CDN-bundled free features and specialist vendors' ~$3,500+/mo
floor. Visibility is free; enforcement is paid.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Plan:
    key: str
    name: str
    monthly_jpy: int
    requests_included: int          # analyzed requests / month
    features: tuple = field(default_factory=tuple)


PLANS = {
    "free": Plan(
        "free", "Free（可視化）", 0, 100_000,
        ("AIボット検知レポート", "ダッシュボード", "robots.txt生成")),
    "starter": Plan(
        "starter", "Starter", 29_800, 3_000_000,
        ("ブロック/チャレンジ/レート制限の実施", "なりすまし検知",
         "メールサポート")),
    "business": Plan(
        "business", "Business", 98_000, 20_000_000,
        ("Web Bot Auth 署名検証", "APIエンドポイント保護ポリシー",
         "監査ログエクスポート", "優先サポート")),
    "enterprise": Plan(
        "enterprise", "Enterprise", 0, 0,   # custom quote
        ("カスタムSLA", "SSO/SAML", "専任サポート",
         "AI事業者ガイドライン対応統制レポート", "クロール課金(402)運用")),
}


def get_plan(key: str) -> Plan:
    return PLANS[key]
