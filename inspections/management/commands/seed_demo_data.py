from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from inspections.models import (
    Criterion, Establishment, Evaluation, EvaluationItem, EvaluationSection,
    Governorate, RequiredRecord, Wilayat
)
from datetime import date


class Command(BaseCommand):
    help = 'Seed demo data for food safety system'

    def handle(self, *args, **options):
        muscat, _ = Governorate.objects.get_or_create(name_ar='مسقط', defaults={'name_en': 'Muscat'})
        muttrah, _ = Wilayat.objects.get_or_create(governorate=muscat, name_ar='بوشر', defaults={'name_en': 'Bausher'})

        section1, _ = EvaluationSection.objects.get_or_create(name_ar='المتطلبات العامة', defaults={'name_en': 'General Requirements', 'sort_order': 1})
        section2, _ = EvaluationSection.objects.get_or_create(name_ar='النظافة والتعقيم', defaults={'name_en': 'Cleaning and Sanitation', 'sort_order': 2})

        c1, _ = Criterion.objects.get_or_create(section=section1, code=1, defaults={'text_ar': 'توفر الترخيص والسجل التجاري', 'text_en': 'License and CR available', 'weight': 5, 'risk_level': 'high'})
        c2, _ = Criterion.objects.get_or_create(section=section2, code=1, defaults={'text_ar': 'تنفيذ برنامج تنظيف وتطهير فعال', 'text_en': 'Cleaning program implemented', 'weight': 5, 'risk_level': 'critical'})

        RequiredRecord.objects.get_or_create(name_ar='سجل درجات الحرارة', defaults={'name_en': 'Temperature Log'})
        RequiredRecord.objects.get_or_create(name_ar='سجل التنظيف والتطهير', defaults={'name_en': 'Cleaning and Sanitation Log'})

        inspector, created = User.objects.get_or_create(username='inspector')
        if created:
            inspector.set_password('admin12345')
            inspector.is_staff = True
            inspector.is_superuser = True
            inspector.save()

        est, _ = Establishment.objects.get_or_create(
            license_no='LIC-001', commercial_reg='CR-001',
            defaults={
                'governorate': muscat,
                'wilayat': muttrah,
                'commercial_name': 'مصنع الأغذية النموذجي',
                'activity_type': 'مصنع أغذية',
                'manager_name': 'مدير المصنع',
                'contact_phone': '90000000',
                'status': 'active'
            }
        )

        evaluation, created = Evaluation.objects.get_or_create(
            establishment=est,
            visit_date=date.today(),
            inspector=inspector,
            defaults={'notes': 'بيانات تجريبية'}
        )
        if created:
            EvaluationItem.objects.get_or_create(evaluation=evaluation, criterion=c1, defaults={'status': 'compliant'})
            EvaluationItem.objects.get_or_create(evaluation=evaluation, criterion=c2, defaults={'status': 'non_compliant', 'remarks': 'يلزم تحسين الخطة'})
            evaluation.calculate_results()
            evaluation.save()

        self.stdout.write(self.style.SUCCESS('Demo data seeded successfully.'))
