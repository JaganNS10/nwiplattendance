# ============================================================
#  Neminath Wood Industry Pvt. Ltd.
#  Attendance System — views.py
#  App: app
# ============================================================

import datetime
import calendar
import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Sum, Q
from decimal import Decimal

from .models import (
    Employee, AttendanceRecord, Permission,
    MonthlyReport, Holiday, Department, SystemConfig,OvertimeRecord
)
from .utils import (
    is_working_day, get_working_days_list, get_working_days_count,
    get_today_summary, get_or_create_daily_attendance,
    get_permission_budget, calculate_net_salary,
    get_month_name, MONTHLY_BUFFER_MINUTES,
)


# ============================================================
# 1. DASHBOARD
# ============================================================

@login_required
def dashboard(request):
    summary = get_today_summary()
    today   = summary['today']

    # Last 7 days bar chart data
    bar_data = []
    for i in range(6, -1, -1):
        d     = today - datetime.timedelta(days=i)
        count = AttendanceRecord.objects.filter(date=d, status='present').count()
        bar_data.append({
            'label':      d.strftime('%d %b'),
            'day':        d.strftime('%a'),
            'count':      count,
            'is_working': is_working_day(d),
        })

    # Recent attendance records (today)
    today_records = AttendanceRecord.objects.filter(
        date=today, employee__status='active'
    ).select_related('employee').order_by('employee__employee_id')[:10]

    # Pending permissions count
    pending_perms = Permission.objects.filter(
        date__year  = today.year,
        date__month = today.month,
    ).count()

    context = {
        'summary':       summary,
        'today':         today,
        'bar_data':      bar_data,
        'today_records': today_records,
        'pending_perms': pending_perms,
    }
    return render(request, 'app/dashboard.html', context)


# ============================================================
# 2. DAILY ATTENDANCE ENTRY  ⭐ Most Important Page
# ============================================================

# @login_required
# def daily_attendance(request):
#     """
#     Admin selects a date → sees all employees in one table
#     → enters In Time, Out Time, Status, Remarks
#     → clicks Save All
#     """
#     today       = timezone.localdate()
#     date_str    = request.GET.get('date', str(today))

#     try:
#         selected_date = datetime.date.fromisoformat(date_str)
#     except ValueError:
#         selected_date = today

#     is_holiday = not is_working_day(selected_date)

#     if request.method == 'POST':
#         selected_date_str = request.POST.get('attendance_date')
#         try:
#             selected_date = datetime.date.fromisoformat(selected_date_str)
#         except (ValueError, TypeError):
#             selected_date = today

#         employees = Employee.objects.filter(status='active').order_by('employee_id')
#         saved     = 0

#         for emp in employees:
#             key_status   = f'status_{emp.id}'
#             key_in       = f'in_time_{emp.id}'
#             key_out      = f'out_time_{emp.id}'
#             key_remarks  = f'remarks_{emp.id}'

#             status  = request.POST.get(key_status, 'absent')
#             in_raw  = request.POST.get(key_in, '').strip()
#             out_raw = request.POST.get(key_out, '').strip()
#             remarks = request.POST.get(key_remarks, '').strip()

#             in_time  = None
#             out_time = None

#             if in_raw:
#                 try:
#                     in_time = datetime.time.fromisoformat(in_raw)
#                 except ValueError:
#                     pass

#             if out_raw:
#                 try:
#                     out_time = datetime.time.fromisoformat(out_raw)
#                 except ValueError:
#                     pass

#             record, _ = AttendanceRecord.objects.get_or_create(
#                 employee = emp,
#                 date     = selected_date,
#             )
#             record.status   = status
#             record.in_time  = in_time
#             record.out_time = out_time
#             record.remarks  = remarks
#             record.save()
#             saved += 1

#         messages.success(request, f'✅ Attendance saved for {saved} employees on {selected_date.strftime("%d %B %Y")}.')
#         return redirect(f'{request.path}?date={selected_date}')

