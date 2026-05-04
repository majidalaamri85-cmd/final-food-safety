from .forms import HACCPFileForm
from .models import HACCPFile
# تفاصيل منشأة
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

def establishment_detail(request, pk):
    establishment = get_object_or_404(Establishment, pk=pk)
    qualification = getattr(establishment.qualification_followups.first(), 'current_status', None)
    haccp_files = establishment.haccp_files.all()
    if request.method == 'POST':
        form = HACCPFileForm(request.POST, request.FILES)
        if form.is_valid():
            haccp_file = form.save(commit=False)
            haccp_file.establishment = establishment
            haccp_file.save()
            messages.success(request, 'تم رفع الملف بنجاح')
            return redirect('establishment_detail', pk=pk)
    else:
        form = HACCPFileForm()
    return render(request, 'inspections/establishment_detail.html', {
        'establishment': establishment,
        'qualification': qualification,
        'haccp_files': haccp_files,
        'form': form,
    })
import os
import hashlib
import tempfile
from collections import OrderedDict
from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles import finders
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Avg, Count, OuterRef, Prefetch, Q, Subquery
from django.forms import modelformset_factory
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from openpyxl import Workbook
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from xhtml2pdf import files as pisa_files
from xhtml2pdf import pisa

from .evaluation_template_data import READY_CORRECTIVE_ACTIONS_BY_CODE
from .forms import (
    CorrectiveActionForm,
    EstablishmentForm,
    EvaluationForm,
    EvaluationHeaderForm,
    EvaluationItemForm,
    EvaluationRecordCheckForm,
    EvaluationTeamMemberForm,
    QualificationFollowUpForm,
)
from .models import (
    CorrectiveActionLog,
    Criterion,
    Establishment,
    Evaluation,
    EvaluationActivityLog,
    EvaluationImage,
    EvaluationItem,
    EvaluationRecordCheck,
    EvaluationSection,
    EvaluationTeamMember,
    Governorate,
    QualificationFollowUp,
    RequiredRecord,
    UserProfile,
    Wilayat,
)

PAGE_SIZE = 25

REFERENCE_DATA_CACHE_KEY = 'inspection_reference_data_v1'
REFERENCE_DATA_CACHE_TIMEOUT = 60 * 30
DASHBOARD_CACHE_TIMEOUT = 60

_ARABIC_TO_LATIN_DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')


