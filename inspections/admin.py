from django.contrib import admin
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
    Governorate,
    RequiredRecord,
    UserProfile,
    Wilayat,
)

admin.site.site_header = 'لوحة إدارة نظام تقييم المصانع الغذائية'
admin.site.site_title = 'إدارة النظام'
admin.site.index_title = 'إدارة البيانات والتقييمات'


class EvaluationItemInline(admin.TabularInline):
    model = EvaluationItem
    extra = 0


class EvaluationRecordCheckInline(admin.TabularInline):
    model = EvaluationRecordCheck
    extra = 0


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('establishment', 'visit_date', 'percentage', 'classification', 'approval_status')
    list_filter = ('approval_status', 'classification', 'visit_date')
    search_fields = ('establishment__commercial_name', 'establishment__license_no')
    inlines = [EvaluationItemInline, EvaluationRecordCheckInline]


@admin.register(Establishment)
class EstablishmentAdmin(admin.ModelAdmin):
    list_display = ('establishment_no', 'commercial_name', 'activity_type', 'governorate', 'wilayat', 'status')
    list_filter = ('status', 'governorate', 'activity_type')
    search_fields = ('establishment_no', 'commercial_name', 'license_no', 'commercial_reg')


admin.site.register(Governorate)
admin.site.register(Wilayat)
admin.site.register(EvaluationSection)
admin.site.register(Criterion)
admin.site.register(RequiredRecord)
admin.site.register(EvaluationImage)
admin.site.register(CorrectiveActionLog)
admin.site.register(EvaluationActivityLog)
admin.site.register(UserProfile)