#     # GET — load existing records
#     records = get_or_create_daily_attendance(selected_date)

#     context = {
#         'selected_date': selected_date,
#         'records':       records,
#         'is_holiday':    is_holiday,
#         'today':         today,
#     }
#     return render(request, 'app/daily_attendance.html', context)

@login_required
def daily_attendance(request):
    """
    Admin selects a date → sees all employees in one table
    → enters In Time, Out Time, Status, Remarks
    → clicks Save All
    """
    today       = timezone.localdate()
    date_str    = request.GET.get('date', str(today))

    try:
        selected_date = datetime.date.fromisoformat(date_str)
    except ValueError:
        selected_date = today

    is_holiday = not is_working_day(selected_date)

    if request.method == 'POST':
        selected_date_str = request.POST.get('attendance_date')
        try:
            selected_date = datetime.date.fromisoformat(selected_date_str)
        except (ValueError, TypeError):
            selected_date = today

        employees = Employee.objects.filter(status='active').order_by('employee_id')
        saved     = 0

        for emp in employees:
            key_status   = f'status_{emp.id}'
            key_in       = f'in_time_{emp.id}'
            key_out      = f'out_time_{emp.id}'
            key_remarks  = f'remarks_{emp.id}'

            status  = request.POST.get(key_status, 'absent')
            in_raw  = request.POST.get(key_in, '').strip()
            out_raw = request.POST.get(key_out, '').strip()
            remarks = request.POST.get(key_remarks, '').strip()

            in_time  = None
            out_time = None

            if in_raw:
                try:
                    in_time = datetime.time.fromisoformat(in_raw)
                except ValueError:
                    pass

            if out_raw:
                try:
                    out_time = datetime.time.fromisoformat(out_raw)
                except ValueError:
                    pass

            record, _ = AttendanceRecord.objects.get_or_create(
                employee = emp,
                date     = selected_date,
            )
            record.status   = status
            record.in_time  = in_time
            record.out_time = out_time
            record.remarks  = remarks
            record.save()
            saved += 1

            # ── AUTO CREATE OT IF SUNDAY ──
            if selected_date.weekday() == 6:  # 6 = Sunday
                if status == 'present':
                    ot_exists = OvertimeRecord.objects.filter(
                        employee = emp,
                        date     = selected_date,
                    ).exists()

                    if not ot_exists:
                        working_days = get_working_days_count(
                            selected_date.year,
                            selected_date.month,
                        )
                        OvertimeRecord.objects.create(
                            employee        = emp,
                            date            = selected_date,
                            ot_type         = 'full_day',
                            added_by        = 'Auto — Sunday Work',
                            override_reason = 'Auto generated — Employee worked on Sunday',
                        )

        messages.success(request, f'Attendance saved for {saved} employees on {selected_date.strftime("%d %B %Y")}.')
        return redirect(f'{request.path}?date={selected_date}')

    # GET — load existing records
    records = get_or_create_daily_attendance(selected_date)

    context = {
        'selected_date': selected_date,
        'records':       records,
        'is_holiday':    is_holiday,
        'today':         today,
    }
    return render(request, 'app/daily_attendance.html', context)

# ============================================================
# 3. EMPLOYEE MANAGEMENT
# ============================================================

@login_required
def employee_list(request):
    search = request.GET.get('q', '').strip()
    dept   = request.GET.get('dept', '')

    employees = Employee.objects.filter(status='active').select_related('department')

    if search:
        employees = employees.filter(
            Q(name__icontains=search) | Q(employee_id__icontains=search)
        )
    if dept:
        employees = employees.filter(department_id=dept)

    departments = Department.objects.all()

    context = {
        'employees':   employees,
        'departments': departments,
        'search':      search,
        'dept':        dept,
        'total':       employees.count(),
    }
    return render(request, 'app/employee_list.html', context)


