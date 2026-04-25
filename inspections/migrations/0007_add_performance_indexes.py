from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inspections', '0006_establishment_establishment_no'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='correctiveactionlog',
            index=models.Index(fields=['status'], name='corrective_status_idx'),
        ),
        migrations.AddIndex(
            model_name='correctiveactionlog',
            index=models.Index(fields=['due_date'], name='corrective_due_idx'),
        ),
        migrations.AddIndex(
            model_name='establishment',
            index=models.Index(fields=['commercial_name'], name='establishment_name_idx'),
        ),
        migrations.AddIndex(
            model_name='establishment',
            index=models.Index(fields=['license_no'], name='establishment_license_idx'),
        ),
        migrations.AddIndex(
            model_name='establishment',
            index=models.Index(fields=['commercial_reg'], name='establishment_reg_idx'),
        ),
        migrations.AddIndex(
            model_name='establishment',
            index=models.Index(fields=['governorate', 'wilayat'], name='establishment_region_idx'),
        ),
        migrations.AddIndex(
            model_name='establishment',
            index=models.Index(fields=['status'], name='establishment_status_idx'),
        ),
        migrations.AddIndex(
            model_name='evaluation',
            index=models.Index(fields=['visit_date'], name='evaluation_visit_idx'),
        ),
        migrations.AddIndex(
            model_name='evaluation',
            index=models.Index(fields=['classification'], name='evaluation_class_idx'),
        ),
        migrations.AddIndex(
            model_name='evaluation',
            index=models.Index(fields=['approval_status'], name='evaluation_approval_idx'),
        ),
        migrations.AddIndex(
            model_name='evaluation',
            index=models.Index(fields=['establishment', 'visit_date'], name='evaluation_est_visit_idx'),
        ),
        migrations.AddIndex(
            model_name='evaluation',
            index=models.Index(fields=['inspector', 'visit_date'], name='evaluation_inspector_visit_idx'),
        ),
        migrations.AddIndex(
            model_name='evaluationitem',
            index=models.Index(fields=['evaluation', 'status'], name='evaluation_item_status_idx'),
        ),
    ]
