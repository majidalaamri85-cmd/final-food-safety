from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inspections', '0011_evaluationitem_corrective_action'),
    ]

    operations = [
        migrations.AddField(
            model_name='establishment',
            name='contact_email',
            field=models.EmailField(blank=True, max_length=254, verbose_name='البريد الإلكتروني'),
        ),
    ]