def _normalize_digit_text(value):
    if not value:
        return ''
    return str(value).translate(str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789'))


def _normalize_criterion_code(code):
    return str(code or '').translate(_ARABIC_TO_LATIN_DIGITS).strip()


def _get_ready_corrective_action_text(criterion_code):
    normalized_code = _normalize_criterion_code(criterion_code)
    return READY_CORRECTIVE_ACTIONS_BY_CODE.get(normalized_code, '')


def _get_profile(user):
    """إرجاع UserProfile للمستخدم أو None إن لم يوجد."""
    try:
        return user.userprofile
    except UserProfile.DoesNotExist:
        return None


def _get_reference_data():
    reference_data = cache.get(REFERENCE_DATA_CACHE_KEY)
    if reference_data is None:
        reference_data = {
            'governorates': list(
                Governorate.objects.order_by('name_ar').values('id', 'name_ar')
            ),
            'wilayats': list(
                Wilayat.objects.order_by('governorate__name_ar', 'name_ar').values(
                    'id', 'name_ar', 'governorate_id'
                )
            ),
        }
        cache.set(REFERENCE_DATA_CACHE_KEY, reference_data, REFERENCE_DATA_CACHE_TIMEOUT)
    return reference_data


def _get_activity_options(qs):
    return list(
        qs.exclude(activity_type='')
        .order_by('activity_type')
        .values_list('activity_type', flat=True)
        .distinct()
    )


def _build_dashboard_cache_key(user_id, governorate_id, wilayat_id, classification, approval_status, date_from, date_to):
    raw = '|'.join([
        str(user_id),
        governorate_id,
        wilayat_id,
        classification,
        approval_status,
        date_from,
        date_to,
    ])
    digest = hashlib.md5(raw.encode('utf-8')).hexdigest()
    return f'dashboard_ctx:{digest}'


def _apply_rbac(qs_establishments, qs_evaluations, profile):
    """
    تطبيق قيود الوصول المبنية على الدور:
    - admin / central / reviewer: يرون كل شيء
    - manager: يرون محافظتهم فقط
    - inspector: يرون كل المنشآت، لكن تقييماتهم فقط
    """
    if profile is None:
        return qs_establishments, qs_evaluations

    role = profile.role
    if role == 'manager' and profile.governorate_id:
        if qs_establishments is not None:
            qs_establishments = qs_establishments.filter(governorate=profile.governorate)
        if qs_evaluations is not None:
            qs_evaluations = qs_evaluations.filter(establishment__governorate=profile.governorate)
    elif role == 'inspector':
        if qs_evaluations is not None:
            qs_evaluations = qs_evaluations.filter(inspector=profile.user)

    return qs_establishments, qs_evaluations


def _build_default_corrective_action(item):
    criterion_code = item.criterion.code
    ready_text = _get_ready_corrective_action_text(criterion_code)
    if ready_text:
        return ready_text

    criterion_text = (item.criterion.text_ar or '').strip()
    risk_text = item.criterion.get_risk_level_display()
    risk_level = item.criterion.risk_level

    if risk_level == 'critical':
        timeline = 'خلال 24 ساعة'
        step_two = 'تنفيذ إجراء احتواء فوري وإيقاف الممارسة الخطرة حتى تصحيحها بالكامل.'
        step_three = 'التحقق الموقعي من الفاعلية خلال 24-48 ساعة مع اعتماد المراجع الفني.'
    elif risk_level == 'high':
        timeline = 'خلال 3 أيام'
        step_two = 'تنفيذ إجراء تصحيحي عاجل يمنع تكرار عدم الاستيفاء.'
        step_three = 'التحقق من الفاعلية خلال 3-5 أيام وتوثيق نتائج المتابعة.'
    elif risk_level == 'medium':
        timeline = 'خلال 7 أيام'
        step_two = 'تنفيذ الإجراء التصحيحي وفق خطة عمل محددة بالمسؤوليات.'
        step_three = 'التحقق من الفاعلية خلال 7-10 أيام وتحديث السجلات.'
    else:
        timeline = 'خلال 14 يومًا'
        step_two = 'تنفيذ تحسين تشغيلي ومعالجة سبب عدم الاستيفاء.'
        step_three = 'التحقق الدوري من الفاعلية وتوثيق الإغلاق النهائي.'

    return (
        f'1) معالجة عدم الاستيفاء في البند {criterion_code} ({criterion_text}) وإزالة السبب الجذري.\n'
        f'2) {step_two}\n'
        f'3) {step_three}\n'
        f'4) تاريخ الإغلاق المستهدف: {timeline}.\n'
        f'مستوى الخطورة: {risk_text}.'
    )


def _sync_corrective_actions_for_evaluation(evaluation, user, pre_loaded_items=None):
    if pre_loaded_items is not None:
        items = pre_loaded_items
    else:
        items = list(
            EvaluationItem.objects.filter(evaluation=evaluation)
            .select_related('criterion')
        )
    existing_logs = {
        log.criterion_id: log
        for log in CorrectiveActionLog.objects.filter(evaluation=evaluation, criterion__isnull=False)
    }

    active_criterion_ids = set()
    for item in items:
        has_corrective_action = bool((item.corrective_action or '').strip())
        if item.status != 'non_compliant' or not has_corrective_action:
            continue

        active_criterion_ids.add(item.criterion_id)
        title = f'إجراء تصحيحي للبند {item.criterion.code}'
        details = item.corrective_action.strip()
        log = existing_logs.get(item.criterion_id)

        if log is None:
            CorrectiveActionLog.objects.create(
                evaluation=evaluation,
                criterion=item.criterion,
                created_by=user,
                title=title,
                details=details,
                assigned_to='يحدد لاحقاً',
                status='open',
            )
            continue

        updated_fields = []
        if log.title != title:
            log.title = title
            updated_fields.append('title')
        if log.details != details:
            log.details = details
            updated_fields.append('details')
        if not log.assigned_to:
            log.assigned_to = 'يحدد لاحقاً'
            updated_fields.append('assigned_to')
        if updated_fields:
            log.save(update_fields=updated_fields)

    stale_logs = [
        log.pk for criterion_id, log in existing_logs.items()
        if criterion_id not in active_criterion_ids and log.status == 'open'
    ]
    if stale_logs:
        CorrectiveActionLog.objects.filter(pk__in=stale_logs).delete()


ISIC4_FOOD_ACTIVITIES = [
    ('1010', 'تجهيز وحفظ اللحوم'),
    ('1020', 'تجهيز وحفظ الأسماك والقشريات والرخويات'),
    ('1030', 'تجهيز وحفظ الفواكه والخضروات'),
    ('1040', 'صناعة الزيوت والدهون النباتية والحيوانية'),
    ('1050', 'صناعة منتجات الألبان'),
    ('1061', 'صناعة منتجات مطاحن الحبوب'),
    ('1062', 'صناعة النشا ومنتجاته'),
    ('1071', 'صناعة منتجات المخابز'),
    ('1072', 'صناعة السكر'),
    ('1073', 'صناعة الكاكاو والشوكولاتة والحلويات السكرية'),
    ('1074', 'صناعة المعكرونة والشعيرية والكسكس ومنتجات النشا المماثلة'),
    ('1075', 'صناعة الوجبات والأطباق الجاهزة'),
    ('1079', 'صناعة منتجات غذائية أخرى غير مصنفة في موضع آخر'),
    ('1080', 'صناعة الأعلاف الحيوانية المحضرة'),
    ('1101', 'تقطير ومزج المشروبات الروحية'),
    ('1102', 'صناعة النبيذ'),
    ('1103', 'صناعة مشروبات الشعير والملت'),
    ('1104', 'صناعة المشروبات الغازية وإنتاج المياه المعدنية والمياه المعبأة الأخرى'),
]


def home(request):
    return render(request, 'inspections/home.html', {'minimal_nav': True})


def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    next_url = (request.GET.get('next') or request.POST.get('next') or '').strip()

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect('dashboard')

        messages.error(request, 'اسم المستخدم أو كلمة السر غير صحيحة.')

    context = {
        'minimal_nav': True,
        'next': next_url,
    }
    return render(request, 'inspections/login.html', context)


@login_required
def user_logout(request):
    logout(request)
    return redirect('home')


def external_establishments_approval(request):
    context = {
        'module_title': 'اعتماد المنشآت الخارجية',
        'module_description': 'هذه الوحدة ستكون متاحة قريباً.',
        'minimal_nav': True,
    }
    return render(request, 'inspections/module_placeholder.html', context)


def conformity_assessment_bodies_assignment(request):
    context = {
        'module_title': 'تعيين جهات تقويم المطابقة',
        'module_description': 'هذه الوحدة ستكون متاحة قريباً.',
        'minimal_nav': True,
    }
    return render(request, 'inspections/module_placeholder.html', context)


@login_required
def qualification_followup_list(request):
    qs = QualificationFollowUp.objects.select_related('establishment').all()

    q = request.GET.get('q', '').strip()
    governorate = request.GET.get('governorate', '').strip()
    status = request.GET.get('status', '').strip()
    activity = request.GET.get('activity', '').strip()

    if q:
        normalized_q = _normalize_digit_text(q)
        filters = (
            Q(establishment_name__icontains=q) |
            Q(activity_type__icontains=q) |
            Q(governorate__icontains=q) |
            Q(establishment__license_no__icontains=q)
        )
        if normalized_q.isdigit():
            filters |= Q(establishment__establishment_no=int(normalized_q))
        qs = qs.filter(filters)
    if governorate:
        qs = qs.filter(governorate=governorate)
    if status:
        qs = qs.filter(current_status=status)
    if activity:
        qs = qs.filter(activity_type=activity)

    if request.method == 'POST':
        form = QualificationFollowUpForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f'تم حفظ متابعة التأهيل للمنشأة: {obj.establishment_name}')
            return redirect('qualification_followup_list')
    else:
        form = QualificationFollowUpForm()

    today = timezone.localdate()
    stats = qs.aggregate(total=Count('id'), avg_progress=Avg('progress_percent'))
    total_count = stats['total'] or 0
    completed_count = qs.filter(current_status='completed').count()
    in_progress_count = qs.filter(current_status='in_progress').count()
    stalled_count = qs.filter(current_status='stalled').count()
    overdue_count = qs.filter(expected_completion_date__lt=today).exclude(current_status='completed').count()
    avg_progress = round(stats['avg_progress'] or 0, 1)

    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))
    reference_data = _get_reference_data()
    activity_options = (
        QualificationFollowUp.objects
        .exclude(activity_type='')
        .order_by('activity_type')
        .values_list('activity_type', flat=True)
        .distinct()
    )
    establishment_options = Establishment.objects.select_related('governorate').only(
        'id', 'establishment_no', 'commercial_name', 'activity_type', 'governorate__name_ar'
    ).order_by('establishment_no', 'commercial_name')

    return render(request, 'inspections/qualification_followup_list.html', {
        'form': form,
        'items': page_obj,
        'page_obj': page_obj,
        'q': q,
        'governorates': reference_data['governorates'],
        'selected_governorate': governorate,
        'selected_status': status,
        'selected_activity': activity,
        'status_choices': QualificationFollowUp.STATUS_CHOICES,
        'activity_options': activity_options,
        'total_count': total_count,
        'completed_count': completed_count,
        'in_progress_count': in_progress_count,
        'stalled_count': stalled_count,
        'overdue_count': overdue_count,
        'avg_progress': avg_progress,
        'establishment_options': establishment_options,
    })