@login_required
def employee_add(request):
    departments = Department.objects.all()

    if request.method == 'POST':
        try:
            emp = Employee(
                employee_id    = request.POST['employee_id'].strip(),
                name           = request.POST['name'].strip(),
                gender         = request.POST.get('gender', 'M'),
                phone          = request.POST.get('phone', '').strip(),
                email          = request.POST.get('email', '').strip(),
                designation    = request.POST['designation'].strip(),
                date_joined    = request.POST['date_joined'],
                monthly_salary = request.POST['monthly_salary'],
                address        = request.POST.get('address', '').strip(),
            )
            dept_id = request.POST.get('department')
            if dept_id:
                emp.department_id = dept_id
            if request.FILES.get('face_photo'):
                emp.face_photo = request.FILES['face_photo']
            emp.save()
            messages.success(request, f'✅ Employee {emp.name} ({emp.employee_id}) added successfully!')
            return redirect('app:employee_list')
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')

    context = {'departments': departments}
    return render(request, 'app/employee_add.html', context)


@login_required
def employee_edit(request, employee_id):
    employee    = get_object_or_404(Employee, employee_id=employee_id)
    departments = Department.objects.all()

    if request.method == 'POST':
        try:
            employee.name           = request.POST['name'].strip()
            employee.gender         = request.POST.get('gender', 'M')
            employee.phone          = request.POST.get('phone', '').strip()
            employee.email          = request.POST.get('email', '').strip()
            employee.designation    = request.POST['designation'].strip()
            employee.date_joined    = request.POST['date_joined']
            employee.monthly_salary = request.POST['monthly_salary']
            employee.address        = request.POST.get('address', '').strip()
            dept_id = request.POST.get('department')
            employee.department_id  = dept_id if dept_id else None
            employee.save()
            messages.success(request, f'✅ {employee.name} updated successfully!')
            return redirect('app:employee_list')
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')

    context = {'employee': employee, 'departments': departments}
    return render(request, 'app/employee_edit.html', context)


@login_required
def employee_detail(request, employee_id):
    employee = get_object_or_404(Employee, employee_id=employee_id)
    today    = timezone.localdate()

    year  = int(request.GET.get('year',  today.year))
    month = int(request.GET.get('month', today.month))

    monthly_data = calculate_net_salary(employee, year, month)
    budget       = get_permission_budget(employee, year, month)
    net_salary = (monthly_data['monthly_salary'] - monthly_data['absent_deduction'] - monthly_data['auto_debit_amount']).quantize(Decimal('0.01'))

    # Monthly attendance records
    records = AttendanceRecord.objects.filter(
        employee    = employee,
        date__year  = year,
        date__month = month,
    ).order_by('date')

    # Permission history this month
    permissions = Permission.objects.filter(
        employee    = employee,
        date__year  = year,
        date__month = month,
    ).order_by('-date')

    years  = list(range(today.year - 1, today.year + 1))
    months = [(i, calendar.month_name[i]) for i in range(1, 13)]
    
    context = {
        'employee':     employee,
        'monthly_data': monthly_data,
        'budget':       budget,
        'records':      records,
        'permissions':  permissions,
        'year':         year,
        'month':        month,
        'month_name':   get_month_name(month),
        'years':        years,
        'months':       months,
        'net_salary':   net_salary,
    }
    return render(request, 'app/employee_detail.html', context)


# ============================================================
# 4. PERMISSION MANAGEMENT
# ============================================================

@login_required
def permission_list(request):
    today = timezone.localdate()
    year  = int(request.GET.get('year',  today.year))
    month = int(request.GET.get('month', today.month))

    permissions = Permission.objects.filter(
        date__year  = year,
        date__month = month,
    ).select_related('employee').order_by('-date')

    years  = list(range(today.year - 1, today.year + 1))
    months = [(i, calendar.month_name[i]) for i in range(1, 13)]

    context = {
        'permissions': permissions,
        'year':        year,
        'month':       month,
        'month_name':  get_month_name(month),
        'years':       years,
        'months':      months,
    }
    return render(request, 'app/permission_list.html', context)


