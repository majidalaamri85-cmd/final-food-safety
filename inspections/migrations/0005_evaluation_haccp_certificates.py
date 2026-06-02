from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inspections', '0004_repair_evaluation_classifications'),
    ]

    operations = [
        migrations.AddField(
            model_name='evaluation',
            name='haccp_certificate',
            field=models.CharField(blank=True, max_length=500, verbose_name='الهاسب'),
        ),
        migrations.AddField(
            model_name='evaluation',
            name='iso_22000_certificate',
            field=models.CharField(blank=True, max_length=500, verbose_name='آيزو 22000'),
        ),
        migrations.AddField(
            model_name='evaluation',
            name='other_quality_certificate',
            field=models.CharField(blank=True, max_length=500, verbose_name='شهادات أنظمة جودة أخرى'),
        ),
    ]
