from django.db import migrations


def trim_virtual_reports_to_50(apps, schema_editor):
    Establishment = apps.get_model('inspections', 'Establishment')
    extra_license_numbers = [f'V-LIC-{1000 + i}' for i in range(51, 101)]
    Establishment.objects.filter(license_no__in=extra_license_numbers).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('inspections', '0007_seed_virtual_evaluation_reports'),
    ]

    operations = [
        migrations.RunPython(trim_virtual_reports_to_50, migrations.RunPython.noop),
    ]