@login_required
def dashboard(request):
    profile = _get_profile(request.user)

    governorate_id = request.GET.get('governorate', '').strip()
    wilayat_id = request.GET.get('wilayat', '').strip()
    classification = request.GET.get('classification', '').strip()
    approval_status = request.GET.get('approval_status', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    cache_key = _build_dashboard_cache_key(
        request.user.id,
        governorate_id,
        wilayat_id,
        classification,
        approval_status,
        date_from,
        date_to,
    )
    cached_context = cache.get(cache_key)
    if cached_context is not None:
        return render(request, 'inspections/dashboard.html', cached_context)

    establishments_qs = Establishment.objects.all()
    evaluations_qs = Evaluation.objects.select_related('establishment')
    establishments_qs, evaluations_qs = _apply_rbac(establishments_qs, evaluations_qs, profile)

    if governorate_id:
        establishments_qs = establishments_qs.filter(governorate_id=governorate_id)
        evaluations_qs = evaluations_qs.filter(establishment__governorate_id=governorate_id)
    if wilayat_id:
        establishments_qs = establishments_qs.filter(wilayat_id=wilayat_id)
        evaluations_qs = evaluations_qs.filter(establishment__wilayat_id=wilayat_id)
    if classification:
        evaluations_qs = evaluations_qs.filter(classification=classification)
    if approval_status:
        evaluations_qs = evaluations_qs.filter(approval_status=approval_status)
    if date_from:
        evaluations_qs = evaluations_qs.filter(visit_date__gte=date_from)
    if date_to:
        evaluations_qs = evaluations_qs.filter(visit_date__lte=date_to)

    total_establishments = establishments_qs.count()
    total_evaluations = evaluations_qs.count()
    completed_evaluations = evaluations_qs.filter(approval_status='completed').count()
    open_actions = CorrectiveActionLog.objects.exclude(status='closed').filter(evaluation__in=evaluations_qs).count()
    non_compliant_items = EvaluationItem.objects.filter(status='non_compliant', evaluation__in=evaluations_qs).count()
    avg_percentage = evaluations_qs.aggregate(avg=Avg('percentage'))['avg'] or 0

    by_governorate = list(
        establishments_qs.values('governorate__name_ar')
        .annotate(total=Count('id'))
        .order_by('governorate__name_ar')
    )
    recent_evaluations = list(
        evaluations_qs.only(
            'id',
            'visit_date',
            'percentage',
            'approval_status',
            'establishment__commercial_name',
        )
        .order_by('-visit_date', '-created_at')[:10]
    )
    classification_summary = list(
        evaluations_qs.values('classification').annotate(total=Count('id')).order_by('-total')
    )
    weakest_evaluations = list(
        evaluations_qs.only(
            'id',
            'visit_date',
            'percentage',
            'classification',
            'establishment__commercial_name',
        )
        .order_by('percentage', '-visit_date', '-created_at')[:5]
    )
    establishment_growth = list(
        establishments_qs.values('governorate__name_ar')
        .annotate(
            active_total=Count('id', filter=Q(status='active')),
            total=Count('id'),
        )
        .order_by('-total')[:6]
    )

    classification_labels = dict(Evaluation.CLASSIFICATION_CHOICES)
    for row in classification_summary:
        row['label'] = classification_labels.get(row['classification'], row['classification'])
        row['pct'] = round((row['total'] / total_evaluations) * 100, 1) if total_evaluations else 0

    for row in establishment_growth:
        row['active_pct'] = round((row['active_total'] / row['total']) * 100, 1) if row['total'] else 0

    STATUS_META = {
        'excellent': {'label': 'ممتاز', 'range': '86%-100%', 'description': 'مستوفي للحصول على شهادة ضبط الجودة', 'color': 'success', 'icon': 'fa-star', 'order': 1},
        'good': {'label': 'جيد', 'range': '70%-85%', 'description': 'مستوفي مع وجود فرص للتحسين', 'color': 'info', 'icon': 'fa-thumbs-up', 'order': 2},
        'acceptable': {'label': 'مقبول', 'range': '41%-69%', 'description': 'يحتاج تأهيل ومزيد من التحسين', 'color': 'warning', 'icon': 'fa-triangle-exclamation', 'order': 3},
        'weak': {'label': 'ضعيف', 'range': '0%-40%', 'description': 'إيقاف الإنتاج', 'color': 'danger', 'icon': 'fa-circle-xmark', 'order': 4},
    }

    latest_eval_subq = evaluations_qs.filter(
        establishment=OuterRef('pk')
    ).order_by('-visit_date', '-created_at')
    establishments_with_latest = establishments_qs.annotate(
        latest_cls=Subquery(latest_eval_subq.values('classification')[:1])
    )
    counted = {
        row['latest_cls']: row['total']
        for row in establishments_with_latest.values('latest_cls').annotate(total=Count('id')).order_by()
        if row['latest_cls']
    }
    no_eval_count = establishments_with_latest.filter(latest_cls__isnull=True).count()
    establishment_status_summary = []
    for key, meta in sorted(STATUS_META.items(), key=lambda x: x[1]['order']):
        count = counted.get(key, 0)
        establishment_status_summary.append({
            **meta,
            'key': key,
            'count': count,
            'pct': round((count / total_establishments) * 100, 1) if total_establishments else 0,
        })

    reference_data = _get_reference_data()

    context = {
        'total_establishments': total_establishments,
        'total_evaluations': total_evaluations,
        'completed_evaluations': completed_evaluations,
        'open_actions': open_actions,
        'non_compliant_items': non_compliant_items,
        'by_governorate': by_governorate,
        'recent_evaluations': recent_evaluations,
        'avg_percentage': round(avg_percentage, 2),
        'classification_summary': classification_summary,
        'weakest_evaluations': weakest_evaluations,
        'establishment_growth': establishment_growth,
        'establishment_status_summary': establishment_status_summary,
        'no_eval_count': no_eval_count,
        'governorates': reference_data['governorates'],
        'wilayats': reference_data['wilayats'],
        'selected_governorate': governorate_id,
        'selected_wilayat': wilayat_id,
        'selected_classification': classification,
        'selected_approval_status': approval_status,
        'date_from': date_from,
        'date_to': date_to,
        'classification_choices': Evaluation.CLASSIFICATION_CHOICES,
        'approval_status_choices': Evaluation.APPROVAL_STATUS_CHOICES,
    }

    cache.set(cache_key, context, DASHBOARD_CACHE_TIMEOUT)

    return render(request, 'inspections/dashboard.html', context)


@login_required
def establishment_list(request):
    profile = _get_profile(request.user)
    qs = (
        Establishment.objects.select_related('governorate', 'wilayat')
        .only(
            'id',
            'establishment_no',
            'commercial_name',
            'activity_type',
            'license_no',
            'direct_location_url',
            'status',
            'governorate__name_ar',
            'wilayat__name_ar',
        )
        .order_by('commercial_name', 'id')
    )
    qs, _ = _apply_rbac(qs, None, profile)
    activity_options = _get_activity_options(qs)

    q = request.GET.get('q', '').strip()
    normalized_q = _normalize_digit_text(q)
    governorate_id = request.GET.get('governorate', '').strip()
    wilayat_id = request.GET.get('wilayat', '').strip()
    activity = request.GET.get('activity', '').strip()
    if q:
        filters = (
            Q(commercial_name__icontains=q) |
            Q(activity_type__icontains=q) |
            Q(license_no__icontains=q) |
            Q(commercial_reg__icontains=q)
        )
        if normalized_q.isdigit():
            filters |= Q(establishment_no=int(normalized_q))
        qs = qs.filter(filters)
    if governorate_id:
        qs = qs.filter(governorate_id=governorate_id)
    if wilayat_id:
        qs = qs.filter(wilayat_id=wilayat_id)
    if activity:
        qs = qs.filter(activity_type=activity)
    reference_data = _get_reference_data()

    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'inspections/establishment_list.html', {
        'establishments': page_obj,
        'page_obj': page_obj,
        'q': q,
        'governorates': reference_data['governorates'],
        'wilayats': reference_data['wilayats'],
        'activity_options': activity_options,
        'selected_governorate': governorate_id,
        'selected_wilayat': wilayat_id,
        'selected_activity': activity,
    })


