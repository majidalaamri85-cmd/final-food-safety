from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from inspections.models import Establishment, Evaluation


class Command(BaseCommand):
    help = 'Delete virtual seeded establishments and related data.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--include-demo',
            action='store_true',
            help='Also delete the demo establishment/user created by seed_demo_data.',
        )

    def handle(self, *args, **options):
        include_demo = options['include_demo']

        virtual_qs = Establishment.objects.filter(
            license_no__startswith='V-LIC-',
            commercial_reg__startswith='V-CR-',
        )

        demo_qs = Establishment.objects.none()
        if include_demo:
            demo_qs = Establishment.objects.filter(
                license_no='LIC-001',
                commercial_reg='CR-001',
            )

        target_qs = (virtual_qs | demo_qs).distinct()
        establishment_count = target_qs.count()
        evaluation_count = Evaluation.objects.filter(establishment__in=target_qs).count()

        if establishment_count == 0:
            self.stdout.write(self.style.WARNING('لا توجد بيانات افتراضية مطابقة للحذف.'))
            return

        target_qs.delete()

        user_deleted = False
        if include_demo:
            inspector = User.objects.filter(username='inspector').first()
            if inspector and not Evaluation.objects.filter(inspector=inspector).exists():
                inspector.delete()
                user_deleted = True

        msg = (
            f'تم حذف البيانات الافتراضية بنجاح. '
            f'منشآت محذوفة: {establishment_count}، تقييمات محذوفة: {evaluation_count}.'
        )
        if include_demo and user_deleted:
            msg += ' وتم حذف المستخدم demo (inspector) لعدم وجود تقييمات مرتبطة.'

        self.stdout.write(self.style.SUCCESS(msg))
