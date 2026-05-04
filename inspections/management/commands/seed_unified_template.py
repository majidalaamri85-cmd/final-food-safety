from django.core.management.base import BaseCommand

from inspections.evaluation_template_data import EVALUATION_TEMPLATE_SECTIONS, REQUIRED_RECORDS
from inspections.models import Criterion, EvaluationSection, RequiredRecord


class Command(BaseCommand):
    help = "إنشاء الاستمارة الموحدة لسلامة الغذاء في المصانع الغذائية بحسب الملف المعتمد"

    def handle(self, *args, **options):
        Criterion.objects.all().delete()
        EvaluationSection.objects.all().delete()
        RequiredRecord.objects.all().delete()

        for section_data in EVALUATION_TEMPLATE_SECTIONS:
            section = EvaluationSection.objects.create(
                name_ar=section_data['name'],
                name_en=section_data['name'],
                sort_order=section_data['order'],
            )
            for item_index, item in enumerate(section_data['items'], start=1):
                Criterion.objects.create(
                    section=section,
                    code=f"{section_data['order']}.{item_index}",
                    sort_order=item_index,
                    text_ar=item['text'],
                    text_en='',
                    weight=item.get('weight', 1),
                    risk_level=item.get('risk', section_data.get('risk', 'medium')),
                    is_active=True,
                )

        for record_name in REQUIRED_RECORDS:
            RequiredRecord.objects.create(name_ar=record_name, name_en='', is_active=True)

        self.stdout.write('تم تحميل استمارة تقييم المنشآت الغذائية الجديدة مع 100 بند والسجلات المطلوبة بنجاح.')
