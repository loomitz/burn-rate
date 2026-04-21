from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("budget", "0007_invitation"),
    ]

    operations = [
        migrations.AlterField(
            model_name="invitation",
            name="display_name",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AlterField(
            model_name="invitation",
            name="full_name",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
    ]
