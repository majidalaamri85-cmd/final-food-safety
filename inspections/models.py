from django.db import models

# HACCP File Model
class HACCPFile(models.Model):
    HACCP_FILE_TYPES = [
        ('policy', 'سياسة سلامة الغذاء'),
        ('product_desc', 'وصف المنتج'),
        ('process_flow', 'مخطط تدفق العملية'),
        ('flow_verification', 'التحقق من مخطط التدفق'),
        ('hazard_analysis', 'تحليل المخاطر'),
        ('ccp', 'تحديد CCP'),
        ('critical_limits', 'الحدود الحرجة'),
        ('monitoring', 'إجراءات المراقبة'),
        ('corrective', 'الإجراءات التصحيحية'),
        ('verification', 'التحقق والتحقق الداخلي'),
        ('records', 'السجلات والنماذج'),
        ('recall_plan', 'خطة السحب والاستدعاء'),
        ('traceability', 'التتبع'),
        ('training', 'التدريب'),
        ('prps', 'النظافة والاشتراطات التمهيدية PRPs'),
        ('other', 'ملف آخر'),
    ]

    establishment = models.ForeignKey(
        'Establishment',
        verbose_name='المنشأة',
        on_delete=models.CASCADE,
        related_name='haccp_files',
    )
    file_type = models.CharField('نوع الملف', max_length=30, choices=HACCP_FILE_TYPES)
    title = models.CharField('عنوان الملف', max_length=255, blank=True)
    file = models.FileField('الملف', upload_to='haccp_files/')
    uploaded_at = models.DateTimeField('تاريخ الرفع', auto_now_add=True)
    notes = models.TextField('ملاحظات', blank=True)

    class Meta:
        verbose_name = 'ملف HACCP'
        verbose_name_plural = 'ملفات HACCP'
        ordering = ['file_type', 'uploaded_at']

    def __str__(self):
        return f"{self.get_file_type_display()} - {self.establishment.commercial_name}"
from decimal import Decimal
from django.contrib.auth.models import User
from django.db import models
from django.db import transaction
from django.utils import timezone


class Governorate(models.Model):
    name_ar = models.CharField('اسم المحافظة بالعربية', max_length=150)
    name_en = models.CharField('اسم المحافظة بالإنجليزية', max_length=150)

    class Meta:
        ordering = ['name_ar']
        verbose_name = 'المحافظة'
        verbose_name_plural = 'المحافظات'

    def __str__(self):
        return self.name_ar


class Wilayat(models.Model):
    governorate = models.ForeignKey(Governorate, verbose_name='المحافظة', on_delete=models.CASCADE, related_name='wilayats')
    name_ar = models.CharField('اسم الولاية بالعربية', max_length=150)
    name_en = models.CharField('اسم الولاية بالإنجليزية', max_length=150)

    class Meta:
        ordering = ['governorate__name_ar', 'name_ar']
        verbose_name = 'الولاية'
        verbose_name_plural = 'الولايات'

    def __str__(self):
        return f'{self.name_ar} - {self.governorate.name_ar}'


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'مدير النظام'),
        ('central', 'الإدارة المركزية'),
        ('manager', 'مدير محافظة'),
        ('inspector', 'مفتش / مقيم'),
        ('reviewer', 'مراجع فني'),
    ]

    user = models.OneToOneField(User, verbose_name='المستخدم', on_delete=models.CASCADE)
    full_name = models.CharField('الاسم الكامل', max_length=255)
    role = models.CharField('الدور الوظيفي', max_length=30, choices=ROLE_CHOICES, default='inspector')
    phone = models.CharField('رقم الهاتف', max_length=30, blank=True)
    governorate = models.ForeignKey(Governorate, verbose_name='المحافظة', on_delete=models.SET_NULL, null=True, blank=True)
    is_active_inspector = models.BooleanField('نشط كمفتش', default=True)

    class Meta:
        verbose_name = 'ملف المستخدم'
        verbose_name_plural = 'ملفات المستخدمين'

    def __str__(self):
        return self.full_name


