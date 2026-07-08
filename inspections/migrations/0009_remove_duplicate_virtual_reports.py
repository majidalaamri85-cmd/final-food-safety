from django.db import migrations


def remove_duplicate_virtual_reports(apps, schema_editor):
    Establishment = apps.get_model('inspections', 'Establishment')
    Evaluation = apps.get_model('inspections', 'Evaluation')

    virtual_establishments = Establishment.objects.filter(license_no__startswith='V-LIC-').order_by('id')
    for establishment in virtual_establishments:
        evaluation_ids = list(
            Evaluation.objects.filter(establishment=establishment)
            .order_by('id')
            .values_list('id', flat=True)
        )
        if len(evaluation_ids) > 1:
            Evaluation.objects.filter(id__in=evaluation_ids[1:]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('inspections', '0008_trim_virtual_reports_to_50'),
    ]

    operations = [
        migrations.RunPython(remove_duplicate_virtual_reports, migrations.RunPython.noop),
    ]
