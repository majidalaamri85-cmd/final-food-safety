from django.db import migrations, models


CERTIFICATE_FIELD_LABELS = {
    'haccp_certificate': '\u0627\u0644\u0647\u0627\u0633\u0628',
    'iso_22000_certificate': '\u0622\u064a\u0632\u0648 22000',
    'other_quality_certificate': (
        '\u0634\u0647\u0627\u062f\u0627\u062a \u0623\u0646\u0638\u0645\u0629 '
        '\u062c\u0648\u062f\u0629 \u0623\u062e\u0631\u0649'
    ),
}


def certificate_field(field_name):
    return models.CharField(
        CERTIFICATE_FIELD_LABELS[field_name],
        blank=True,
        max_length=500,
    )


def get_existing_columns(schema_editor, table_name):
    with schema_editor.connection.cursor() as cursor:
        description = schema_editor.connection.introspection.get_table_description(
            cursor,
            table_name,
        )
    return {column.name for column in description}


def add_certificate_field_if_missing(apps, schema_editor, field_name):
    Evaluation = apps.get_model('inspections', 'Evaluation')
    existing_columns = get_existing_columns(schema_editor, Evaluation._meta.db_table)

    if field_name in existing_columns:
        return

    field = certificate_field(field_name)
    field.set_attributes_from_name(field_name)
    schema_editor.add_field(Evaluation, field)


def remove_certificate_field_if_present(apps, schema_editor, field_name):
    Evaluation = apps.get_model('inspections', 'Evaluation')
    existing_columns = get_existing_columns(schema_editor, Evaluation._meta.db_table)

    if field_name not in existing_columns:
        return

    field = certificate_field(field_name)
    field.set_attributes_from_name(field_name)
    schema_editor.remove_field(Evaluation, field)


def add_haccp_certificate_if_missing(apps, schema_editor):
    add_certificate_field_if_missing(apps, schema_editor, 'haccp_certificate')


def add_iso_22000_certificate_if_missing(apps, schema_editor):
    add_certificate_field_if_missing(apps, schema_editor, 'iso_22000_certificate')


def add_other_quality_certificate_if_missing(apps, schema_editor):
    add_certificate_field_if_missing(apps, schema_editor, 'other_quality_certificate')


def remove_haccp_certificate_if_present(apps, schema_editor):
    remove_certificate_field_if_present(apps, schema_editor, 'haccp_certificate')


def remove_iso_22000_certificate_if_present(apps, schema_editor):
    remove_certificate_field_if_present(apps, schema_editor, 'iso_22000_certificate')


def remove_other_quality_certificate_if_present(apps, schema_editor):
    remove_certificate_field_if_present(apps, schema_editor, 'other_quality_certificate')


class Migration(migrations.Migration):

    dependencies = [
        ('inspections', '0004_repair_evaluation_classifications'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    add_haccp_certificate_if_missing,
                    remove_haccp_certificate_if_present,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='evaluation',
                    name='haccp_certificate',
                    field=certificate_field('haccp_certificate'),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    add_iso_22000_certificate_if_missing,
                    remove_iso_22000_certificate_if_present,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='evaluation',
                    name='iso_22000_certificate',
                    field=certificate_field('iso_22000_certificate'),
                ),
            ],
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    add_other_quality_certificate_if_missing,
                    remove_other_quality_certificate_if_present,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='evaluation',
                    name='other_quality_certificate',
                    field=certificate_field('other_quality_certificate'),
                ),
            ],
        ),
    ]
