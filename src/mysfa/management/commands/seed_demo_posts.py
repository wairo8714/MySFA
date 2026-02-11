from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from mysfa.models import Group, GroupMembership, IndustryMaster, Post, ProductMaster


@dataclass(frozen=True)
class SeedRow:
    custom_user_id: str
    created_at: str  # "YYYY-MM-DD HH:MM"
    status_label_ja: str
    product_code: str
    product_name: str
    industry_name: str
    contents: str


PRESET_ROWS: list[SeedRow] = [
    SeedRow(
        custom_user_id="dammy001",
        created_at="2026-01-01 09:05",
        status_label_ja="交渉中",
        product_code="1023",
        product_name="冷凍ほうれん草カット",
        industry_name="外食(チェーン)",
        contents="パスタ具材で提案。時短と歩留まりを評価、テスト調理予定。",
    ),
    SeedRow(
        custom_user_id="dammy002",
        created_at="2026-01-01 09:12",
        status_label_ja="採用",
        product_code="2451",
        product_name="だし醤油(濃縮)",
        industry_name="小売",
        contents="鍋・煮物向けに採用。売場訴求は「時短だし」で展開。",
    ),
    SeedRow(
        custom_user_id="dammy001",
        created_at="2026-01-01 09:26",
        status_label_ja="使用中",
        product_code="5188",
        product_name="冷凍唐揚げ",
        industry_name="コンビニ",
        contents="弁当で使用中。食感評価良、増産可否を確認中。",
    ),
    SeedRow(
        custom_user_id="dammy002",
        created_at="2026-01-01 09:41",
        status_label_ja="不採用",
        product_code="6095",
        product_name="骨取りサバ切り身",
        industry_name="外食(個店)",
        contents="仕入れ価格が合わず不採用。小サイズ規格で再提案。",
    ),
    SeedRow(
        custom_user_id="dammy001",
        created_at="2026-01-01 10:03",
        status_label_ja="交渉中",
        product_code="1048",
        product_name="冷凍ブロッコリー小房",
        industry_name="外食(惣菜・弁当)",
        contents="弁当の彩り用途で提案。自然解凍可否を確認中。",
    ),
    SeedRow(
        custom_user_id="dammy002",
        created_at="2026-01-01 10:18",
        status_label_ja="採用",
        product_code="6402",
        product_name="ドリップコーヒー(個包装)",
        industry_name="宿泊・レジャー",
        contents="客室用に採用。小ロット対応が決め手、納品日調整中。",
    ),
    SeedRow(
        custom_user_id="dammy001",
        created_at="2026-01-01 10:33",
        status_label_ja="交渉中",
        product_code="2934",
        product_name="冷凍ダイス玉ねぎ",
        industry_name="食品メーカー",
        contents="新商品ソース具材で提案。粒度指定あり、試作へ。",
    ),
    SeedRow(
        custom_user_id="dammy002",
        created_at="2026-01-01 10:47",
        status_label_ja="使用中",
        product_code="1209",
        product_name="無糖ヨーグルト(業務用)",
        industry_name="パティスリー",
        contents="ムース原料で使用中。酸味が安定、定期便を検討。",
    ),
    SeedRow(
        custom_user_id="dammy001",
        created_at="2026-01-01 11:02",
        status_label_ja="不採用",
        product_code="7742",
        product_name="冷凍グラタン(個食)",
        industry_name="EC",
        contents="送料込み価格が合わず不採用。セット組みで再打診。",
    ),
    SeedRow(
        custom_user_id="dammy002",
        created_at="2026-01-01 11:18",
        status_label_ja="交渉中",
        product_code="2680",
        product_name="冷凍シュレッドチーズ",
        industry_name="ベーカリー",
        contents="惣菜パン用途で提案。焼成後の伸びを確認予定。",
    ),
]

DEFAULT_INDUSTRY_NAMES: list[str] = [
    "EC",
    "コンビニ",
    "パティスリー",
    "ベーカリー",
    "公共施設",
    "外食(チェーン)",
    "外食(個店)",
    "外食(惣菜・弁当)",
    "宿泊・レジャー",
    "小売",
    "量販店",
    "食品メーカー",
    "食品製造",
]

