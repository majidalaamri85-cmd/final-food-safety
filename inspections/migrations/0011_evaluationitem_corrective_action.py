from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inspections', '0010_remove_establishment_has_commercial_register_doc_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='evaluationitem',
            name='corrective_action',
            field=models.TextField(blank=True, verbose_name='الإجراء التصحيحي'),
        ),
    ]