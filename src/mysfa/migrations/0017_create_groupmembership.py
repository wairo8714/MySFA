import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def forwards(apps, schema_editor):
    Group = apps.get_model("mysfa", "Group")
    GroupMembership = apps.get_model("mysfa", "GroupMembership")

    for group in Group.objects.all():
        for user in group.users.all():
            GroupMembership.objects.get_or_create(
                group_id=group.id,
                user_id=user.id,
                defaults={"role": "MEMBER", "is_active": True},
            )

        if getattr(group, "creator_id", None):
            m, _ = GroupMembership.objects.get_or_create(
                group_id=group.id,
                user_id=group.creator_id,
                defaults={"role": "OWNER", "is_active": True},
            )
            if m.role != "OWNER" or m.is_active is not True:
                m.role = "OWNER"
                m.is_active = True
                m.save(update_fields=["role", "is_active"])


def backwards(apps, schema_editor):
    GroupMembership = apps.get_model("mysfa", "GroupMembership")
    GroupMembership.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("mysfa", "0016_rename_mysfa_postc_post_id_1c2d4a_idx_mysfa_postc_post_id_6bcd6f_idx_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="GroupMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "role",
                    models.CharField(
                        choices=[("OWNER", "オーナー"), ("ADMIN", "管理者"), ("MEMBER", "メンバー")],
                        default="MEMBER",
                        max_length=10,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                (
                    "group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memberships",
                        to="mysfa.group",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="group_memberships",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("group", "user"), name="uq_group_membership_group_user"),
                ],
                "indexes": [
                    models.Index(fields=["group", "role", "is_active"], name="idx_gm_group_role_active"),
                    models.Index(fields=["user", "is_active"], name="idx_gm_user_active"),
                ],
            },
        ),
        migrations.RunPython(forwards, backwards),
    ]
