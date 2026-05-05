from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("budget", "0014_recurringexpense_auto_charge"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="budget_treatment",
            field=models.CharField(
                choices=[
                    ("budgeted", "Presupuestada"),
                    ("tracking_only", "Fuera de presupuesto"),
                ],
                default="budgeted",
                max_length=24,
            ),
        ),
    ]
