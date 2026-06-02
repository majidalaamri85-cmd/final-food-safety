from decimal import Decimal

from django.db import migrations, models


def repair_evaluation_classifications(apps, schema_editor):
    Evaluation = apps.get_model('inspections', 'Evaluation')
    EvaluationItem = apps.get_model('inspections', 'EvaluationItem')
    EvaluationRecordCheck = apps.get_model('inspections', 'EvaluationRecordCheck')

    item_totals = {
        row['evaluation_id']: row
        for row in (
            EvaluationItem.objects.filter(criterion__is_active=True)
            .values('evaluation_id')
            .annotate(
                max_points=models.Sum(
                    'criterion__weight',
                    filter=~models.Q(status='na'),
                ),
                awarded=models.Sum('score_awarded'),
            )
        )
    }
    record_totals = {
        row['evaluation_id']: row
        for row in (
            EvaluationRecordCheck.objects.filter(record__is_active=True)
            .values('evaluation_id')
            .annotate(
                max_points=models.Count('id'),
                awarded=models.Count('id', filter=models.Q(is_available=True)),
            )
        )
    }

    evaluations = []
    for evaluation in Evaluation.objects.only('id'):
        item_total = item_totals.get(evaluation.id, {})
        record_total = record_totals.get(evaluation.id, {})
        max_points = Decimal(item_total.get('max_points') or 0)
        max_points += Decimal(record_total.get('max_points') or 0)
        awarded = Decimal(item_total.get('awarded') or 0)
        awarded += Decimal(record_total.get('awarded') or 0)
        percentage = Decimal('0')
        if max_points:
            percentage = (awarded / max_points) * Decimal('100')

        evaluation.total_points = awarded.quantize(Decimal('0.01'))
        evaluation.percentage = percentage.quantize(Decimal('0.01'))
        if evaluation.percentage >= 86:
            evaluation.classification = 'excellent'
        elif evaluation.percentage >= 70:
            evaluation.classification = 'good'
        elif evaluation.percentage >= 41:
            evaluation.classification = 'acceptable'
        else:
            evaluation.classification = 'weak'
        evaluations.append(evaluation)

    Evaluation.objects.bulk_update(
        evaluations,
        ['total_points', 'percentage', 'classification'],
        batch_size=500,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('inspections', '0003_qualificationfollowup_evaluation_haccpfile'),
    ]

    operations = [
        migrations.RunPython(repair_evaluation_classifications, migrations.RunPython.noop),
    ]
