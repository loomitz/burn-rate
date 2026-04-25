from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("budget", "0013_category_budget_behavior_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="recurringexpense",
            name="auto_charge",
            field=models.BooleanField(default=False),
        ),
    ]