@login_required
def establishment_create(request):
    form = EstablishmentForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        obj = form.save()
        messages.success(request, f'تم حفظ المنشأة بنجاح. رقم المنشأة: {obj.establishment_no}')
        return redirect('establishment_list')
    reference_data = _get_reference_data()
    return render(request, 'inspections/establishment_form.html', {
        'form': form,
        'title': 'إضافة منشأة',
        'wilayats': reference_data['wilayats'],
        'isic_activities': ISIC4_FOOD_ACTIVITIES,
    })


@login_required
def evaluation_list(request):
    profile = _get_profile(request.user)
    qs = (
        Evaluation.objects.select_related(
            'establishment',
            'establishment__governorate',
            'establishment__wilayat',
        )
        .only(
            'id',
            'visit_date',
            'classification',
            'approval_status',
            'establishment__commercial_name',
            'establishment__activity_type',
            'establishment__license_no',
            'establishment__establishment_no',
            'establishment__commercial_reg',
            'establishment__governorate__name_ar',
            'establishment__wilayat__name_ar',
        )
        .order_by('-visit_date', '-created_at')
    )
    _, qs = _apply_rbac(None, qs, profile)
    activity_options = _get_activity_options(
        Establishment.objects.filter(evaluations__in=qs).distinct()
    )

    governorate_id = request.GET.get('governorate', '').strip()
    wilayat_id = request.GET.get('wilayat', '').strip()
    classification = request.GET.get('classification', '').strip()
    activity = request.GET.get('activity', '').strip()
    q = request.GET.get('q', '').strip()
    normalized_q = _normalize_digit_text(q)

    if governorate_id:
        qs = qs.filter(establishment__governorate_id=governorate_id)
    if wilayat_id:
        qs = qs.filter(establishment__wilayat_id=wilayat_id)
    if classification:
        qs = qs.filter(classification=classification)
    if activity:
        qs = qs.filter(establishment__activity_type=activity)
    if q:
        filters = (
            Q(establishment__commercial_name__icontains=q) |
            Q(establishment__activity_type__icontains=q) |
            Q(establishment__license_no__icontains=q) |
            Q(establishment__commercial_reg__icontains=q)
        )
        if normalized_q.isdigit():
            filters |= Q(establishment__establishment_no=int(normalized_q))
        qs = qs.filter(filters)

    reference_data = _get_reference_data()
    classification_choices = Evaluation.CLASSIFICATION_CHOICES

    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'inspections/evaluation_list.html', {
        'evaluations': page_obj,
        'page_obj': page_obj,
        'governorates': [
            {'governorate__id': governorate['id'], 'governorate__name_ar': governorate['name_ar']}
            for governorate in reference_data['governorates']
        ],
        'wilayats': [
            {
                'wilayat__id': wilayat['id'],
                'wilayat__name_ar': wilayat['name_ar'],
                'governorate__id': wilayat['governorate_id'],
            }
            for wilayat in reference_data['wilayats']
        ],
        'classification_choices': classification_choices,
        'activity_options': activity_options,
        'selected_governorate': governorate_id,
        'selected_wilayat': wilayat_id,
        'selected_classification': classification,
        'selected_activity': activity,
        'q': q,
    })


def create_evaluation_items(evaluation):
    criteria = Criterion.objects.filter(is_active=True).select_related('section').order_by('section__sort_order', 'code')
    for criterion in criteria:
        EvaluationItem.objects.get_or_create(
            evaluation=evaluation,
            criterion=criterion,
            defaults={'status': 'compliant'}
        )

    records = RequiredRecord.objects.filter(is_active=True).order_by('name_ar')
    for record in records:
        EvaluationRecordCheck.objects.get_or_create(
            evaluation=evaluation,
            record=record,
        )


@login_required
def evaluation_create(request):
    profile = _get_profile(request.user)
    establishments_qs = Establishment.objects.all()
    establishments_qs, _ = _apply_rbac(establishments_qs, None, profile)
    default_establishment = establishments_qs.order_by('commercial_name', 'id').first()

    if not default_establishment:
        messages.error(request, 'لا توجد منشآت متاحة لإنشاء تقييم. يرجى إضافة منشأة أولاً.')
        return redirect('establishment_create')

    obj = Evaluation.objects.create(
        establishment=default_establishment,
        inspector=request.user,
        visit_date=timezone.localdate(),
    )
    create_evaluation_items(obj)
    EvaluationActivityLog.objects.create(
        evaluation=obj,
        user=request.user,
        action='إنشاء تقييم',
        notes='تم إنشاء مسودة تقييم وفتح صفحة البنود مباشرة.',
    )
    messages.success(request, 'تم فتح تقييم جديد. يمكنك الآن اختيار المنشأة والتاريخ وإكمال البنود في نفس الصفحة.')
    return redirect('evaluation_update', pk=obj.pk)