class Establishment(models.Model):
    STATUS_CHOICES = [
        ('active', 'نشط'),
        ('suspended', 'موقوف'),
        ('closed', 'مغلق'),
    ]

    governorate = models.ForeignKey(Governorate, verbose_name='المحافظة', on_delete=models.PROTECT, related_name='establishments')
    wilayat = models.ForeignKey(Wilayat, verbose_name='الولاية', on_delete=models.PROTECT, related_name='establishments')
    establishment_no = models.PositiveIntegerField('رقم المنشأة', unique=True, db_index=True, null=True, blank=True)
    commercial_name = models.CharField('الاسم التجاري', max_length=255)
    activity_type = models.CharField('النشاط الرئيسي', max_length=255)
    license_no = models.CharField('رقم رخصة النشاط', max_length=100)
    commercial_reg = models.CharField('رقم السجل التجاري', max_length=100)
    manager_name = models.CharField('اسم مدير الجودة أو سلامة الغذاء', max_length=255)
    contact_phone = models.CharField('رقم التواصل', max_length=30)
    contact_email = models.EmailField('البريد الإلكتروني', blank=True)
    employee_count = models.PositiveIntegerField('عدد الموظفين', null=True, blank=True)
    production_capacity = models.CharField('الطاقة الإنتاجية', max_length=255, blank=True)
    product_types = models.TextField('نوع المنتجات', blank=True)
    doc_commercial_register = models.FileField('السجل التجاري', upload_to='establishment_docs/', blank=True, null=True)
    doc_municipal_license = models.FileField('الترخيص البلدي', upload_to='establishment_docs/', blank=True, null=True)
    doc_quality_certificates = models.FileField('شهادات الجودة', upload_to='establishment_docs/', blank=True, null=True)
    doc_factory_layout = models.FileField('مخططات المصنع', upload_to='establishment_docs/', blank=True, null=True)
    direct_location_url = models.URLField('الموقع المباشر', blank=True)
    latitude = models.DecimalField('خط العرض', max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField('خط الطول', max_digits=10, decimal_places=7, null=True, blank=True)
    status = models.CharField('حالة المنشأة', max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)

    class Meta:
        ordering = ['commercial_name']
        verbose_name = 'المنشأة'
        verbose_name_plural = 'المنشآت'
        constraints = [
            models.UniqueConstraint(fields=['license_no', 'commercial_reg'], name='unique_establishment_license_reg'),
        ]
        indexes = [
            models.Index(fields=['commercial_name'], name='establishment_name_idx'),
            models.Index(fields=['license_no'], name='establishment_license_idx'),
            models.Index(fields=['commercial_reg'], name='establishment_reg_idx'),
            models.Index(fields=['governorate', 'wilayat'], name='establishment_region_idx'),
            models.Index(fields=['status'], name='establishment_status_idx'),
        ]

    def __str__(self):
        return self.commercial_name

    @property
    def reference_no(self):
        year = (self.created_at or timezone.now()).year
        serial = self.establishment_no or self.pk or 0
        return f'EST-{year}-{serial:05d}'

    def save(self, *args, **kwargs):
        if not self.establishment_no:
            with transaction.atomic():
                last_no = (
                    Establishment.objects.select_for_update()
                    .order_by('-establishment_no')
                    .values_list('establishment_no', flat=True)
                    .first()
                    or 0
                )
                self.establishment_no = last_no + 1
                return super().save(*args, **kwargs)
        return super().save(*args, **kwargs)


class EvaluationSection(models.Model):
    name_ar = models.CharField('اسم القسم بالعربية', max_length=255)
    name_en = models.CharField('اسم القسم بالإنجليزية', max_length=255)
    sort_order = models.PositiveIntegerField('ترتيب القسم', default=1)

    class Meta:
        ordering = ['sort_order', 'name_ar']
        verbose_name = 'قسم التقييم'
        verbose_name_plural = 'أقسام التقييم'

    def __str__(self):
        return self.name_ar


class Criterion(models.Model):
    RISK_CHOICES = [
        ('low', 'منخفض'),
        ('medium', 'متوسط'),
        ('high', 'عالٍ'),
        ('critical', 'حرج'),
    ]

    section = models.ForeignKey(EvaluationSection, verbose_name='القسم', on_delete=models.CASCADE, related_name='criteria')
    code = models.CharField('رقم البند', max_length=20)
    sort_order = models.PositiveIntegerField('ترتيب البند', default=1)
    text_ar = models.TextField('نص البند بالعربية')
    text_en = models.TextField('نص البند بالإنجليزية', blank=True)
    weight = models.PositiveIntegerField('الدرجة القصوى', default=1)
    risk_level = models.CharField('مستوى الخطورة', max_length=10, choices=RISK_CHOICES, default='medium')
    is_active = models.BooleanField('مفعل', default=True)

    class Meta:
        ordering = ['section__sort_order', 'sort_order', 'code']
        verbose_name = 'البند'
        verbose_name_plural = 'بنود التقييم'
        unique_together = ('section', 'code')

    def __str__(self):
        return f'{self.code} - {self.text_ar[:60]}'


class RequiredRecord(models.Model):
    name_ar = models.CharField('اسم السجل بالعربية', max_length=255)
    name_en = models.CharField('اسم السجل بالإنجليزية', max_length=255, blank=True)
    is_active = models.BooleanField('مفعل', default=True)

    class Meta:
        ordering = ['name_ar']
        verbose_name = 'سجل مطلوب'
        verbose_name_plural = 'السجلات المطلوبة'

    def __str__(self):
        return self.name_ar


class Evaluation(models.Model):
    CLASSIFICATION_CHOICES = [
        ('excellent', 'ممتاز'),
        ('good', 'جيد'),
        ('acceptable', 'مقبول'),
        ('weak', 'ضعيف'),
    ]
    APPROVAL_STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('completed', 'مكتمل'),
    ]

    establishment = models.ForeignKey(Establishment, verbose_name='المنشأة', on_delete=models.CASCADE, related_name='evaluations')
    inspector = models.ForeignKey(User, verbose_name='المفتش / المقيم', on_delete=models.PROTECT, related_name='inspector_evaluations')
    reviewer = models.ForeignKey(User, verbose_name='المراجع الفني', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewer_evaluations')
    visit_date = models.DateField('تاريخ التقييم')
    total_points = models.DecimalField('إجمالي النقاط المحققة', max_digits=7, decimal_places=2, default=0)
    percentage = models.DecimalField('نسبة الامتثال', max_digits=5, decimal_places=2, default=0)
    classification = models.CharField('التصنيف النهائي', max_length=20, choices=CLASSIFICATION_CHOICES, default='acceptable')
    approval_status = models.CharField('حالة التقييم', max_length=20, choices=APPROVAL_STATUS_CHOICES, default='draft')
    reviewed_at = models.DateTimeField('تاريخ المراجعة', null=True, blank=True)
    rejection_reason = models.TextField('سبب الرفض', blank=True)
    notes = models.TextField('ملاحظات عامة', blank=True)
    corrective_action = models.TextField('الإجراءات التصحيحية العامة', blank=True)
    follow_up_date = models.DateField('تاريخ المتابعة', null=True, blank=True)
    created_at = models.DateTimeField('تاريخ إنشاء التقييم', auto_now_add=True)

    class Meta:
        ordering = ['-visit_date', '-created_at']
        verbose_name = 'التقييم'
        verbose_name_plural = 'التقييمات'
        indexes = [
            models.Index(fields=['visit_date'], name='evaluation_visit_idx'),
            models.Index(fields=['classification'], name='evaluation_class_idx'),
            models.Index(fields=['approval_status'], name='evaluation_approval_idx'),
            models.Index(fields=['establishment', 'visit_date'], name='evaluation_est_visit_idx'),
            models.Index(fields=['inspector', 'visit_date'], name='evaluation_inspector_visit_idx'),
        ]

    def __str__(self):
        return f'{self.establishment.commercial_name} - {self.visit_date}'

    @property
    def report_reference_no(self):
        visit = self.visit_date or timezone.localdate()
        serial = self.pk or 0
        return f'REP-{visit.year}-{serial:06d}'

    def calculate_results(self, items=None, record_checks=None):
        if items is None:
            items = list(self.items.select_related('criterion'))
        if record_checks is None:
            record_checks = list(self.record_checks.select_related('record'))
        max_points = sum(i.criterion.weight for i in items if i.status != 'na')
        max_points += sum(1 for record_check in record_checks if record_check.record.is_active)
        awarded = sum(Decimal(i.score_awarded) for i in items)
        awarded += sum(Decimal('1') for record_check in record_checks if record_check.is_available)
        percentage = Decimal('0')
        if max_points:
            percentage = (awarded / Decimal(max_points)) * Decimal('100')
        self.total_points = awarded.quantize(Decimal('0.01'))
        self.percentage = percentage.quantize(Decimal('0.01'))
        self.classification = self.suggest_classification()
        return self.total_points, self.percentage

    def has_blocking_risk_non_compliance(self):
        if not self.pk:
            return False
        return self.items.filter(
            status='non_compliant',
            criterion__risk_level__in=['high', 'critical'],
        ).exists()

    def blocking_risk_non_compliant_codes(self):
        if not self.pk:
            return []
        return list(
            self.items.filter(
                status='non_compliant',
                criterion__risk_level__in=['high', 'critical'],
            )
            .select_related('criterion')
            .order_by('criterion__section__sort_order', 'criterion__sort_order', 'criterion__code')
            .values_list('criterion__code', flat=True)
        )

    def suggest_classification(self):
        pct = Decimal(self.percentage or 0)
        if pct >= 86:
            return 'excellent'
        if pct >= 70:
            return 'good'
        if pct >= 41:
            return 'acceptable'
        return 'weak'

    @property
    def establishment_status(self):
        """إرجاع وصف حالة المنشأة بناءً على نسبة الامتثال."""
        pct = Decimal(self.percentage or 0)
        if pct >= 86:
            return {
                'label': 'ممتاز',
                'range': '86% - 100%',
                'description': 'مستوفي للحصول على شهادة ضبط الجودة',
                'color': 'success',
                'icon': 'fa-star',
                'blocks_grant': False,
                'blocking_codes': [],
            }
        if pct >= 70:
            return {
                'label': 'جيد',
                'range': '70% - 85%',
                'description': 'مستوفي للحصول على شهادة ضبط الجودة مع وجود فرص للتحسين',
                'color': 'info',
                'icon': 'fa-thumbs-up',
                'blocks_grant': False,
                'blocking_codes': [],
            }
        if pct >= 41:
            return {
                'label': 'مقبول',
                'range': '41% - 69%',
                'description': 'يحتاج تأهيل ومزيد من التحسين',
                'color': 'warning',
                'icon': 'fa-triangle-exclamation',
                'blocks_grant': False,
                'blocking_codes': [],
            }
        return {
            'label': 'ضعيف',
            'range': '0% - 40%',
            'description': 'إيقاف الإنتاج',
            'color': 'danger',
            'icon': 'fa-circle-xmark',
            'blocks_grant': True,
            'blocking_codes': [],
        }

    def mark_completed(self):
        self.calculate_results()
        self.approval_status = 'completed'
        self.save()


class QualificationFollowUp(models.Model):
    STATUS_CHOICES = [
        ('not_started', 'لم يبدأ'),
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'مكتمل'),
        ('stalled', 'متعثر'),
    ]

    QUALITY_SYSTEM_CHOICES = [
        ('ISO 22000', 'ISO 22000'),
        ('ISO 9001', 'ISO 9001'),
        ('HACCP', 'HACCP'),
        ('GMP', 'GMP'),
        ('Halal', 'Halal'),
        ('Organic', 'Organic'),
        ('G.A.P', 'G.A.P'),
        ('Others', 'أخرى'),
    ]

    establishment = models.ForeignKey(
        Establishment,
        verbose_name='المنشأة المسجلة',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='qualification_followups',
    )
    governorate = models.CharField('المحافظة', max_length=150)
    establishment_name = models.CharField('اسم المنشأة', max_length=255)
    activity_type = models.CharField('نوع النشاط', max_length=255)
    current_status = models.CharField('الحالة الحالية', max_length=20, choices=STATUS_CHOICES, default='not_started')
    quality_system = models.CharField('أنظمة الجودة وسلامة الغذاء', max_length=100, choices=QUALITY_SYSTEM_CHOICES, blank=True)
    custom_quality_system = models.CharField('نظام جودة آخر', max_length=150, blank=True)
    start_date = models.DateField('تاريخ البدء', null=True, blank=True)
    expected_completion_date = models.DateField('تاريخ الإنجاز المتوقع', null=True, blank=True)
    progress_percent = models.PositiveSmallIntegerField('نسبة الإنجاز (%)', default=0)
    challenges = models.TextField('التحديات', blank=True)
    notes = models.TextField('ملاحظات', blank=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)
    updated_at = models.DateTimeField('تاريخ التحديث', auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-id']
        verbose_name = 'متابعة تأهيل منشأة'
        verbose_name_plural = 'متابعة تأهيل المنشآت'
        indexes = [
            models.Index(fields=['governorate'], name='qual_follow_gov_idx'),
            models.Index(fields=['current_status'], name='qual_follow_status_idx'),
            models.Index(fields=['expected_completion_date'], name='qual_follow_due_idx'),
        ]

    def __str__(self):
        return f'{self.establishment_name} - {self.get_current_status_display()}'

    @property
    def governorate_code(self):
        mapping = {
            'مسقط': 'MA',
            'ظفار': 'ZU',
            'مسندم': 'MU',
            'البريمي': 'BU',
            'الداخلية': 'DA',
            'شمال الباطنة': 'NB',
            'جنوب الباطنة': 'SB',
            'شمال الشرقية': 'NS',
            'جنوب الشرقية': 'SS',
            'الظاهرة': 'DH',
            'الوسطى': 'WU',
        }
        return mapping.get((self.governorate or '').strip(), 'NA')

    @property
    def activity_code(self):
        text = (self.activity_type or '').strip()
        mapping = {
            'مصنع مياه': 'WTR',
            'تجهيز وتجميد الأسماك': 'FSH',
            'مسحوق وزيت السمك وتكرير الزيت': 'FSH',
            'سفن الصيد': 'FSH',
            'القيمة المضافة': 'VAD',
            'الاستزراع السمكي': 'AQU',
            'مزارع الروبيان': 'SHR',
            'الالبان': 'DRY',
            'الألبان': 'DRY',
            'الخضروات الفواكة': 'FVG',
            'الخضروات والفواكه': 'FVG',
            'العصائر': 'JUC',
            'عصائر': 'JUC',
            'اللحوم والدواجن': 'MET',
            'مشروبات الغازية': 'BEV',
            'مشروبات غازية': 'BEV',
            'منتجات الحبوب': 'GRN',
            'الزيوت': 'OIL',
        }
        return mapping.get(text, 'GEN')

    @property
    def facility_reference_code(self):
        serial = self.establishment.establishment_no if self.establishment_id else (self.pk or 0)
        return f'FSQ-OM-{self.governorate_code}-{self.activity_code}-{serial:04d}'

    @property
    def visit_year(self):
        date_value = self.start_date or self.created_at or timezone.now()
        return date_value.year

    @property
    def visit_no(self):
        if not self.pk:
            return 1
        return (
            QualificationFollowUp.objects
            .filter(establishment=self.establishment)
            .filter(pk__lte=self.pk)
            .count()
            if self.establishment_id
            else 1
        )

    @property
    def visit_reference_code(self):
        return f'{self.facility_reference_code}-{self.visit_year}-{self.visit_no:03d}'

    @property
    def django_link_key(self):
        return self.visit_reference_code

    @property
    def is_overdue(self):
        return (
            self.expected_completion_date
            and self.expected_completion_date < timezone.localdate()
            and self.current_status != 'completed'
        )

    def save(self, *args, **kwargs):
        if self.establishment_id:
            self.establishment_name = self.establishment_name or self.establishment.commercial_name
            self.activity_type = self.activity_type or self.establishment.activity_type
            self.governorate = self.governorate or self.establishment.governorate.name_ar
        if self.current_status == 'completed':
            self.progress_percent = 100
        elif self.current_status == 'in_progress' and not self.progress_percent:
            self.progress_percent = 50
        elif self.current_status in {'not_started', 'stalled'}:
            self.progress_percent = 0
        self.progress_percent = max(0, min(int(self.progress_percent or 0), 100))
        super().save(*args, **kwargs)


class EvaluationTeamMember(models.Model):
    evaluation = models.ForeignKey(Evaluation, verbose_name='التقييم', on_delete=models.CASCADE, related_name='team_members')
    full_name = models.CharField('الاسم', max_length=255)
    job_title = models.CharField('المسمى الوظيفي', max_length=255)
    sort_order = models.PositiveIntegerField('الترتيب', default=1)

    class Meta:
        ordering = ['sort_order', 'id']
        verbose_name = 'عضو فريق التقييم'
        verbose_name_plural = 'أعضاء فريق التقييم'

    def __str__(self):
        return f'{self.full_name} - {self.job_title}'

class EvaluationItem(models.Model):
    STATUS_CHOICES = [
        ('compliant', 'مستوفي'),
        ('non_compliant', 'غير مستوفي'),
        ('na', 'لا ينطبق'),
        ('observation', 'ملاحظة'),
    ]

    evaluation = models.ForeignKey(Evaluation, verbose_name='التقييم', on_delete=models.CASCADE, related_name='items')
    criterion = models.ForeignKey(Criterion, verbose_name='البند', on_delete=models.CASCADE, related_name='evaluation_items')
    status = models.CharField('النتيجة', max_length=20, choices=STATUS_CHOICES, default='compliant')
    remarks = models.TextField('الملاحظات', blank=True)
    corrective_action = models.TextField('الإجراء التصحيحي', blank=True)
    score_awarded = models.DecimalField('الدرجة المحققة', max_digits=6, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'عنصر التقييم'
        verbose_name_plural = 'عناصر التقييم'
        unique_together = ('evaluation', 'criterion')
        indexes = [
            models.Index(fields=['evaluation', 'status'], name='evaluation_item_status_idx'),
        ]

    def __str__(self):
        return f'{self.evaluation} - {self.criterion.code}'

    def save(self, *args, **kwargs):
        if self.status == 'compliant':
            self.score_awarded = self.criterion.weight
        elif self.status in {'na', 'observation'}:
            self.score_awarded = 0
        else:
            self.score_awarded = 0
        super().save(*args, **kwargs)


class EvaluationRecordCheck(models.Model):
    evaluation = models.ForeignKey(Evaluation, verbose_name='التقييم', on_delete=models.CASCADE, related_name='record_checks')
    record = models.ForeignKey(RequiredRecord, verbose_name='السجل', on_delete=models.CASCADE, related_name='record_checks')
    is_available = models.BooleanField('متوفر', default=False)
    remarks = models.CharField('ملاحظات', max_length=255, blank=True)

    class Meta:
        verbose_name = 'تحقق السجل'
        verbose_name_plural = 'تحققات السجلات'
        unique_together = ('evaluation', 'record')


class EvaluationImage(models.Model):
    evaluation = models.ForeignKey(Evaluation, verbose_name='التقييم', on_delete=models.CASCADE, related_name='images')
    criterion = models.ForeignKey(Criterion, verbose_name='البند', on_delete=models.SET_NULL, null=True, blank=True, related_name='images')
    image = models.ImageField('الصورة', upload_to='evaluation_images/')
    caption = models.CharField('وصف الصورة', max_length=255, blank=True)
    taken_at = models.DateTimeField('وقت الالتقاط', null=True, blank=True)
    latitude = models.DecimalField('خط العرض', max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField('خط الطول', max_digits=10, decimal_places=7, null=True, blank=True)
    created_at = models.DateTimeField('تاريخ الإضافة', auto_now_add=True)

    class Meta:
        verbose_name = 'صورة التقييم'
        verbose_name_plural = 'صور التقييم'


class CorrectiveActionLog(models.Model):
    STATUS_CHOICES = [
        ('open', 'مفتوح'),
        ('in_progress', 'قيد التنفيذ'),
        ('closed', 'مغلق'),
        ('overdue', 'متأخر'),
    ]

    evaluation = models.ForeignKey(Evaluation, verbose_name='التقييم', on_delete=models.CASCADE, related_name='corrective_logs')
    criterion = models.ForeignKey(Criterion, verbose_name='البند', on_delete=models.SET_NULL, null=True, blank=True, related_name='corrective_logs')
    created_by = models.ForeignKey(User, verbose_name='أُنشئ بواسطة', on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField('عنوان الإجراء', max_length=255)
    details = models.TextField('تفاصيل الإجراء')
    assigned_to = models.CharField('مكلّف بالتنفيذ', max_length=255)
    due_date = models.DateField('تاريخ الاستحقاق', null=True, blank=True)
    status = models.CharField('حالة الإجراء', max_length=20, choices=STATUS_CHOICES, default='open')
    closed_at = models.DateTimeField('تاريخ الإغلاق', null=True, blank=True)
    created_at = models.DateTimeField('تاريخ الإنشاء', auto_now_add=True)

    class Meta:
        ordering = ['status', 'due_date']
        verbose_name = 'إجراء تصحيحي'
        verbose_name_plural = 'الإجراءات التصحيحية'
        indexes = [
            models.Index(fields=['status'], name='corrective_status_idx'),
            models.Index(fields=['due_date'], name='corrective_due_idx'),
        ]

    def __str__(self):
        return self.title


class EvaluationActivityLog(models.Model):
    evaluation = models.ForeignKey(Evaluation, verbose_name='التقييم', on_delete=models.CASCADE, related_name='activity_logs')
    user = models.ForeignKey(User, verbose_name='المستخدم', on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField('الإجراء', max_length=255)
    notes = models.TextField('ملاحظات', blank=True)
    created_at = models.DateTimeField('تاريخ التنفيذ', auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'سجل نشاط'
        verbose_name_plural = 'سجلات النشاط'

    def __str__(self):
        return f'{self.action} - {self.created_at:%Y-%m-%d %H:%M}'
