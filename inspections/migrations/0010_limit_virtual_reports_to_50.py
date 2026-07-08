from django.db import migrations


def limit_virtual_reports_to_50(apps, schema_editor):
    Evaluation = apps.get_model('inspections', 'Evaluation')

    virtual_report_ids = list(
        Evaluation.objects.filter(establishment__license_no__startswith='V-LIC-')
        .order_by('-visit_date', '-created_at', '-id')
        .values_list('id', flat=True)
    )
    extra_ids = virtual_report_ids[50:]
    if extra_ids:
        Evaluation.objects.filter(id__in=extra_ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('inspections', '0009_remove_duplicate_virtual_reports'),
    ]

    operations = [
        migrations.RunPython(limit_virtual_reports_to_50, migrations.RunPython.noop),
    ]
