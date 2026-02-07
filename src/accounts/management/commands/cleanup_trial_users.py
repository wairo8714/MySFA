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
            help="Delete ALL trial users (dangerous).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do not delete; only show how many would be deleted.",
        )
        parser.add_argument(
            "--prefix",
            default="trial",
            help="custom_user_id prefix treated as trial (default: trial)",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        prefix = str(options["prefix"] or "trial")
        dry_run = bool(options["dry_run"])
        delete_all = bool(options["all"])

        base_q = Q(is_trial=True) | Q(custom_user_id__startswith=prefix)
        qs = User.objects.filter(base_q)

        if not delete_all:
            now = timezone.now()
            # If expires_at is missing, treat as expired (legacy leftovers)
            qs = qs.filter(Q(trial_expires_at__isnull=True) | Q(trial_expires_at__lte=now))

        count = qs.count()
        if dry_run:
            self.stdout.write(self.style.WARNING(f"[dry-run] would delete: {count} trial users"))
            return

        deleted = qs.delete()
        # deleted is (num_deleted, per_model_dict)
        self.stdout.write(self.style.SUCCESS(f"deleted trial users: {count} (details={deleted[1]})"))

