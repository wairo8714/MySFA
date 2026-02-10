from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone


class Command(BaseCommand):
    help = "Delete trial users (all or expired)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="すべてのお試しユーザーを削除",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="削除対象を表示",
        )
        parser.add_argument(
            "--prefix",
            default="trial",
            help="IDがtrialから始まるユーザーをデフォルトで指定",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        prefix = str(options["prefix"] or "trial")
        dry_run = bool(options["dry_run"])
        delete_all = bool(options["all"])

        base_q = Q(is_trial=True) | Q(custom_user_id__startswith=prefix)
        qs = User.objects.filter(base_q)

        # 全削除未指定時は、期限切れユーザーのみ削除
        if not delete_all:
            now = timezone.now()
            qs = qs.filter(
                Q(trial_expires_at__isnull=True) | Q(trial_expires_at__lte=now)
            )

        count = qs.count()
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"[dry-run] 削除対象: {count} 件")
            )
            return

        deleted = qs.delete()
        self.stdout.write(
            self.style.SUCCESS(f": {count} 件 (内訳={deleted[1]})")
        )
