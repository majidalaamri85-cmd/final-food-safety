from django.core.management.base import BaseCommand
from django.db import transaction

from inspections.evaluation_template_data import EVALUATION_TEMPLATE_SECTIONS, REQUIRED_RECORDS
from inspections.models import Criterion, EvaluationSection, RequiredRecord


class Command(BaseCommand):
    help = "إنشاء الاستمارة الموحدة لسلامة الغذاء في المصانع الغذائية بحسب الملف المعتمد"

    def handle(self, *args, **options):
        active_codes = set()

        with transaction.atomic():
            for section_data in EVALUATION_TEMPLATE_SECTIONS:
                section = (
                    EvaluationSection.objects
                    .filter(sort_order=section_data['order'])
                    .order_by('id')
                    .first()
                )
                if section is None:
                    section = EvaluationSection.objects.create(
                        name_ar=section_data['name'],
                        name_en=section_data['name'],
                        sort_order=section_data['order'],
                    )
                else:
                    section.name_ar = section_data['name']
                    section.name_en = section_data['name']
                    section.sort_order = section_data['order']
                    section.save(update_fields=['name_ar', 'name_en', 'sort_order'])

                for item_index, item in enumerate(section_data['items'], start=1):
                    code = f"{section_data['order']}.{item_index}"
                    active_codes.add(code)
                    defaults = {
                        'section': section,
                        'sort_order': item_index,
                        'text_ar': item['text'],
                        'text_en': '',
                        'weight': item.get('weight', 1),
                        'risk_level': item.get('risk', section_data.get('risk', 'medium')),
                        'is_active': True,
                    }
                    criterion = Criterion.objects.filter(code=code).order_by('id').first()
                    if criterion is None:
                        Criterion.objects.create(code=code, **defaults)
                    else:
                        for field, value in defaults.items():
                            setattr(criterion, field, value)
                        criterion.save(update_fields=[*defaults.keys()])

            Criterion.objects.exclude(code__in=active_codes).update(is_active=False)

            RequiredRecord.objects.all().update(is_active=False)
            for record_name in REQUIRED_RECORDS:
                record = RequiredRecord.objects.filter(name_ar=record_name).order_by('id').first()
                if record is None:
                    RequiredRecord.objects.create(name_ar=record_name, name_en='', is_active=True)
                else:
                    record.name_en = ''
                    record.is_active = True
                    record.save(update_fields=['name_en', 'is_active'])

        self.stdout.write('تم تحميل استمارة تقييم المنشآت الغذائية الجديدة مع 100 بند والسجلات المطلوبة بنجاح.')