@login_required
def permission_add(request):
    today     = timezone.localdate()
    employees = Employee.objects.filter(status='active').order_by('employee_id')

    if request.method == 'POST':
        emp_id    = request.POST.get('employee')
        date_str  = request.POST.get('date', str(today))
        minutes   = request.POST.get('requested_minutes', 0)
        reason    = request.POST.get('reason', '').strip()
        status    = request.POST.get('status', 'approved')

        try:
            employee = Employee.objects.get(id=emp_id)
            date     = datetime.date.fromisoformat(date_str)
            minutes  = int(minutes)

            # Check budget
            budget = get_permission_budget(employee, date.year, date.month)

            perm = Permission.objects.create(
                employee          = employee,
                date              = date,
                requested_minutes = minutes,
                reason            = reason,
                status            = status,
                added_by          = request.user.get_full_name() or request.user.username,
            )

            if budget['used'] + minutes > MONTHLY_BUFFER_MINUTES:
                messages.warning(
                    request,
                    f'⚠ Permission added for {employee.name}. '
                    f'Monthly 2-hour buffer exceeded by {(budget["used"] + minutes) - MONTHLY_BUFFER_MINUTES} min. '
                    f'Excess will be debited from salary.'
                )
            else:
                messages.success(request, f'✅ Permission added for {employee.name} — {minutes} minutes.')

            return redirect('app:permission_list')

        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')

    context = {
        'employees': employees,
        'today':     today,
    }
    return render(request, 'app/permission_add.html', context)


@login_required
def permission_delete(request, perm_id):
    perm = get_object_or_404(Permission, id=perm_id)
    name = perm.employee.name
    perm.delete()
    messages.success(request, f'Permission deleted for {name}.')
    return redirect('app:permission_list')


# ============================================================
# 5. MONTHLY REPORT
# ============================================================

@login_required
def monthly_report(request):
    today = timezone.localdate()
    year  = int(request.GET.get('year',  today.year))
    month = int(request.GET.get('month', today.month))

    employees   = Employee.objects.filter(status='active').select_related('department')
    report_data = []

    for emp in employees:
        data = calculate_net_salary(emp, year, month)
        if not data:
            continue

        # Check if admin override exists
        try:
            mr = MonthlyReport.objects.get(employee=emp, year=year, month=month)
            data['admin_debit_override']        = mr.admin_debit_override
            data['admin_debit_override_reason'] = mr.admin_debit_override_reason
            data['final_debit'] = mr.final_debit
            data['net_salary']  = (
                emp.monthly_salary - data['absent_deduction'] - mr.final_debit
            ).quantize(Decimal('0.01'))
            data['report_id'] = mr.id
        except MonthlyReport.DoesNotExist:
            data['admin_debit_override']        = None
            data['admin_debit_override_reason'] = ''
            data['final_debit'] = data['auto_debit_amount']
            data['net_salary']  = (
                emp.monthly_salary - data['absent_deduction'] - data['auto_debit_amount']
            ).quantize(Decimal('0.01'))
            data['report_id'] = None

        report_data.append(data)

    # Totals
    totals = {
        'monthly_salary':   sum(d['monthly_salary']   for d in report_data),
        'absent_deduction': sum(d['absent_deduction'] for d in report_data),
        'final_debit':      sum(d['final_debit']      for d in report_data),
        'net_salary':       sum(d['net_salary']        for d in report_data),
    }

    working_days = get_working_days_count(year, month)
    years  = list(range(today.year - 1, today.year + 1))
    months = [(i, calendar.month_name[i]) for i in range(1, 13)]

    context = {
        'report_data':  report_data,
        'totals':       totals,
        'year':         year,
        'month':        month,
        'month_name':   get_month_name(month),
        'working_days': working_days,
        'years':        years,
        'months':       months,
    }
    return render(request, 'app/monthly_report.html', context)