@login_required
def evaluation_update(request, pk):
    profile = _get_profile(request.user)
    evaluation = get_object_or_404(
        Evaluation.objects.select_related('establishment', 'inspector', 'reviewer').prefetch_related('team_members'),
        pk=pk,
    )

    # المفتش لا يستطيع تعديل تقييمات الآخرين
    if profile and profile.role == 'inspector' and evaluation.inspector != request.user:
        messages.error(request, 'ليس لديك صلاحية لتعديل هذا التقييم.')
        return redirect('evaluation_list')

    queryset = EvaluationItem.objects.filter(
        evaluation=evaluation
    ).select_related(
        'criterion', 'criterion__section'
    ).order_by(
        'criterion__section__sort_order', 'criterion__sort_order', 'id'
    )

    EvaluationItemFormSet = modelformset_factory(
        EvaluationItem,
        form=EvaluationItemForm,
        extra=0,
        can_delete=False,
    )
    EvaluationRecordFormSet = modelformset_factory(
        EvaluationRecordCheck,
        form=EvaluationRecordCheckForm,
        extra=0,
        can_delete=False,
    )
    EvaluationTeamMemberFormSet = modelformset_factory(
        EvaluationTeamMember,
        form=EvaluationTeamMemberForm,
        extra=1,
        can_delete=True,
    )
    record_queryset = EvaluationRecordCheck.objects.filter(
        evaluation=evaluation
    ).select_related('record').order_by('record__name_ar', 'id')
    team_queryset = EvaluationTeamMember.objects.filter(
        evaluation=evaluation
    ).order_by('sort_order', 'id')
    meta_form = EvaluationHeaderForm(request.POST or None, instance=evaluation, prefix='meta')

    if request.method == 'POST':
        formset = EvaluationItemFormSet(request.POST, queryset=queryset)
        record_formset = EvaluationRecordFormSet(request.POST, queryset=record_queryset, prefix='records')
        team_formset = EvaluationTeamMemberFormSet(request.POST, queryset=team_queryset, prefix='team')
        if meta_form.is_valid() and formset.is_valid() and record_formset.is_valid() and team_formset.is_valid():
            from django.db import transaction as _tx
            with _tx.atomic():
                meta_form.save()
                formset.save()
                record_formset.save()
                team_members = team_formset.save(commit=False)
                for deleted_member in team_formset.deleted_objects:
                    deleted_member.delete()
                for index, member in enumerate(team_members, start=1):
                    member.evaluation = evaluation
                    member.sort_order = index
                    member.save()

                # استخدام البيانات الموجودة في الذاكرة بدل إعادة الجلب من DB
                all_items = [f.instance for f in formset.forms if f.instance.pk]
                all_records = [f.instance for f in record_formset.forms if f.instance.pk]

                for item in all_items:
                    if item.status == 'non_compliant' and not (item.corrective_action or '').strip():
                        item.corrective_action = _build_default_corrective_action(item)
                        item.save(update_fields=['corrective_action'])

                # معالجة الصور لجميع البنود (وليس فقط المعدّلة)
                for form in formset.forms:
                    form_item = form.instance
                    if not form_item.pk:
                        continue
                    image_field = request.FILES.get(f'image_{form_item.id}')
                    caption = request.POST.get(f'caption_{form_item.id}', '').strip()
                    if image_field:
                        EvaluationImage.objects.create(
                            evaluation=evaluation,
                            criterion=form_item.criterion,
                            image=image_field,
                            caption=caption,
                        )

                # تمرير البيانات الموجودة في الذاكرة لتجنب استعلامات DB إضافية
                _sync_corrective_actions_for_evaluation(evaluation, request.user, pre_loaded_items=all_items)
                evaluation.calculate_results(items=all_items, record_checks=all_records)
                evaluation.approval_status = 'completed'
                evaluation.save(update_fields=['total_points', 'percentage', 'classification', 'approval_status'])
                EvaluationActivityLog.objects.create(evaluation=evaluation, user=request.user, action='إنهاء التقييم', notes='تم حفظ بنود التقييم وإنهاء التقييم.')

                # محرك التأهيل الذكي وربط البنود غير المستوفية وخطة HACCP
                from inspections.models import QualificationFollowUp, HACCPFile
                pct = float(evaluation.percentage)
                if pct >= 86:
                    qual_status = 'qualified'
                elif pct >= 70:
                    qual_status = 'conditionally_qualified'
                elif pct >= 41:
                    qual_status = 'in_progress'
                else:
                    qual_status = 'not_qualified'

                qf, created = QualificationFollowUp.objects.get_or_create(
                    establishment=evaluation.establishment,
                    defaults={
                        'governorate': evaluation.establishment.governorate.name_ar,
                        'establishment_name': evaluation.establishment.commercial_name,
                        'activity_type': evaluation.establishment.activity_type,
                        'current_status': qual_status,
                        'evaluation': evaluation,
                    }
                )
                if not created:
                    qf.current_status = qual_status
                    qf.evaluation = evaluation
                    qf.save(update_fields=['current_status', 'evaluation'])

                # إنشاء خطة تأهيل تلقائية للبنود غير المستوفية
                for item in all_items:
                    if item.status == 'non_compliant':
                        # ربط كل بند غير مستوفي بخطة التأهيل
                        # إضافة بند إلى خطة HACCP إذا كان البند متعلقاً بها
                        criterion_text = item.criterion.text_ar
                        if 'تتبع' in criterion_text or 'تحليل مخاطر' in criterion_text or 'سجلات' in criterion_text or 'نظافة' in criterion_text:
                            HACCPFile.objects.get_or_create(
                                establishment=evaluation.establishment,
                                file_type='prps' if 'نظافة' in criterion_text else (
                                    'traceability' if 'تتبع' in criterion_text else (
                                        'records' if 'سجلات' in criterion_text else 'hazard_analysis'
                                    )
                                ),
                                title=criterion_text,
                                defaults={
                                    'notes': f'تم إنشاؤه تلقائيًا بناءً على بند غير مستوفي في التقييم رقم {evaluation.pk}',
                                }
                            )

            # مسح كاش PDF بعد الحفظ حتى لا يُعرض تقرير قديم
            cache.delete(f'pdf_bytes:eval:{evaluation.pk}')
            messages.success(request, f'تم حفظ وإنهاء التقييم بنجاح. النسبة: {evaluation.percentage}% - التصنيف: {evaluation.get_classification_display()}')
            return redirect('evaluation_update', pk=evaluation.pk)
    else:
        formset = EvaluationItemFormSet(queryset=queryset)
        record_formset = EvaluationRecordFormSet(queryset=record_queryset, prefix='records')
        team_formset = EvaluationTeamMemberFormSet(queryset=team_queryset, prefix='team')

    grouped_forms = OrderedDict()
    status_counts = {
        row['status']: row['total']
        for row in queryset.values('status').annotate(total=Count('id'))
    }
    non_compliant_count = status_counts.get('non_compliant', 0)
    compliant_count = status_counts.get('compliant', 0)
    has_evaluation_result = EvaluationActivityLog.objects.filter(
        evaluation=evaluation,
        action__in=['حفظ التقييم', 'إنهاء التقييم'],
    ).exists()
    high_risk_non_compliant = list(
        queryset.filter(
            status='non_compliant',
            criterion__risk_level__in=['high', 'critical'],
        ).values_list('criterion__code', flat=True)
    )

    image_map = {}
    for image in EvaluationImage.objects.filter(evaluation=evaluation).select_related('criterion').order_by('id'):
        image_map.setdefault(image.criterion_id, []).append(image)

    for form in formset.forms:
        section = form.instance.criterion.section
        grouped_forms.setdefault(section, [])
        grouped_forms[section].append(form)

    signature_rows = [
        {
            'name': getattr(evaluation.inspector, 'get_full_name', lambda: '')() or evaluation.inspector.username,
            'job_title': 'المفتش / المقيم',
        }
    ]
    signature_rows.extend(
        {
            'name': member.full_name,
            'job_title': member.job_title,
        }
        for member in evaluation.team_members.all()
    )
    if evaluation.reviewer:
        signature_rows.append({
            'name': getattr(evaluation.reviewer, 'get_full_name', lambda: '')() or evaluation.reviewer.username,
            'job_title': 'المراجع الفني',
        })
    while len(signature_rows) < 4:
        signature_rows.append({'name': '', 'job_title': ''})

    context = {
        'evaluation': evaluation,
        'meta_form': meta_form,
        'formset': formset,
        'record_formset': record_formset,
        'team_formset': team_formset,
        'grouped_forms': grouped_forms,
        'non_compliant_count': non_compliant_count,
        'compliant_count': compliant_count,
        'has_evaluation_result': has_evaluation_result,
        'high_risk_non_compliant': high_risk_non_compliant,
        'image_map': image_map,
    }
    return render(request, 'inspections/evaluation_update.html', context)


