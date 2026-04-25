from django.db import migrations, models


def backfill_establishment_numbers(apps, schema_editor):
    Establishment = apps.get_model('inspections', 'Establishment')
    rows = Establishment.objects.order_by('id').only('id', 'establishment_no')
    current = 1
    for row in rows:
        if row.establishment_no is None:
            row.establishment_no = current
            row.save(update_fields=['establishment_no'])
            current += 1
        else:
            current = max(current, row.establishment_no + 1)


class Migration(migrations.Migration):

    dependencies = [
        ('inspections', '0005_establishment_direct_location_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='establishment',
            name='establishment_no',
            field=models.PositiveIntegerField(blank=True, db_index=True, editable=False, null=True, unique=True, verbose_name='رقم المنشأة'),
        ),
        migrations.RunPython(backfill_establishment_numbers, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='establishment',
            name='establishment_no',
            field=models.PositiveIntegerField(db_index=True, editable=False, unique=True, verbose_name='رقم المنشأة'),
        ),
    ]