@login_required
def debit_override(request, employee_id):
    """Admin overrides debit amount for an employee for a specific month."""
    employee = get_object_or_404(Employee, employee_id=employee_id)
    today    = timezone.localdate()
    year     = int(request.POST.get('year',  today.year))
    month    = int(request.POST.get('month', today.month))

    if request.method == 'POST':
        override_amount = request.POST.get('admin_debit_override', '').strip()
        override_reason = request.POST.get('admin_debit_override_reason', '').strip()

        try:
            # Get or create monthly report
            mr, _ = MonthlyReport.objects.get_or_create(
                employee = employee,
                year     = year,
                month    = month,
            )
            mr.calculate()  # Recalculate first

            if override_amount == '' or override_amount is None:
                mr.admin_debit_override        = None
                mr.admin_debit_override_reason = ''
                messages.success(request, f'✅ Debit override cleared for {employee.name}. Auto debit restored.')
            else:
                mr.admin_debit_override        = Decimal(override_amount).quantize(Decimal('0.01'))
                mr.admin_debit_override_reason = override_reason
                messages.success(request, f'✅ Debit overridden to ₹{override_amount} for {employee.name}.')

            # Recalculate net salary with new override
            mr.net_salary = (
                employee.monthly_salary - mr.absent_deduction - mr.final_debit
            ).quantize(Decimal('0.01'))
            mr.save()

        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')

    return redirect(f"{request.META.get('HTTP_REFERER', '/reports/monthly/')}#{employee_id}")


# ============================================================
# 6. EXPORT CSV
# ============================================================

@login_required
def export_monthly_csv(request):
    today = timezone.localdate()
    year  = int(request.GET.get('year',  today.year))
    month = int(request.GET.get('month', today.month))

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="NeminathAttendance_{year}_{str(month).zfill(2)}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow([
        'S.No', 'Employee ID', 'Name', 'Designation', 'Department',
        'Working Days', 'Present', 'Absent', 'Paid Leave',
        'Late (min)', 'Early Exit (min)', 'Permission (min)',
        'Total Deviation (min)', 'Excess (min)',
        'Monthly Salary', 'Absent Deduction',
        'Auto Debit', 'Admin Override Debit', 'Final Debit', 'Net Salary'
    ])

    employees = Employee.objects.filter(status='active').select_related('department')

    for i, emp in enumerate(employees, 1):
        d = calculate_net_salary(emp, year, month)
        if not d:
            continue

        try:
            mr             = MonthlyReport.objects.get(employee=emp, year=year, month=month)
            override_debit = mr.admin_debit_override or ''
            final_debit    = mr.final_debit
            net_salary     = mr.net_salary
        except MonthlyReport.DoesNotExist:
            override_debit = ''
            final_debit    = d['auto_debit_amount']
            net_salary     = d['monthly_salary'] - d['absent_deduction'] - final_debit

        writer.writerow([
            i,
            emp.employee_id,
            emp.name,
            emp.designation,
            emp.department.name if emp.department else '',
            d['total_working_days'],
            d['present_days'],
            d['absent_days'],
            d['paid_leave_days'],
            d['total_late_minutes'],
            d['total_early_exit_minutes'],
            d['total_permission_minutes'],
            d['total_deviation_minutes'],
            d['excess_minutes'],
            d['monthly_salary'],
            d['absent_deduction'],
            d['auto_debit_amount'],
            override_debit,
            final_debit,
            net_salary,
        ])

    return response


# ============================================================
# 7. AJAX — Live salary preview
# ============================================================