@login_required
def evaluation_submit(request, pk):
    profile = _get_profile(request.user)
    evaluation = get_object_or_404(Evaluation, pk=pk)

    # المفتش لا يستطيع إنهاء تقييمات الآخرين
    if profile and profile.role == 'inspector' and evaluation.inspector != request.user:
        messages.error(request, 'ليس لديك صلاحية لإنهاء هذا التقييم.')
        return redirect('evaluation_list')

    evaluation.mark_completed()
    EvaluationActivityLog.objects.create(evaluation=evaluation, user=request.user, action='إنهاء التقييم')
    messages.success(request, 'تم إنهاء التقييم وحفظه كحالة مكتملة.')
    return redirect('evaluation_list')


@login_required
def corrective_action_list(request):
    qs = (
        CorrectiveActionLog.objects.select_related('evaluation', 'criterion')
        .order_by('-id')
    )
    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(
        request,
        'inspections/corrective_list.html',
        {
            'actions': page_obj,
            'page_obj': page_obj,
        },
    )


@login_required
def corrective_action_create(request):
    form = CorrectiveActionForm(request.POST or None)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.created_by = request.user
        obj.save()
        messages.success(request, 'تم حفظ الإجراء التصحيحي.')
        return redirect('corrective_action_list')
    return render(request, 'inspections/form.html', {'form': form, 'title': 'إضافة إجراء تصحيحي'})


@login_required
def corrective_action_update(request, pk):
    corrective_action = get_object_or_404(CorrectiveActionLog, pk=pk)
    form = CorrectiveActionForm(request.POST or None, instance=corrective_action)
    if form.is_valid():
        form.save()
        messages.success(request, 'تم تحديث الإجراء التصحيحي.')
        return redirect('corrective_action_list')
    return render(request, 'inspections/form.html', {'form': form, 'title': 'تعديل إجراء تصحيحي'})


@login_required
def export_establishments_excel(request):
    profile = _get_profile(request.user)
    qs = Establishment.objects.select_related('governorate', 'wilayat').all()
    qs, _ = _apply_rbac(qs, None, profile)

    governorate_id = request.GET.get('governorate', '').strip()
    wilayat_id = request.GET.get('wilayat', '').strip()
    activity = request.GET.get('activity', '').strip()
    q = request.GET.get('q', '').strip()
    normalized_q = _normalize_digit_text(q)

    if governorate_id:
        qs = qs.filter(governorate_id=governorate_id)
    if wilayat_id:
        qs = qs.filter(wilayat_id=wilayat_id)
    if activity:
        qs = qs.filter(activity_type=activity)
    if q:
        filters = (
            Q(commercial_name__icontains=q) |
            Q(activity_type__icontains=q) |
            Q(license_no__icontains=q) |
            Q(commercial_reg__icontains=q)
        )
        if normalized_q.isdigit():
            filters |= Q(establishment_no=int(normalized_q))
        qs = qs.filter(filters)

    wb = Workbook()
    ws = wb.active
    ws.title = 'المنشآت'
    ws.append(['رقم المنشأة', 'الاسم التجاري', 'النشاط', 'المحافظة', 'الولاية', 'رقم الترخيص', 'السجل التجاري', 'الحالة'])
    for e in qs:
        ws.append([
            e.establishment_no,
            e.commercial_name, e.activity_type, e.governorate.name_ar, e.wilayat.name_ar,
            e.license_no, e.commercial_reg, e.get_status_display()
        ])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="establishments.xlsx"'
    wb.save(response)
    return response


@login_required
def export_qualification_followups_excel(request):
    qs = QualificationFollowUp.objects.select_related('establishment').all()

    q = request.GET.get('q', '').strip()
    governorate = request.GET.get('governorate', '').strip()
    status = request.GET.get('status', '').strip()
    activity = request.GET.get('activity', '').strip()
    if q:
        normalized_q = _normalize_digit_text(q)
        filters = (
            Q(establishment_name__icontains=q) |
            Q(activity_type__icontains=q) |
            Q(governorate__icontains=q) |
            Q(establishment__license_no__icontains=q)
        )
        if normalized_q.isdigit():
            filters |= Q(establishment__establishment_no=int(normalized_q))
        qs = qs.filter(filters)
    if governorate:
        qs = qs.filter(governorate=governorate)
    if status:
        qs = qs.filter(current_status=status)
    if activity:
        qs = qs.filter(activity_type=activity)

    wb = Workbook()
    ws = wb.active
    ws.title = 'متابعة التأهيل'
    ws.append([
        'م', 'المحافظة', 'اسم المنشأة', 'نوع النشاط', 'الحالة الحالية',
        'أنظمة الجودة وسلامة الغذاء', 'تاريخ البدء', 'تاريخ الإنجاز المتوقع',
        'نسبة الإنجاز (%)', 'التحديات', 'ملاحظات', 'رقم المنشأة المرجعي',
        'رقم الزيارة المرجعي', 'سنة الزيارة', 'رقم الزيارة لنفس المنشأة',
        'رمز المحافظة', 'رمز النشاط', 'مفتاح الربط Django',
    ])
    for index, item in enumerate(qs, start=1):
        ws.append([
            index,
            item.governorate,
            item.establishment_name,
            item.activity_type,
            item.get_current_status_display(),
            item.custom_quality_system or item.quality_system,
            item.start_date,
            item.expected_completion_date,
            item.progress_percent,
            item.challenges,
            item.notes,
            item.facility_reference_code,
            item.visit_reference_code,
            item.visit_year,
            item.visit_no,
            item.governorate_code,
            item.activity_code,
            item.django_link_key,
        ])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="qualification_followups.xlsx"'
    wb.save(response)
    return response


