from django import forms
from django.utils import timezone

from .models import (
    CorrectiveActionLog,
    Establishment,
    Evaluation,
    EvaluationItem,
    EvaluationRecordCheck,
    EvaluationTeamMember,
    QualificationFollowUp,
    Wilayat,
)


class EstablishmentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['governorate'].queryset = self.fields['governorate'].queryset.order_by('name_ar')
        self.fields['wilayat'].queryset = (
            Wilayat.objects.select_related('governorate')
            .only('id', 'name_ar', 'governorate_id', 'governorate__name_ar')
            .order_by('governorate__name_ar', 'name_ar')
        )

    def clean_establishment_no(self):
        no = self.cleaned_data.get('establishment_no')
        if no:
            qs = Establishment.objects.filter(establishment_no=no)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('رقم المنشأة هذا مستخدم مسبقاً، اختر رقماً آخر.')
        return no

    class Meta:
        model = Establishment
        fields = [
            'governorate', 'wilayat', 'commercial_name', 'activity_type', 'license_no',
            'commercial_reg', 'manager_name', 'contact_phone', 'contact_email',
            'employee_count', 'production_capacity', 'product_types',
            'doc_commercial_register', 'doc_municipal_license',
            'doc_quality_certificates', 'doc_factory_layout',
            'direct_location_url', 'status'
        ]
        widgets = {
            'governorate': forms.Select(attrs={'class': 'form-select'}),
            'wilayat': forms.Select(attrs={'class': 'form-select'}),
            'commercial_name': forms.TextInput(attrs={'class': 'form-control'}),
            'activity_type': forms.TextInput(attrs={'class': 'form-control', 'list': 'isic-activities', 'placeholder': 'ابدأ بكتابة النشاط أو رمز آيسك'}),
            'license_no': forms.TextInput(attrs={'class': 'form-control'}),
            'commercial_reg': forms.TextInput(attrs={'class': 'form-control'}),
            'manager_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@domain.com'}),
            'establishment_no': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'اتركه فارغاً للتوليد التلقائي'}),
            'employee_count': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'production_capacity': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: 2 طن يوميا'}),
            'product_types': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'اذكر المنتجات الرئيسية'}),
            'doc_commercial_register': forms.FileInput(attrs={'class': 'form-control'}),
            'doc_municipal_license': forms.FileInput(attrs={'class': 'form-control'}),
            'doc_quality_certificates': forms.FileInput(attrs={'class': 'form-control'}),
            'doc_factory_layout': forms.FileInput(attrs={'class': 'form-control'}),
            'direct_location_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'إضغط لإختيار الموقع المباشر'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'establishment_no': 'رقم المنشأة',
            'governorate': 'المحافظة',
            'wilayat': 'الولاية / المدينة',
            'commercial_name': 'اسم المنشأة (التجاري)',
            'activity_type': 'نوع النشاط الرئيسي',
            'license_no': 'رقم رخصة النشاط',
            'commercial_reg': 'رقم السجل التجاري',
            'manager_name': 'اسم مدير الجودة أو سلامة الغذاء',
            'contact_phone': 'رقم التواصل',
            'contact_email': 'الإيميل',
            'employee_count': 'عدد الموظفين',
            'production_capacity': 'الطاقة الإنتاجية',
            'product_types': 'نوع المنتجات',
            'doc_commercial_register': 'السجل التجاري',
            'doc_municipal_license': 'الترخيص البلدي',
            'doc_quality_certificates': 'شهادات الجودة',
            'doc_factory_layout': 'مخططات المصنع',
            'direct_location_url': 'الموقع المباشر',
            'status': 'حالة المنشأة',
        }