# 商品は「現行マスタ」から、投稿生成に使う分だけピックアップ（20件用）
DEFAULT_PRODUCTS: list[tuple[str, str]] = [
    ("1023", "冷凍ほうれん草カット"),
    ("1048", "冷凍ブロッコリー小房"),
    ("1076", "冷凍ミックスベジタブル"),
    ("1124", "冷凍カットねぎ"),
    ("1183", "冷凍コーン粒"),
    ("1209", "無糖ヨーグルト(業務用)"),
    ("1297", "冷凍枝豆むき身"),
    ("1335", "冷凍里芋ホール"),
    ("1412", "冷凍かぼちゃダイス"),
    ("1520", "冷凍にんじん千切り"),
    ("1634", "冷凍きのこミックス"),
    ("1715", "冷凍ピーマンスライス"),
    ("1826", "冷凍キャベツカット"),
    ("1938", "冷凍小松菜カット"),
    ("2057", "冷凍バジルペースト"),
    ("2149", "冷凍いちごホール"),
    ("2231", "冷凍マンゴーダイス"),
    ("2364", "冷凍ブルーベリー"),
    ("2451", "だし醤油(濃縮)"),
    ("2680", "冷凍シュレッドチーズ"),
]


JA_STATUS_TO_CODE = {
    "交渉中": Post.Status.NEGOTIATING,
    "採用": Post.Status.ADOPTED,
    "不採用": Post.Status.REJECTED,
    "使用中": Post.Status.USING,
}


def _parse_created_at(value: str) -> datetime:
    dt = datetime.strptime(value, "%Y-%m-%d %H:%M")
    if settings.USE_TZ:
        tz = timezone.get_current_timezone()
        if timezone.is_naive(dt):
            return timezone.make_aware(dt, tz)
        return dt
    # MySQL backend does not support aware datetimes when USE_TZ=False
    return dt.replace(tzinfo=None)


def _fmt_created_at(dt: datetime) -> str:
    if settings.USE_TZ:
        return timezone.localtime(dt).strftime("%Y-%m-%d %H:%M")
    return dt.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M")


def _make_contents(*, status_ja: str, product_name: str, industry_name: str) -> str:
    # Post.contents は max_length=100 なので、少し文字数を稼ぎつつ100以内に収める
    if status_ja == "交渉中":
        return (
            f"導入条件の再確認。{industry_name}向けに提案中。"
            f"{product_name}の試作とリードタイム確認、段取り中。"
        )
    if status_ja == "採用":
        return (
            f"採用決定。{industry_name}で前進。"
            f"{product_name}は初回納品日と発注単位のすり合わせ中。"
        )
    if status_ja == "使用中":
        return (
            f"使用中。{industry_name}で運用開始。"
            f"{product_name}は品質安定、欠品リスクの確認継続。"
        )
    if status_ja == "不採用":
        return (
            f"不採用判断。{industry_name}では条件未達。"
            f"{product_name}は規格と価格を見直して再提案予定。"
        )
    return f"{industry_name}向けの検討。{product_name}の条件整理中。"


def _truncate_100(s: str) -> str:
    s = (s or "").strip()
    if len(s) <= 100:
        return s
    return s[:100]


def build_rows(*, count: int) -> list[SeedRow]:
    """
    Return SeedRow list of length=count.

    - first: PRESET_ROWS (your copied examples)
    - then: auto-generated rows using DEFAULT_PRODUCTS / DEFAULT_INDUSTRY_NAMES
    """
    count = max(0, int(count))
    if count <= len(PRESET_ROWS):
        return PRESET_ROWS[:count]

    rows: list[SeedRow] = list(PRESET_ROWS)

    # start from last preset + 7 minutes (same cadence as examples)
    last_dt = _parse_created_at(PRESET_ROWS[-1].created_at)
    dt = last_dt + timedelta(minutes=7)

    users = ["dammy001", "dammy002"]
    statuses = ["交渉中", "採用", "使用中", "不採用"]

    # Make sure we don't reuse product_code too early (avoid duplicates)
    used_codes = {r.product_code for r in PRESET_ROWS}
    products = [(c, n) for (c, n) in DEFAULT_PRODUCTS if c not in used_codes]
    if not products:
        products = DEFAULT_PRODUCTS[:]

    idx = 0
    while len(rows) < count:
        user_id = users[idx % len(users)]
        status_ja = statuses[idx % len(statuses)]
        product_code, product_name = products[idx % len(products)]
        industry_name = DEFAULT_INDUSTRY_NAMES[idx % len(DEFAULT_INDUSTRY_NAMES)]

        rows.append(
            SeedRow(
                custom_user_id=user_id,
                created_at=_fmt_created_at(dt),
                status_label_ja=status_ja,
                product_code=product_code,
                product_name=product_name,
                industry_name=industry_name,
                contents=_truncate_100(
                    _make_contents(
                        status_ja=status_ja,
                        product_name=product_name,
                        industry_name=industry_name,
                    )
                ),
            )
        )

        dt = dt + timedelta(minutes=7)
        idx += 1

    return rows


