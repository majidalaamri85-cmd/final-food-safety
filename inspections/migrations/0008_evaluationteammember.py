from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inspections', '0007_add_performance_indexes'),
    ]

    operations = [
        migrations.CreateModel(
            name='EvaluationTeamMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=255, verbose_name='الاسم')),
                ('job_title', models.CharField(max_length=255, verbose_name='المسمى الوظيفي')),
                ('sort_order', models.PositiveIntegerField(default=1, verbose_name='الترتيب')),
                ('evaluation', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='team_members', to='inspections.evaluation', verbose_name='التقييم')),
            ],
            options={
                'verbose_name': 'عضو فريق التقييم',
                'verbose_name_plural': 'أعضاء فريق التقييم',
                'ordering': ['sort_order', 'id'],
            },
        ),
    ]