@login_required
def export_evaluations_excel(request):
    profile = _get_profile(request.user)
    qs = Evaluation.objects.select_related(
        'establishment', 'establishment__governorate', 'establishment__wilayat', 'inspector'
    ).prefetch_related(
        Prefetch('items', queryset=EvaluationItem.objects.filter(status='non_compliant').select_related('criterion')),
        Prefetch('record_checks', queryset=EvaluationRecordCheck.objects.filter(is_available=False).select_related('record')),
    ).all()
    _, qs = _apply_rbac(None, qs, profile)
    governorate_id = request.GET.get('governorate', '').strip()
    wilayat_id = request.GET.get('wilayat', '').strip()
    classification = request.GET.get('classification', '').strip()
    activity = request.GET.get('activity', '').strip()
    q = request.GET.get('q', '').strip()
    normalized_q = _normalize_digit_text(q)

    if governorate_id:
        qs = qs.filter(establishment__governorate_id=governorate_id)
    if wilayat_id:
        qs = qs.filter(establishment__wilayat_id=wilayat_id)
    if classification:
        qs = qs.filter(classification=classification)
    if activity:
        qs = qs.filter(establishment__activity_type=activity)
    if q:
        filters = (
            Q(establishment__commercial_name__icontains=q) |
            Q(establishment__activity_type__icontains=q) |
            Q(establishment__license_no__icontains=q) |
            Q(establishment__commercial_reg__icontains=q)
        )
        if normalized_q.isdigit():
            filters |= Q(establishment__establishment_no=int(normalized_q))
        qs = qs.filter(filters)

    wb = Workbook()
    ws = wb.active
    ws.title = 'تقارير التقييم'
    ws.append([
        'مرجع التقرير', 'رقم المنشأة', 'اسم المنشأة', 'المحافظة', 'الولاية', 'رقم الترخيص', 'تاريخ الزيارة',
        'المفتش', 'النسبة', 'التصنيف', 'الحالة', 'البنود غير المستوفية',
    ])

    for evaluation in qs:
        non_compliant = evaluation.items.all()
        missing_records = evaluation.record_checks.all()
        non_compliant_text = ' | '.join(
            f'{item.criterion.code}. {item.criterion.text_ar}' + (f' - {item.remarks}' if item.remarks else '')
            for item in non_compliant
        )
        missing_records_text = ' | '.join(record_check.record.name_ar for record_check in missing_records)
        issues_text = ' | '.join(filter(None, [non_compliant_text, missing_records_text])) or 'لا توجد بنود غير مستوفية'
        ws.append([
            evaluation.report_reference_no,
            evaluation.establishment.establishment_no,
            evaluation.establishment.commercial_name,
            evaluation.establishment.governorate.name_ar,
            evaluation.establishment.wilayat.name_ar,
            evaluation.establishment.license_no,
            str(evaluation.visit_date),
            evaluation.inspector.get_full_name() or evaluation.inspector.username,
            float(evaluation.percentage),
            evaluation.get_classification_display(),
            evaluation.get_approval_status_display(),
            issues_text,
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="evaluation_reports.xlsx"'
    wb.save(response)
    return response


_static_path_cache: dict = {}


def link_callback(uri, rel):
    if uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ''))
    elif uri.startswith(settings.STATIC_URL):
        relative = uri.replace(settings.STATIC_URL, '')
        if relative not in _static_path_cache:
            _static_path_cache[relative] = finders.find(relative)
        path = _static_path_cache[relative]
    else:
        return uri

    if not path or not os.path.isfile(path):
        raise Exception(f'تعذر العثور على الملف: {uri}')
    return path



def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    original_named_temp_file = pisa_files.tempfile.NamedTemporaryFile

    def reopenable_named_temp_file(*args, **kwargs):
        kwargs.setdefault('delete', False)
        return original_named_temp_file(*args, **kwargs)

    pisa_files.tempfile.NamedTemporaryFile = reopenable_named_temp_file
    try:
        pdf = pisa.pisaDocument(
            BytesIO(html.encode('UTF-8')),
            result,
            encoding='UTF-8',
            link_callback=link_callback,
        )
    finally:
        pisa_files.tempfile.NamedTemporaryFile = original_named_temp_file

    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None


def get_pdf_font_context():
    return {}


def _build_evaluation_report_context(evaluation):
    items_list = list(
        EvaluationItem.objects.filter(evaluation=evaluation, status='non_compliant')
        .select_related('criterion', 'criterion__section')
        .order_by('criterion__section__sort_order', 'criterion__sort_order', 'id')
    )

    grouped_items = OrderedDict()
    images_by_criterion = {}
    for image in EvaluationImage.objects.filter(evaluation=evaluation).select_related('criterion').order_by('id'):
        images_by_criterion.setdefault(image.criterion_id, []).append(image)

    for item in items_list:
        section = item.criterion.section
        grouped_items.setdefault(section, [])
        grouped_items[section].append(item)

    # النتائج محفوظة مسبقاً - لا حاجة لإعادة الحساب عند كل فتح للتقرير

    def _person_name(user):
        if not user:
            return ''
        profile_name = getattr(getattr(user, 'userprofile', None), 'full_name', '')
        if (profile_name or '').strip():
            return profile_name.strip()
        full_name = getattr(user, 'get_full_name', lambda: '')() or ''
        return full_name.strip()

    signature_rows = []
    signature_rows.extend(
        {
            'name': member.full_name,
            'job_title': member.job_title,
        }
        for member in evaluation.team_members.all()
        if (member.full_name or '').strip() or (member.job_title or '').strip()
    )
    if evaluation.reviewer:
        signature_rows.append({
            'name': _person_name(evaluation.reviewer),
            'job_title': 'المراجع الفني',
        })

    return {
        'evaluation': evaluation,
        'grouped_items': grouped_items,
        'images_by_criterion': images_by_criterion,
        'signature_rows': signature_rows,
        'non_compliant_total': len(items_list),
    }


def _set_docx_rtl(paragraph, alignment=WD_ALIGN_PARAGRAPH.RIGHT):
    paragraph.alignment = alignment
    p_pr = paragraph._element.get_or_add_pPr()
    if p_pr.find(qn('w:bidi')) is None:
        p_pr.append(OxmlElement('w:bidi'))


def _set_cell_text(cell, text, bold=False, alignment=WD_ALIGN_PARAGRAPH.CENTER, vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER):
    cell.vertical_alignment = vertical_alignment
    cell.text = ''
    paragraph = cell.paragraphs[0]
    _set_docx_rtl(paragraph, alignment=alignment)
    run = paragraph.add_run(str(text or ''))
    run.bold = bold
    run.font.name = 'Tahoma'
    run._element.rPr.rFonts.set(qn('w:cs'), 'Tahoma')
    run.font.size = Pt(10)


def _add_docx_heading(document, text, level=1):
    paragraph = document.add_heading('', level=level)
    _set_docx_rtl(paragraph, alignment=WD_ALIGN_PARAGRAPH.CENTER)
    run = paragraph.add_run(str(text or ''))
    run.font.name = 'Tahoma'
    run._element.rPr.rFonts.set(qn('w:cs'), 'Tahoma')
    return paragraph


def _add_docx_paragraph(document, label, value=''):
    paragraph = document.add_paragraph()
    _set_docx_rtl(paragraph)
    label_run = paragraph.add_run(str(label or ''))
    label_run.bold = True
    label_run.font.name = 'Tahoma'
    label_run._element.rPr.rFonts.set(qn('w:cs'), 'Tahoma')
    value_run = paragraph.add_run(str(value or ''))
    value_run.font.name = 'Tahoma'
    value_run._element.rPr.rFonts.set(qn('w:cs'), 'Tahoma')
    return paragraph


def _format_docx_date(value):
    if not value:
        return ''
    return value.strftime('%Y/%m/%d')


def _add_docx_report_header(section):
    header_path = finders.find('images/report_header.png')
    if not header_path or not os.path.exists(header_path):
        return
    header = section.header
    paragraph = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
    _set_docx_rtl(paragraph, alignment=WD_ALIGN_PARAGRAPH.CENTER)
    available_width = section.page_width - section.left_margin - section.right_margin
    try:
        paragraph.add_run().add_picture(header_path, width=available_width)
    except Exception:
        return


