from django.core.management import call_command
from django.db import migrations


def seed_virtual_evaluation_reports(apps, schema_editor):
    call_command('seed_virtual_data', count=100, verbosity=0)


class Migration(migrations.Migration):
    dependencies = [
        ('inspections', '0006_waterfactoryclassification'),
    ]

    operations = [
        migrations.RunPython(seed_virtual_evaluation_reports, migrations.RunPython.noop),
    ]