class EvaluationForm(forms.ModelForm):
    class Meta:
        model = Evaluation
        fields = ['establishment', 'visit_date', 'notes', 'corrective_action', 'follow_up_date']
        widgets = {
            'establishment': forms.Select(attrs={'class': 'form-select'}),
            'visit_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'corrective_action': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'follow_up_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
        labels = {
            'establishment': 'المنشأة',
            'visit_date': 'تاريخ التقييم',
            'notes': 'ملاحظات عامة',
            'corrective_action': 'الإجراءات التصحيحية العامة',
            'follow_up_date': 'تاريخ المتابعة',
        }


class EvaluationHeaderForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['establishment'].queryset = (
            Establishment.objects
            .only('id', 'establishment_no', 'commercial_name')
            .order_by('establishment_no', 'commercial_name')
        )
        self.fields['establishment'].label_from_instance = lambda obj: f'{obj.establishment_no} - {obj.commercial_name}'
        if not self.instance.pk or not self.instance.visit_date:
            self.fields['visit_date'].initial = timezone.localdate()

    class Meta:
        model = Evaluation
        fields = ['establishment', 'visit_date', 'notes']
        widgets = {
            'establishment': forms.Select(attrs={'class': 'form-select'}),
            'visit_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'أدخل الملاحظات العامة للتقييم'}),
        }
        labels = {
            'establishment': 'المنشأة',
            'visit_date': 'تاريخ التقييم',
            'notes': 'ملاحظات عامة',
        }


class EvaluationItemForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].choices = [
            ('compliant', 'مستوفي'),
            ('non_compliant', 'غير مستوفي'),
            ('na', 'لا ينطبق'),
            ('observation', 'ملاحظة'),
        ]

    class Meta:
        model = EvaluationItem
        fields = ['status', 'remarks', 'corrective_action']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select form-select-sm result-select'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control form-control-sm remark-field', 'rows': 2, 'placeholder': 'أدخل الملاحظات عند اختيار غير مستوفي'}),
            'corrective_action': forms.Textarea(attrs={'class': 'form-control form-control-sm corrective-action-field', 'rows': 2, 'placeholder': 'أدخل الإجراء التصحيحي المطلوب لهذا البند'}),
        }


class EvaluationRecordCheckForm(forms.ModelForm):
    class Meta:
        model = EvaluationRecordCheck
        fields = ['is_available', 'remarks']
        widgets = {
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input record-availability'}),
            'remarks': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'ملاحظات السجل'}),
        }


class EvaluationTeamMemberForm(forms.ModelForm):
    class Meta:
        model = EvaluationTeamMember
        fields = ['full_name', 'job_title']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم عضو فريق التقييم'}),
            'job_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'المسمى الوظيفي'}),
        }
        labels = {
            'full_name': 'الاسم',
            'job_title': 'المسمى الوظيفي',
        }


class CorrectiveActionForm(forms.ModelForm):
    class Meta:
        model = CorrectiveActionLog
        fields = ['evaluation', 'criterion', 'title', 'details', 'assigned_to', 'due_date', 'status']
        widgets = {
            'evaluation': forms.Select(attrs={'class': 'form-select'}),
            'criterion': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'assigned_to': forms.TextInput(attrs={'class': 'form-control'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'evaluation': 'التقييم',
            'criterion': 'البند',
            'title': 'عنوان الإجراء',
            'details': 'تفاصيل الإجراء',
            'assigned_to': 'مكلّف بالتنفيذ',
            'due_date': 'تاريخ الاستحقاق',
            'status': 'حالة الإجراء',
        }


class QualificationFollowUpForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['establishment'].queryset = (
            Establishment.objects
            .select_related('governorate')
            .only('id', 'establishment_no', 'commercial_name', 'activity_type', 'governorate__name_ar')
            .order_by('establishment_no', 'commercial_name')
        )
        self.fields['establishment'].label_from_instance = lambda obj: f'{obj.establishment_no} - {obj.commercial_name}'

    class Meta:
        model = QualificationFollowUp
        fields = [
            'establishment', 'governorate', 'establishment_name', 'activity_type',
            'current_status', 'quality_system', 'custom_quality_system',
            'start_date', 'expected_completion_date', 'progress_percent',
            'challenges', 'notes',
        ]
        widgets = {
            'establishment': forms.Select(attrs={'class': 'form-select', 'data-autofill': 'qualification-establishment'}),
            'governorate': forms.TextInput(attrs={'class': 'form-control', 'list': 'governorate-options'}),
            'establishment_name': forms.TextInput(attrs={'class': 'form-control'}),
            'activity_type': forms.TextInput(attrs={'class': 'form-control', 'list': 'qualification-activity-options'}),
            'current_status': forms.Select(attrs={'class': 'form-select'}),
            'quality_system': forms.Select(attrs={'class': 'form-select'}),
            'custom_quality_system': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اكتب النظام إذا اخترت أخرى'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'expected_completion_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'progress_percent': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100'}),
            'challenges': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'establishment': 'المنشأة المسجلة',
            'governorate': 'المحافظة',
            'establishment_name': 'اسم المنشأة',
            'activity_type': 'نوع النشاط',
            'current_status': 'الحالة الحالية',
            'quality_system': 'أنظمة الجودة وسلامة الغذاء',
            'custom_quality_system': 'نظام جودة آخر',
            'start_date': 'تاريخ البدء',
            'expected_completion_date': 'تاريخ الإنجاز المتوقع',
            'progress_percent': 'نسبة الإنجاز (%)',
            'challenges': 'التحديات',
            'notes': 'ملاحظات',
        }