def _build_evaluation_docx(evaluation):
    context = _build_evaluation_report_context(evaluation)
    grouped_items = context['grouped_items']
    images_by_criterion = context['images_by_criterion']

    document = Document()
    section = document.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = section.page_height, section.page_width
    section.top_margin = Inches(1.65)
    section.bottom_margin = Inches(0.5)
    section.left_margin = Inches(0.55)
    section.right_margin = Inches(0.55)
    section.header_distance = Inches(0.15)
    _add_docx_report_header(section)

    styles = document.styles
    styles['Normal'].font.name = 'Tahoma'
    styles['Normal']._element.rPr.rFonts.set(qn('w:cs'), 'Tahoma')
    styles['Normal'].font.size = Pt(10)

    _add_docx_heading(document, f'تقرير زيارة ميدانية إلى شركة: {evaluation.establishment.commercial_name}', 1)

    info_table = document.add_table(rows=0, cols=4)
    info_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    info_table.style = 'Table Grid'
    rows = [
        ('مرجع التقرير', evaluation.report_reference_no, 'تاريخ الزيارة', _format_docx_date(evaluation.visit_date)),
        ('اسم المنشأة', evaluation.establishment.commercial_name, 'رقم المنشأة', evaluation.establishment.establishment_no),
        ('المحافظة', evaluation.establishment.governorate.name_ar, 'الولاية', evaluation.establishment.wilayat.name_ar),
        ('نسبة الامتثال', f'{evaluation.percentage}%', 'التصنيف', evaluation.get_classification_display()),
        ('المفتش / المقيم', evaluation.inspector.get_full_name() or evaluation.inspector.username, 'حالة التقييم', evaluation.get_approval_status_display()),
    ]
    for row_values in rows:
        cells = info_table.add_row().cells
        _set_cell_text(cells[0], row_values[0], bold=True)
        _set_cell_text(cells[1], row_values[1])
        _set_cell_text(cells[2], row_values[2], bold=True)
        _set_cell_text(cells[3], row_values[3])

    document.add_paragraph()
    _add_docx_heading(document, 'البنود غير المستوفية والإجراءات التصحيحية', 2)

    if not grouped_items:
        _add_docx_paragraph(document, '', 'لا توجد بنود غير مستوفية.')
    else:
        for section_obj, items in grouped_items.items():
            _add_docx_heading(document, f'{section_obj.sort_order} - {section_obj.name_ar}', 3)
            table = document.add_table(rows=1, cols=5)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.style = 'Table Grid'
            headers = ['البند', 'نص البند غير المستوفي', 'الملاحظات', 'الإجراء التصحيحي', 'الصور']
            for index, header in enumerate(headers):
                _set_cell_text(table.rows[0].cells[index], header, bold=True)
            for item in items:
                cells = table.add_row().cells
                _set_cell_text(cells[0], item.criterion.code)
                _set_cell_text(cells[1], item.criterion.text_ar)
                _set_cell_text(cells[2], item.remarks or '-')
                _set_cell_text(cells[3], item.corrective_action or '-')
                image_cell = cells[4]
                image_cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
                image_cell.text = ''
                images = images_by_criterion.get(item.criterion_id, [])
                if images:
                    for image in images:
                        paragraph = image_cell.add_paragraph()
                        _set_docx_rtl(paragraph, alignment=WD_ALIGN_PARAGRAPH.CENTER)
                        image_path = getattr(image.image, 'path', '')
                        if image_path and os.path.exists(image_path):
                            try:
                                paragraph.add_run().add_picture(image_path, width=Inches(1.55))
                            except Exception:
                                paragraph.add_run('تعذر إدراج الصورة')
                        else:
                            paragraph.add_run('الصورة غير متوفرة')
                        if image.caption:
                            caption = image_cell.add_paragraph()
                            _set_docx_rtl(caption, alignment=WD_ALIGN_PARAGRAPH.CENTER)
                            caption.add_run(image.caption)
                else:
                    _set_cell_text(image_cell, '-')

    # نتيجة التقييم (جدول)
    _add_docx_heading(document, 'نتيجة التقييم', 2)
    result_table = document.add_table(rows=1, cols=3)
    result_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    result_table.style = 'Table Grid'
    headers = ['الوصف', 'النسبة', 'التصنيف']
    for index, header in enumerate(headers):
        _set_cell_text(result_table.rows[0].cells[index], header, bold=True)
    status = getattr(evaluation, 'establishment_status', None)
    if status:
        row = result_table.add_row().cells
        _set_cell_text(row[0], status.get('description', '') if isinstance(status, dict) else getattr(status, 'description', ''))
        _set_cell_text(row[1], f"{evaluation.percentage}%")
        _set_cell_text(row[2], status.get('label', '') if isinstance(status, dict) else getattr(status, 'label', ''))

    # ملاحظات عامة (قبل فريق التقييم)
    if (evaluation.notes or '').strip():
        _add_docx_heading(document, 'ملاحظات عامة', 2)
        _add_docx_paragraph(document, '', evaluation.notes)

    # الإجراءات التصحيحية العامة (إن وجدت)
    if (evaluation.corrective_action or '').strip():
        _add_docx_heading(document, 'الإجراءات التصحيحية العامة', 2)
        _add_docx_paragraph(document, '', evaluation.corrective_action)

    # فريق التقييم والاعتماد
    if context['signature_rows']:
        _add_docx_heading(document, 'فريق التقييم والاعتماد', 2)
        sign_table = document.add_table(rows=1, cols=3)
        sign_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        sign_table.style = 'Table Grid'
        for index, header in enumerate(['الاسم', 'المسمى الوظيفي', 'التوقيع']):
            _set_cell_text(sign_table.rows[0].cells[index], header, bold=True)
        for signature in context['signature_rows']:
            cells = sign_table.add_row().cells
            _set_cell_text(cells[0], signature['name'])
            _set_cell_text(cells[1], signature['job_title'])
            _set_cell_text(cells[2], '')

    output = BytesIO()
    document.save(output)
    output.seek(0)
    return output


@login_required
def evaluation_word(request, pk):
    evaluation = get_object_or_404(
        Evaluation.objects.select_related(
            'establishment',
            'establishment__governorate',
            'establishment__wilayat',
            'inspector',
            'reviewer',
        ).prefetch_related('team_members'),
        pk=pk,
    )
    docx_file = _build_evaluation_docx(evaluation)
    response = HttpResponse(
        docx_file.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )
    response['Content-Disposition'] = f'attachment; filename="official_evaluation_{evaluation.id}.docx"'
    return response


PDF_CACHE_TIMEOUT = 60 * 10  # 10 دقائق


@login_required
def evaluation_pdf(request, pk):
    evaluation = get_object_or_404(
        Evaluation.objects.select_related('establishment', 'inspector', 'reviewer').prefetch_related('team_members'),
        pk=pk,
    )
    # استخدم الكاش فقط للتقييمات المكتملة (المسودات قد تتغير)
    pdf_cache_key = None
    if evaluation.approval_status == 'completed':
        pdf_cache_key = f'pdf_bytes:eval:{pk}'
        cached_pdf = cache.get(pdf_cache_key)
        if cached_pdf is not None:
            response = HttpResponse(cached_pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="official_evaluation_{pk}.pdf"'
            return response

    context = _build_evaluation_report_context(evaluation)
    response = render_to_pdf('inspections/evaluation_pdf_official.html', context)
    if response:
        if pdf_cache_key:
            cache.set(pdf_cache_key, response.content, PDF_CACHE_TIMEOUT)
        response['Content-Disposition'] = f'inline; filename="official_evaluation_{evaluation.id}.pdf"'
        return response
    return HttpResponse('حدث خطأ أثناء إنشاء ملف PDF')

