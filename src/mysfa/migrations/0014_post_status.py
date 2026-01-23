from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mysfa", "0013_postlike_changerequest_trial_session_id_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="status",
            field=models.CharField(
                choices=[
                    ("NEGOTIATING", "交渉中"),
                    ("ADOPTED", "採用"),
                    ("REJECTED", "不採用"),
                    ("USING", "使用中"),
                ],
                db_index=True,
                default="NEGOTIATING",
                max_length=20,
            ),
        ),
    ]
