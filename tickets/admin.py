from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from .models import Category, Ticket, Resolution, SolutionCenter, SectoralStatistic, StaffProfile, PhoneVerification, DynamicField, DynamicFieldResponse, FormFieldAuditLog, TicketSupport, TicketComment

from .widgets import MapTilerWidget


class DynamicFieldInline(admin.TabularInline):
    model = DynamicField
    extra = 1
    fields = ('label', 'field_type', 'choices_text', 'is_required', 'order')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'sector', 'default_unit', 'description')
    list_filter = ('sector', 'default_unit')


class DynamicFieldResponseInline(admin.TabularInline):
    model = DynamicFieldResponse
    extra = 0
    readonly_fields = ('field', 'value')
    can_delete = False


@admin.register(Ticket)
class TicketAdmin(GISModelAdmin):
    list_display = ('tracking_code', 'title', 'category', 'district', 'status', 'current_unit', 'created_at')
    list_filter = ('status', 'category', 'district', 'current_unit')
    search_fields = ('tracking_code', 'title', 'description', 'district')
    readonly_fields = ('tracking_code', 'created_at', 'updated_at')
    inlines = [DynamicFieldResponseInline]
    gis_widget = MapTilerWidget
    list_per_page = 25


@admin.register(Resolution)
class ResolutionAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'assigned_unit', 'new_status', 'handled_by', 'created_at')
    list_filter = ('assigned_unit', 'new_status')
    search_fields = ('ticket__tracking_code', 'note')


@admin.register(SolutionCenter)
class SolutionCenterAdmin(GISModelAdmin):
    list_display = ('name', 'district', 'neighborhood')
    list_filter = ('district',)
    search_fields = ('name', 'address')
    gis_widget = MapTilerWidget


@admin.register(SectoralStatistic)
class SectoralStatisticAdmin(admin.ModelAdmin):
    list_display = ('year', 'month', 'period_type', 'sector', 'percentage')
    list_filter = ('period_type', 'sector', 'year')


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'unit')
    list_filter = ('unit',)

    
@admin.register(PhoneVerification)
class PhoneVerificationAdmin(admin.ModelAdmin):
    list_display = ('phone', 'is_verified', 'created_at')
    list_filter = ('is_verified',)

@admin.register(FormFieldAuditLog)
class FormFieldAuditLogAdmin(admin.ModelAdmin):
    list_display = ('category', 'field_label', 'action', 'performed_by', 'created_at')
    list_filter = ('action', 'category')
    readonly_fields = ('category', 'field_label', 'action', 'performed_by', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(TicketSupport)
class TicketSupportAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'ip_address', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('ticket__tracking_code', 'ip_address')


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'author_type', 'staff_user', 'created_at')
    list_filter = ('author_type',)
    search_fields = ('ticket__tracking_code', 'message')