from datetime import timedelta
from random import Random

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from inspections.models import (
    Criterion,
    Establishment,
    Evaluation,
    EvaluationItem,
    EvaluationRecordCheck,
    EvaluationSection,
    Governorate,
    RequiredRecord,
    Wilayat,
)


class Command(BaseCommand):
    help = 'Seed virtual establishments and evaluations for testing.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            help='Number of virtual establishments to create (default: 20).',
        )

    def handle(self, *args, **options):
        count = max(1, int(options['count']))
        rnd = Random(2026)

        self._ensure_minimum_reference_data()

        inspector, _ = User.objects.get_or_create(username='inspector')
        if not inspector.is_staff or not inspector.is_superuser:
            inspector.is_staff = True
            inspector.is_superuser = True
            inspector.set_password('admin12345')
            inspector.save()

        governorates = list(Governorate.objects.order_by('id'))
        wilayats = list(Wilayat.objects.select_related('governorate').order_by('id'))
        if not governorates or not wilayats:
            self.stdout.write(self.style.ERROR('لا توجد بيانات مواقع كافية. شغّل seed_oman_locations أولاً.'))
            return

        criteria = list(
            Criterion.objects.select_related('section')
            .filter(is_active=True)
            .order_by('section__sort_order', 'sort_order', 'code')[:16]
        )
        records = list(RequiredRecord.objects.filter(is_active=True).order_by('id')[:6])

        if not criteria:
            self.stdout.write(self.style.ERROR('لا توجد بنود تقييم. شغّل seed_unified_template أولاً.'))
            return

        created_establishments = 0
        created_evaluations = 0

        activity_types = [
            'مصنع أغذية',
            'مخبز وحلويات',
            'تعبئة مياه',
            'مصنع منتجات ألبان',
            'مصنع لحوم',
        ]

        today = timezone.localdate()

        for i in range(1, count + 1):
            wilayat = wilayats[(i - 1) % len(wilayats)]
            governorate = wilayat.governorate
            seq = 1000 + i

            establishment, est_created = Establishment.objects.get_or_create(
                license_no=f'V-LIC-{seq}',
                commercial_reg=f'V-CR-{seq}',
                defaults={
                    'governorate': governorate,
                    'wilayat': wilayat,
                    'commercial_name': f'منشأة افتراضية رقم {i}',
                    'activity_type': activity_types[(i - 1) % len(activity_types)],
                    'manager_name': f'مدير افتراضي {i}',
                    'contact_phone': f'9{(7000000 + i):07d}',
                    'contact_email': f'virtual{i}@example.com',
                    'employee_count': rnd.randint(8, 90),
                    'production_capacity': f'{rnd.randint(1, 20)} طن/يوم',
                    'product_types': 'منتجات غذائية متنوعة',
                    'status': 'active',
                },
            )
            if est_created:
                created_establishments += 1

            visit_date = today - timedelta(days=rnd.randint(0, 90))
            evaluation, eval_created = Evaluation.objects.get_or_create(
                establishment=establishment,
                visit_date=visit_date,
                inspector=inspector,
                defaults={
                    'approval_status': 'completed',
                    'notes': f'تقييم افتراضي آلي للمنشأة رقم {i}',
                },
            )

            if eval_created:
                for criterion in criteria:
                    roll = rnd.random()
                    if roll < 0.72:
                        status = 'compliant'
                    elif roll < 0.92:
                        status = 'non_compliant'
                    else:
                        status = 'observation'

                    EvaluationItem.objects.get_or_create(
                        evaluation=evaluation,
                        criterion=criterion,
                        defaults={
                            'status': status,
                            'remarks': 'مولد تلقائي لأغراض الاختبار',
                        },
                    )

                for record in records:
                    EvaluationRecordCheck.objects.get_or_create(
                        evaluation=evaluation,
                        record=record,
                        defaults={
                            'is_available': rnd.random() < 0.8,
                            'remarks': 'فحص سجل افتراضي',
                        },
                    )

                evaluation.calculate_results()
                evaluation.approval_status = 'completed'
                evaluation.save()
                created_evaluations += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'تم إنشاء/تحديث بيانات افتراضية بنجاح. منشآت جديدة: {created_establishments}، تقييمات جديدة: {created_evaluations}.',
            )
        )

    def _ensure_minimum_reference_data(self):
        if not Governorate.objects.exists():
            muscat = Governorate.objects.create(name_ar='مسقط', name_en='Muscat')
            Wilayat.objects.create(governorate=muscat, name_ar='بوشر', name_en='Bausher')

        if not EvaluationSection.objects.exists():
            section = EvaluationSection.objects.create(
                name_ar='متطلبات أساسية',
                name_en='Basic Requirements',
                sort_order=1,
            )
            Criterion.objects.create(
                section=section,
                code='1.1',
                sort_order=1,
                text_ar='توفر متطلبات الترخيص الأساسية',
                text_en='Basic licensing requirements are available',
                weight=5,
                risk_level='high',
                is_active=True,
            )

        if not RequiredRecord.objects.exists():
            RequiredRecord.objects.create(name_ar='سجل درجات الحرارة', name_en='Temperature Log', is_active=True)