@login_required
def api_salary_preview(request, employee_id):
    """Returns salary breakdown JSON for a given employee/month."""
    employee = get_object_or_404(Employee, employee_id=employee_id)
    today    = timezone.localdate()
    year     = int(request.GET.get('year',  today.year))
    month    = int(request.GET.get('month', today.month))

    data = calculate_net_salary(employee, year, month)

    return JsonResponse({
        'present_days':             data.get('present_days', 0),
        'absent_days':              data.get('absent_days', 0),
        'total_late_minutes':       data.get('total_late_minutes', 0),
        'total_early_exit_minutes': data.get('total_early_exit_minutes', 0),
        'total_permission_minutes': data.get('total_permission_minutes', 0),
        'excess_minutes':           data.get('excess_minutes', 0),
        'monthly_salary':           str(data.get('monthly_salary', 0)),
        'absent_deduction':         str(data.get('absent_deduction', 0)),
        'auto_debit_amount':        str(data.get('auto_debit_amount', 0)),
        'net_salary':               str(
            data.get('monthly_salary', Decimal(0)) -
            data.get('absent_deduction', Decimal(0)) -
            data.get('auto_debit_amount', Decimal(0))
        ),
    })


# ============================================================
#  ADD THESE VIEWS INTO YOUR EXISTING views.py
#  Place after the export_monthly_csv view
# ============================================================

# Add these imports at top of views.py if not already there:
# from django.http import HttpResponse
# from .export_utils import generate_monthly_excel, generate_daily_pdf

import datetime
import calendar
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from .utils import (
    get_working_days_count, get_month_name,
    calculate_net_salary, get_or_create_daily_attendance,
    is_working_day,
)
from .models import Employee, AttendanceRecord, MonthlyReport, Department
from .utils import generate_monthly_excel, generate_daily_pdf
from decimal import Decimal


# ============================================================
# EXPORT EXCEL — Monthly Salary Report
# ============================================================

