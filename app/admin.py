# ============================================================
#  Neminath Wood Industry Pvt. Ltd.
#  Attendance System — admin.py
#  App: app
# ============================================================

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    Department, Employee, AttendanceRecord,
    Permission, MonthlyReport, Holiday, SystemConfig,OvertimeRecord
)


# ------------------------------------------------------------
# 1. DEPARTMENT
# ------------------------------------------------------------
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display  = ('name', 'employee_count', 'created_at')
    search_fields = ('name',)

    def employee_count(self, obj):
        count = obj.employees.filter(status='active').count()
        return format_html('<b style="color:#3B82F6">{}</b>', count)
    employee_count.short_description = 'Active Employees'


# ------------------------------------------------------------
# 2. EMPLOYEE
# ------------------------------------------------------------
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display   = (
        'employee_id', 'name', 'department', 'face_photo',
        'designation', 'monthly_salary', 'status_badge', 'date_joined'
    )
    list_filter    = ('status', 'department', 'gender')
    search_fields  = ('employee_id', 'name', 'phone', 'email')
    ordering       = ('employee_id',)
    readonly_fields= ('created_at', 'updated_at')

    fieldsets = (
        ('Personal Info', {
            'fields': ('employee_id', 'name', 'gender', 'phone', 'email', 'address')
        }),
        ('Job Details', {
            'fields': ('department', 'designation', 'date_joined', 'status')
        }),
        ('Salary', {
    'fields': ('monthly_salary',)
        }),
        ('Face Recognition', {
            'fields': ('face_photo',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        color = '#10B981' if obj.status == 'active' else '#EF4444'
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:20px;font-size:11px;font-weight:700">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'


# ------------------------------------------------------------
# 3. ATTENDANCE RECORD
# ------------------------------------------------------------
@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display   = (
        'employee', 'date', 'in_time', 'out_time',
        'status_badge', 'late_minutes', 'early_exit_minutes', 'remarks'
    )
    list_filter    = ('status', 'date')
    search_fields  = ('employee__employee_id', 'employee__name')
    date_hierarchy = 'date'
    ordering       = ('-date', 'employee__employee_id')
    readonly_fields= ('late_minutes', 'early_exit_minutes', 'created_at', 'updated_at')

    fieldsets = (
        ('Record', {
            'fields': ('employee', 'date', 'status')
        }),
        ('Times', {
            'fields': ('in_time', 'out_time', 'late_minutes', 'early_exit_minutes')
        }),
        ('Notes', {
            'fields': ('remarks',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        colors = {
            'present':    '#10B981',
            'absent':     '#EF4444',
            'paid_leave': '#3B82F6',
            'holiday':    '#6366F1',
        }
        color = colors.get(obj.status, '#64748B')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:20px;font-size:11px;font-weight:700">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'


# ------------------------------------------------------------
# 4. PERMISSION
# ------------------------------------------------------------
@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display   = (
        'employee', 'date', 'requested_minutes',
        'status_badge', 'reason', 'added_by', 'created_at'
    )
    list_filter    = ('status', 'date')
    search_fields  = ('employee__employee_id', 'employee__name')
    ordering       = ('-date',)
    readonly_fields= ('created_at',)

    def status_badge(self, obj):
        color = '#10B981' if obj.status == 'approved' else '#EF4444'
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:20px;font-size:11px;font-weight:700">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'


# ------------------------------------------------------------
# 5. MONTHLY REPORT
# ------------------------------------------------------------
@admin.register(MonthlyReport)
class MonthlyReportAdmin(admin.ModelAdmin):
    list_display   = (
        'employee', 'year', 'month_display',
        'present_days', 'absent_days',
        'excess_minutes',
        'auto_debit_display',
        'override_display',
        'net_salary_display',
        'is_finalized'
    )
    list_filter    = ('year', 'month', 'is_finalized')
    search_fields  = ('employee__employee_id', 'employee__name')
    ordering       = ('-year', '-month', 'employee__employee_id')
    readonly_fields= ('generated_at', 'auto_debit_amount', 'absent_deduction',
                      'total_deviation_minutes', 'excess_minutes', 'net_salary')

    fieldsets = (
        ('Employee & Period', {
            'fields': ('employee', 'year', 'month')
        }),
        ('Day Summary', {
            'fields': ('total_working_days', 'present_days', 'absent_days', 'paid_leave_days')
        }),
        ('Time Deviation', {
            'fields': ('total_late_minutes', 'total_early_exit_minutes',
                       'total_permission_minutes', 'total_deviation_minutes', 'excess_minutes')
        }),
        ('Salary', {
            'fields': ('monthly_salary', 'absent_deduction', 'auto_debit_amount',
                       'admin_debit_override', 'admin_debit_override_reason', 'net_salary')
        }),
        ('Status', {
            'fields': ('is_finalized', 'generated_at')
        }),
    )

    def month_display(self, obj):
        import calendar
        return calendar.month_name[obj.month]
    month_display.short_description = 'Month'

    def auto_debit_display(self, obj):
        if obj.auto_debit_amount > 0:
            return format_html('<span style="color:#F59E0B;font-weight:700">₹{}</span>',
                               obj.auto_debit_amount)
        return '—'
    auto_debit_display.short_description = 'Auto Debit'

    def override_display(self, obj):
        if obj.admin_debit_override is not None:
            return format_html('<span style="color:#EF4444;font-weight:700">₹{}</span>',
                               obj.admin_debit_override)
        return format_html('<span style="color:#64748B">—</span>')
    override_display.short_description = 'Override Debit'

    def net_salary_display(self, obj):
        return format_html('<b style="color:#10B981;font-size:13px">₹{}</b>', obj.net_salary)
    net_salary_display.short_description = 'Net Salary'


# ------------------------------------------------------------
# 6. HOLIDAY
# ------------------------------------------------------------
@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display  = ('date', 'name', 'description')
    search_fields = ('name',)
    date_hierarchy= 'date'
    ordering      = ('date',)


# ------------------------------------------------------------
# 7. SYSTEM CONFIG
# ------------------------------------------------------------
@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = (
        'company_name',
        'in_grace_end',
        'out_grace_start',
        'monthly_permission_limit_minutes',
        'monthly_paid_leave_limit',
        'updated_at'
    )

    fieldsets = (
        ('Company', {
            'fields': ('company_name',)
        }),
        ('Time Windows', {
            'fields': (('in_grace_end', 'out_grace_start'),)
        }),
        ('Policy', {
            'fields': ('monthly_permission_limit_minutes', 'monthly_paid_leave_limit')
        }),
    )

    def has_add_permission(self, request):
        # Only one config row allowed
        return not SystemConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


# ------------------------------------------------------------
# ADMIN SITE CUSTOMIZATION
# ------------------------------------------------------------
admin.site.site_header  = 'Neminath Wood Industry'
admin.site.site_title   = 'Neminath Attendance'
admin.site.index_title  = 'Attendance Management System'

@admin.register(OvertimeRecord)
class OvertimeRecordAdmin(admin.ModelAdmin):
    list_display  = (
        'employee', 'date', 'ot_type',
        'ot_hours', 'per_day_display',
        'auto_ot_display', 'override_display',
        'final_ot_display', 'added_by'
    )
    list_filter   = ('ot_type', 'date')
    search_fields = ('employee__employee_id', 'employee__name')
    ordering      = ('-date',)
    readonly_fields = ('auto_ot_amount', 'created_at')

    def per_day_display(self, obj):
        return format_html(
            '<span style="color:#94a3b8;font-size:11px;">₹{}/day</span>',
            obj.per_day_salary
        )
    per_day_display.short_description = 'Per Day'

    def auto_ot_display(self, obj):
        return format_html('<span style="color:#f59e0b;">₹{}</span>', obj.auto_ot_amount)
    auto_ot_display.short_description = 'Auto OT'

    def override_display(self, obj):
        if obj.admin_ot_override is not None:
            return format_html('<span style="color:#ef4444;font-weight:700;">₹{}</span>', obj.admin_ot_override)
        return '—'
    override_display.short_description = 'Override'

    def final_ot_display(self, obj):
        return format_html('<b style="color:#10b981;">₹{}</b>', obj.final_ot_amount)
    final_ot_display.short_description = 'Final OT'