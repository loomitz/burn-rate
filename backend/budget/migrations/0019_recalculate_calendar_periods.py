from calendar import monthrange
from datetime import date

from django.db import migrations


def _month_bounds(value):
    return date(value.year, value.month, 1), date(value.year, value.month, monthrange(value.year, value.month)[1])


def recalc(apps, schema_editor):
    CategoryBudgetChange = apps.get_model("budget", "CategoryBudgetChange")
    BudgetAllocation = apps.get_model("budget", "BudgetAllocation")
    CategoryOverspendRecord = apps.get_model("budget", "CategoryOverspendRecord")
    ExpectedChargeDismissal = apps.get_model("budget", "ExpectedChargeDismissal")

    # D8: re-anclar cambios de presupuesto al mes calendario de su effective_date.
    for change in CategoryBudgetChange.objects.all().iterator():
        start, end = _month_bounds(change.effective_date)
        if change.period_start != start or change.period_end != end:
            change.period_start = start
            change.period_end = end
            change.save(update_fields=["period_start", "period_end"])

    # D8: borrar allocations y overspend records; se regeneran lazy con la matematica nueva.
    BudgetAllocation.objects.all().delete()
    CategoryOverspendRecord.objects.all().delete()

    # D2: re-anclar dismissals al dia 1 del mes calendario; dedupe contra el unique
    # (source_type, source_id, period_start) conservando el mas viejo. Dos pasadas para
    # que un re-anclaje nunca choque con una fila que ya ocupa la clave destino.
    keepers = {}
    for dismissal in ExpectedChargeDismissal.objects.all().order_by("id"):
        start, _ = _month_bounds(dismissal.period_start)
        key = (dismissal.source_type, dismissal.source_id, start)
        if key in keepers:
            dismissal.delete()
        else:
            keepers[key] = dismissal
    for (_, _, start), dismissal in keepers.items():
        if dismissal.period_start != start:
            dismissal.period_start = start
            dismissal.save(update_fields=["period_start"])


class Migration(migrations.Migration):

    dependencies = [
        ("budget", "0018_remove_appsettings_cutoff_day"),
    ]

    operations = [
        migrations.RunPython(recalc, migrations.RunPython.noop),
    ]