@login_required
def export_monthly_excel(request):
    """
    Generates and downloads the monthly salary report as a styled .xlsx file.
    URL: /reports/export/excel/?year=2025&month=5
    """
    today = timezone.localdate()
    year  = int(request.GET.get('year',  today.year))
    month = int(request.GET.get('month', today.month))

    employees    = Employee.objects.filter(status='active').select_related('department')
    report_data  = []
    working_days = get_working_days_count(year, month)

    for emp in employees:
        data = calculate_net_salary(emp, year, month)
        if not data:
            continue

        try:
            mr = MonthlyReport.objects.get(employee=emp, year=year, month=month)
            data['admin_debit_override']        = mr.admin_debit_override
            data['admin_debit_override_reason'] = mr.admin_debit_override_reason
            data['final_debit'] = mr.final_debit
            data['net_salary']  = (
                emp.monthly_salary - data['absent_deduction'] - mr.final_debit
            ).quantize(Decimal('0.01'))
        except MonthlyReport.DoesNotExist:
            data['admin_debit_override']        = None
            data['admin_debit_override_reason'] = ''
            data['final_debit'] = data['auto_debit_amount']
            data['net_salary']  = (
                emp.monthly_salary - data['absent_deduction'] - data['auto_debit_amount']
            ).quantize(Decimal('0.01'))

        report_data.append(data)

    totals = {
        'monthly_salary':   sum(d['monthly_salary']   for d in report_data),
        'absent_deduction': sum(d['absent_deduction'] for d in report_data),
        'final_debit':      sum(d['final_debit']      for d in report_data),
        'net_salary':       sum(d['net_salary']        for d in report_data),
    }

    month_name = get_month_name(month)
    buf        = generate_monthly_excel(report_data, totals, year, month, working_days)
    filename   = f"NWI_Salary_Report_{month_name}_{year}.xlsx"

    response = HttpResponse(
        buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ============================================================
# EXPORT PDF — Daily Attendance Register
# ============================================================

@login_required
def export_daily_pdf(request):
    """
    Generates and downloads the daily attendance register as a styled PDF.
    URL: /attendance/export/pdf/?date=2025-05-21
    """
    today    = timezone.localdate()
    date_str = request.GET.get('date', str(today))

    try:
        selected_date = datetime.date.fromisoformat(date_str)
    except ValueError:
        selected_date = today

    # Get all attendance records for the date
    records = AttendanceRecord.objects.filter(
        date=selected_date,
        employee__status='active',
    ).select_related('employee', 'employee__department').order_by('employee__employee_id')

    # Build summary
    total_active = Employee.objects.filter(status='active').count()
    present      = records.filter(status='present').count()
    absent       = records.filter(status='absent').count()
    late         = records.filter(status='present', late_minutes__gt=0).count()
    paid_leave   = records.filter(status='paid_leave').count()

    summary = {
        'total_active': total_active,
        'present':      present,
        'absent':       absent,
        'late':         late,
        'paid_leave':   paid_leave,
        'is_working':   is_working_day(selected_date),
    }

    buf      = generate_daily_pdf(records, selected_date, summary)
    filename = f"NWI_Attendance_{selected_date.strftime('%d_%b_%Y')}.pdf"

    response = HttpResponse(buf.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ============================================================
#  FACE CHECK-IN VIEW — Add to views.py
# ============================================================
# Add these imports at top of views.py:
# import base64, json
# from PIL import Image as PILImage
# import io

import base64
import json
import datetime
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import Employee, AttendanceRecord


# ============================================================
# FACE CHECK-IN API
# ============================================================

@login_required
def face_checkin(request):
    """
    POST endpoint called by face-api.js when a face is matched.
    Receives: employee_id, session_start_time, matched (bool)
    Logic:
      - If scan_time is within 30 min of session_start → use session_start as in_time
      - If scan_time is after 30 min → use actual scan_time (genuinely late)
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    try:
        data           = json.loads(request.body)
        employee_id    = data.get('employee_id')
        session_start  = data.get('session_start')   # "HH:MM" string
        matched        = data.get('matched', False)

        if not matched:
            return JsonResponse({'success': False, 'error': 'Face not matched! Try again.'})

        employee = get_object_or_404(Employee, employee_id=employee_id)
        today    = timezone.localdate()

        # ── Server time (real, tamper-proof) ──
        now_server = timezone.localtime(timezone.now())
        scan_time  = now_server.time().replace(second=0, microsecond=0)

        # ── Grace window logic ──
        # Parse session_start time
        in_time = scan_time  # default: use real scan time

        if session_start:
            try:
                sh, sm    = map(int, session_start.split(':'))
                sess_time = datetime.time(sh, sm)
                sess_dt   = datetime.datetime.combine(today, sess_time)
                scan_dt   = datetime.datetime.combine(today, scan_time)
                diff_mins = (scan_dt - sess_dt).total_seconds() / 60

                if 0 <= diff_mins <= 30:
                    # Within 30 min grace window → use session start time
                    in_time = sess_time
                else:
                    # Beyond grace window → real scan time (late)
                    in_time = scan_time
            except (ValueError, TypeError):
                in_time = scan_time

        # ── Save to AttendanceRecord ──
        record, created = AttendanceRecord.objects.get_or_create(
            employee = employee,
            date     = today,
            defaults = {'status': 'present', 'in_time': in_time},
        )

        if not created:
            # Only update if in_time not already set (don't overwrite)
            if not record.in_time:
                record.in_time = in_time
                record.status  = 'present'
                record.save()
            else:
                return JsonResponse({
                    'success': False,
                    'error':   f'{employee.name} already checked in at {record.in_time.strftime("%H:%M")}.'
                })
        else:
            record.save()

        # ── Response ──
        grace_used = (in_time != scan_time)
        return JsonResponse({
            'success':     True,
            'employee':    employee.name,
            'employee_id': employee.employee_id,
            'in_time':     in_time.strftime('%H:%M'),
            'scan_time':   scan_time.strftime('%H:%M'),
            'grace_used':  grace_used,
            'message':     (
                f'✅ {employee.name} checked in at {in_time.strftime("%H:%M")}'
                + (' (session start time applied)' if grace_used else ' (actual time)')
            ),
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ============================================================
# GET EMPLOYEE FACE PHOTO — for face-api.js matching
# ============================================================

@login_required
def employee_face_photo(request, employee_id):
    """
    Returns the employee's face photo as base64 JSON.
    Used by face-api.js to load reference image for matching.
    """
    employee = get_object_or_404(Employee, employee_id=employee_id)

    if not employee.face_photo:
        return JsonResponse({'success': False, 'error': 'No face photo uploaded.'})

    try:
        with employee.face_photo.open('rb') as f:
            img_data = base64.b64encode(f.read()).decode('utf-8')

        # Detect content type
        name = employee.face_photo.name.lower()
        if name.endswith('.png'):
            mime = 'image/png'
        elif name.endswith('.webp'):
            mime = 'image/webp'
        else:
            mime = 'image/jpeg'

        return JsonResponse({
            'success':   True,
            'photo':     f'data:{mime};base64,{img_data}',
            'name':      employee.name,
            'employee_id': employee.employee_id,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    


@login_required
def ot_list(request):
    today = timezone.localdate()
    year  = int(request.GET.get('year',  today.year))
    month = int(request.GET.get('month', today.month))

    ot_records = OvertimeRecord.objects.filter(
        date__year=year, date__month=month
    ).select_related('employee', 'employee__department')

    # Attach per day salary to each record
    for ot in ot_records:
        ot.per_day = ot.per_day_salary

    total_ot = sum(ot.final_ot_amount for ot in ot_records)

    years  = list(range(today.year - 1, today.year + 2))
    months = [(i, calendar.month_name[i]) for i in range(1, 13)]

    return render(request, 'app/ot_list.html', {
        'ot_records':  ot_records,
        'year':        year,
        'month':       month,
        'month_name':  get_month_name(month),
        'total_ot':    total_ot,
        'years':       years,
        'months':      months,
    })


@login_required
def ot_add(request):
    employees = Employee.objects.filter(status='active').select_related('department')

    # Attach per day salary hint for each employee
    today = timezone.localdate()
    from .utils import get_working_days_count
    working_days = get_working_days_count(today.year, today.month)
    for emp in employees:
        # emp.per_day = (
        #     emp.monthly_salary / Decimal(working_days)
        # ).quantize(Decimal('0.01')) if working_days else Decimal('0')
        emp.per_day = (
            emp.monthly_salary / Decimal(working_days)
        ).quantize(Decimal('0.01')) if working_days else Decimal('0')
        emp.per_hour = (
            emp.per_day / Decimal('9')
        ).quantize(Decimal('0.01'))

    if request.method == 'POST':
        emp_id   = request.POST.get('employee')
        date_str = request.POST.get('date')
        ot_type  = request.POST.get('ot_type')
        ot_hours = request.POST.get('ot_hours') or None
        override = request.POST.get('admin_ot_override') or None
        reason   = request.POST.get('override_reason', '')
        added_by = request.user.get_full_name() or request.user.username

        try:
            emp  = Employee.objects.get(id=emp_id)
            date = datetime.date.fromisoformat(date_str)

            ot = OvertimeRecord(
                employee          = emp,
                date              = date,
                ot_type           = ot_type,
                ot_hours          = Decimal(ot_hours) if ot_hours else None,
                admin_ot_override = Decimal(override) if override else None,
                override_reason   = reason,
                added_by          = added_by,
            )
            ot.save()
            messages.success(request, f'OT added for {emp.name} — ₹{ot.final_ot_amount}')
            return redirect('app:ot_list')
        except Exception as e:
            messages.error(request, f'Error: {e}')

    return render(request, 'app/ot_add.html', {
        'employees': employees,
        'today':     today,
    })


@login_required
def ot_delete(request, ot_id):
    ot = get_object_or_404(OvertimeRecord, id=ot_id)
    if request.method == 'POST':
        emp_name = ot.employee.name
        ot.delete()
        messages.success(request, f'OT record deleted for {emp_name}.')
    return redirect('app:ot_list')