class Command(BaseCommand):
    help = "Seed demo posts into a group using existing Product/Industry masters."

    def add_arguments(self, parser):
        parser.add_argument(
            "--group",
            default="72014332",
            help="Target group custom_id (default: 72014332)",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=20,
            help="Number of posts to create (default: 20)",
        )
        parser.add_argument(
            "--create-missing-masters",
            action="store_true",
            help="Create missing ProductMaster/IndustryMaster in the target group.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do not write; only show what would be created.",
        )

    def handle(self, *args, **options):
        group_custom_id = str(options["group"] or "72014332")
        count = int(options["count"] or 20)
        create_missing = bool(options["create_missing_masters"])
        dry_run = bool(options["dry_run"])

        group = Group.objects.filter(
            custom_id=group_custom_id,
            is_active=True,
        ).first()
        if not group:
            raise SystemExit(
                f"Group not found or inactive: custom_id={group_custom_id}"
            )

        rows = build_rows(count=count)

        # Prepare masters lookup
        # (include inactive too; demo seeding only cares about existence)
        products = {
            p.product_code: p for p in ProductMaster.objects.filter(group=group)
        }
        industries = {i.name: i for i in IndustryMaster.objects.filter(group=group)}

        User = get_user_model()

        created = 0
        skipped = 0

        with transaction.atomic():
            if create_missing and not dry_run:
                for r in rows:
                    if r.product_code not in products:
                        p, _ = ProductMaster.objects.get_or_create(
                            group=group,
                            product_code=r.product_code,
                            defaults={
                                "name": r.product_name,
                                "is_active": True,
                            },
                        )
                        products[p.product_code] = p
                    if r.industry_name not in industries:
                        i, _ = IndustryMaster.objects.get_or_create(
                            group=group,
                            name=r.industry_name,
                            defaults={"is_active": True},
                        )
                        industries[i.name] = i

            missing_products = sorted(
                {r.product_code for r in rows if r.product_code not in products}
            )
            missing_industries = sorted(
                {r.industry_name for r in rows if r.industry_name not in industries}
            )
            if missing_products or missing_industries:
                msg = []
                if missing_products:
                    msg.append(
                        f"Missing ProductMaster.product_code: {missing_products} "
                        "(use --create-missing-masters to auto-create)"
                    )
                if missing_industries:
                    msg.append(
                        f"Missing IndustryMaster.name: {missing_industries} "
                        "(use --create-missing-masters to auto-create)"
                    )
                raise SystemExit("\n".join(msg))

            for r in rows:
                status = JA_STATUS_TO_CODE.get(r.status_label_ja)
                if not status:
                    raise SystemExit(f"Unknown status label: {r.status_label_ja}")

                u, _ = User.objects.get_or_create(
                    custom_user_id=r.custom_user_id,
                    defaults={
                        "username": r.custom_user_id,
                        "email": f"{r.custom_user_id}@example.com",
                        "question": "seed",
                        "answer": "seed",
                    },
                )
                # Ensure auth-group relation + membership exists
                u.groups.add(group)
                GroupMembership.objects.get_or_create(
                    group=group,
                    user=u,
                    defaults={"role": GroupMembership.Role.MEMBER, "is_active": True},
                )

                created_at = _parse_created_at(r.created_at)

                # Idempotency: skip if same record already exists
                exists = Post.objects.filter(
                    group=group,
                    user=u,
                    created_at=created_at,
                    contents=r.contents,
                ).exists()
                if exists:
                    skipped += 1
                    continue

                if dry_run:
                    created += 1
                    continue

                post = Post.objects.create(
                    group=group,
                    user=u,
                    status=status,
                    product=products[r.product_code],
                    industry=industries[r.industry_name],
                    contents=r.contents,
                )
                # Override created_at to requested timestamp
                Post.objects.filter(pk=post.pk).update(created_at=created_at)
                created += 1

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                (
                    f"seed_demo_posts: group={group.custom_id} "
                    f"created={created} skipped={skipped} dry_run={dry_run} "
                    f"count={len(rows)}"
                )
            )
        )
