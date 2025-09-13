import random

from django.core.management.base import BaseCommand
from django.db import models

from mysfa.models import Group


class Command(BaseCommand):
    help = "Fix empty custom_id fields for existing groups"

    def handle(self, *args, **options):
        groups_without_custom_id = Group.objects.filter(
            models.Q(custom_id__isnull=True)
            | models.Q(custom_id="")
            | models.Q(custom_id="00000000")
        )

        self.stdout.write(
            f"Found {groups_without_custom_id.count()} groups without custom_id"
        )

        for group in groups_without_custom_id:
            # Generate unique custom_id
            while True:
                new_id = "".join([str(random.randint(0, 9)) for _ in range(8)])
                if not Group.objects.filter(custom_id=new_id).exists():
                    group.custom_id = new_id
                    group.save()
                    self.stdout.write(
                        f'Fixed group "{group.name}" with custom_id: {new_id}'
                    )
                    break

        self.stdout.write(self.style.SUCCESS("Successfully fixed all group custom_ids"))
