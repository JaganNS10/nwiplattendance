# ============================================================
#  Neminath Wood Industry Pvt. Ltd.
#  Attendance System — models.py
#  App: app
# ============================================================

from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
import datetime


# ------------------------------------------------------------
# 1. DEPARTMENT
# ------------------------------------------------------------
class Department(models.Model):
    name       = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


# ------------------------------------------------------------
# 2. EMPLOYEE
# ------------------------------------------------------------
class Employee(models.Model):

    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]
    STATUS_CHOICES = [('active', 'Active'), ('inactive', 'Inactive')]

    employee_id    = models.CharField(max_length=20, unique=True)
    name           = models.CharField(max_length=200)
    gender         = models.CharField(max_length=1, choices=GENDER_CHOICES, default='M')
    phone          = models.CharField(max_length=15, blank=True)
    email          = models.EmailField(null=True,blank=True)
    address        = models.TextField(blank=True)
    face_photo = models.ImageField(
      upload_to='face_photos/',
      null=True, blank=True,
      help_text="Employee face photo for check-in recognition"
    )
    department     = models.ForeignKey(Department, on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name='employees')
    designation    = models.CharField(max_length=100)
    date_joined    = models.DateField(null=True,blank=True)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    monthly_salary = models.DecimalField(max_digits=10, decimal_places=2,
                                         validators=[MinValueValidator(Decimal('0.01'))])
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee_id} — {self.name}"

    class Meta:
        ordering = ['employee_id']


# ------------------------------------------------------------
# 3. ATTENDANCE RECORD
# ------------------------------------------------------------
class AttendanceRecord(models.Model):

    STATUS_CHOICES = [
        ('present',    'Present'),
        ('absent',     'Absent'),
        ('paid_leave', 'Paid Leave'),
        ('holiday',    'Holiday'),
    ]

    employee           = models.ForeignKey(Employee, on_delete=models.CASCADE,
                                           related_name='attendance_records')
    date               = models.DateField()
    status             = models.CharField(max_length=20, choices=STATUS_CHOICES, default='absent')
    in_time            = models.TimeField(null=True, blank=True)
    out_time           = models.TimeField(null=True, blank=True)
    late_minutes       = models.PositiveIntegerField(default=0)
    early_exit_minutes = models.PositiveIntegerField(default=0)
    remarks            = models.CharField(max_length=200, blank=True)
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    IN_GRACE_END    = datetime.time(9,  0)
    OUT_GRACE_START = datetime.time(18, 50)

    def save(self, *args, **kwargs):
        if self.in_time and self.status == 'present':
            if self.in_time > self.IN_GRACE_END:
                in_dt    = datetime.datetime.combine(self.date, self.in_time)
                grace_dt = datetime.datetime.combine(self.date, self.IN_GRACE_END)
                self.late_minutes = max(int((in_dt - grace_dt).total_seconds() / 60), 0)
            else:
                self.late_minutes = 0
        else:
            self.late_minutes = 0

        if self.out_time and self.status == 'present' and self.out_time > datetime.time(12, 0):
            if self.out_time < self.OUT_GRACE_START:
                out_dt   = datetime.datetime.combine(self.date, self.out_time)
                grace_dt = datetime.datetime.combine(self.date, self.OUT_GRACE_START)
                self.early_exit_minutes = max(int((grace_dt - out_dt).total_seconds() / 60), 0)
            else:
                self.early_exit_minutes = 0
        else:
            self.early_exit_minutes = 0

        super().save(*args, **kwargs)

    @property
    def total_deviation(self):
        return self.late_minutes + self.early_exit_minutes

    def __str__(self):
        return f"{self.employee.employee_id} | {self.date} | {self.get_status_display()}"

    class Meta:
        unique_together = ('employee', 'date')
        ordering        = ['-date', 'employee__employee_id']


# ------------------------------------------------------------
# 4. PERMISSION
# ------------------------------------------------------------
class Permission(models.Model):

    employee          = models.ForeignKey(Employee, on_delete=models.CASCADE,
                                          related_name='permissions')
    date              = models.DateField()
    requested_minutes = models.PositiveIntegerField()
    reason            = models.TextField(blank=True)
    status            = models.CharField(max_length=20,
                                         choices=[('approved','Approved'),('rejected','Rejected')],
                                         default='approved')
    added_by          = models.CharField(max_length=100, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee.employee_id} | {self.date} | {self.requested_minutes} min"

    class Meta:
        ordering = ['-date']


# ------------------------------------------------------------
# 5. MONTHLY REPORT
# ------------------------------------------------------------
class MonthlyReport(models.Model):

    employee                    = models.ForeignKey(Employee, on_delete=models.CASCADE,
                                                    related_name='monthly_reports')
    year                        = models.PositiveIntegerField()
    month                       = models.PositiveIntegerField()
    total_working_days          = models.PositiveIntegerField(default=0)
    present_days                = models.PositiveIntegerField(default=0)
    absent_days                 = models.PositiveIntegerField(default=0)
    paid_leave_days             = models.PositiveIntegerField(default=0)
    total_late_minutes          = models.PositiveIntegerField(default=0)
    total_early_exit_minutes    = models.PositiveIntegerField(default=0)
    total_permission_minutes    = models.PositiveIntegerField(default=0)
    total_deviation_minutes     = models.PositiveIntegerField(default=0)
    excess_minutes              = models.PositiveIntegerField(default=0)
    monthly_salary              = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    absent_deduction            = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    auto_debit_amount           = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    admin_debit_override        = models.DecimalField(max_digits=10, decimal_places=2,
                                                       null=True, blank=True)
    admin_debit_override_reason = models.TextField(blank=True)
    net_salary                  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_finalized                = models.BooleanField(default=False)
    generated_at                = models.DateTimeField(auto_now=True)

    MONTHLY_BUFFER_MINUTES = 120
    WORK_MINUTES_PER_DAY   = 610

    @property
    def final_debit(self):
        if self.admin_debit_override is not None:
            return self.admin_debit_override
        return self.auto_debit_amount

    def calculate(self):
        from .utils import get_working_days_count
        from django.db.models import Sum

        working_days            = get_working_days_count(self.year, self.month)
        self.total_working_days = working_days
        records = AttendanceRecord.objects.filter(
            employee=self.employee, date__year=self.year, date__month=self.month)

        self.present_days    = records.filter(status='present').count()
        self.paid_leave_days = records.filter(status='paid_leave').count()
        self.absent_days     = max(working_days - self.present_days - self.paid_leave_days, 0)

        agg = records.filter(status='present').aggregate(
            late=Sum('late_minutes'), early=Sum('early_exit_minutes'))
        self.total_late_minutes       = agg['late']  or 0
        self.total_early_exit_minutes = agg['early'] or 0

        perm_mins = Permission.objects.filter(
            employee=self.employee, date__year=self.year,
            date__month=self.month, status='approved'
        ).aggregate(total=Sum('requested_minutes'))['total'] or 0
        self.total_permission_minutes = perm_mins

        self.total_deviation_minutes = (
            self.total_late_minutes + self.total_early_exit_minutes + self.total_permission_minutes)
        self.excess_minutes = max(self.total_deviation_minutes - self.MONTHLY_BUFFER_MINUTES, 0)

        self.monthly_salary   = self.employee.monthly_salary
        # per_day               = self.monthly_salary / Decimal(working_days) if working_days else Decimal('0')
        import calendar
        calendar_days = calendar.monthrange(self.year, self.month)[1]
        per_day = self.monthly_salary / Decimal(calendar_days)
        self.absent_deduction = (per_day * Decimal(self.absent_days)).quantize(Decimal('0.01'))

        total_work_mins = Decimal(working_days * self.WORK_MINUTES_PER_DAY)
        self.auto_debit_amount = (
            Decimal(self.excess_minutes) / total_work_mins * self.monthly_salary
        ).quantize(Decimal('0.01')) if self.excess_minutes > 0 and total_work_mins > 0 else Decimal('0.00')

        self.net_salary = (
            self.monthly_salary - self.absent_deduction - self.final_debit
        ).quantize(Decimal('0.01'))

        self.save()

    def __str__(self):
        return f"{self.employee.employee_id} | {self.year}-{self.month:02d} | ₹{self.net_salary}"

    class Meta:
        unique_together = ('employee', 'year', 'month')
        ordering        = ['-year', '-month', 'employee__employee_id']


# ------------------------------------------------------------
# 6. HOLIDAY
# ------------------------------------------------------------
class Holiday(models.Model):
    date        = models.DateField(unique=True)
    name        = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.date} — {self.name}"

    class Meta:
        ordering = ['date']


# ------------------------------------------------------------
# 7. SYSTEM CONFIG (single row)
# ------------------------------------------------------------
class SystemConfig(models.Model):
    company_name                     = models.CharField(max_length=200,
                                       default='Neminath Wood Industry Pvt. Ltd.')
    monthly_permission_limit_minutes = models.PositiveIntegerField(default=120)
    monthly_paid_leave_limit         = models.PositiveIntegerField(default=1)
    in_grace_end                     = models.TimeField(default=datetime.time(9, 0))
    out_grace_start                  = models.TimeField(default=datetime.time(18, 50))
    updated_at                       = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name

    class Meta:
        verbose_name        = 'System Configuration'
        verbose_name_plural = 'System Configuration'


# ------------------------------------------------------------
# 8. OVERTIME RECORD
# ------------------------------------------------------------
class OvertimeRecord(models.Model):

    OT_TYPE_CHOICES = [
        ('full_day', 'Full Day'),
        ('hours',    'Hours'),
    ]

    employee          = models.ForeignKey(Employee, on_delete=models.CASCADE,
                                          related_name='overtime_records')
    date              = models.DateField()
    ot_type           = models.CharField(max_length=20, choices=OT_TYPE_CHOICES)
    ot_hours          = models.DecimalField(max_digits=4, decimal_places=1,
                                            null=True, blank=True,
                                            help_text="Only if type is Hours")
    auto_ot_amount    = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    admin_ot_override = models.DecimalField(max_digits=10, decimal_places=2,
                                            null=True, blank=True,
                                            help_text="Leave blank to use auto amount")
    override_reason   = models.TextField(blank=True)
    added_by          = models.CharField(max_length=100, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    @property
    def final_ot_amount(self):
        if self.admin_ot_override is not None:
            return self.admin_ot_override
        return self.auto_ot_amount

    @property
    def per_day_salary(self):
        from .utils import get_working_days_count
        import datetime
        working_days = get_working_days_count(
            self.date.year, self.date.month
        )
        if working_days == 0:
            return Decimal('0')
        return (self.employee.monthly_salary / Decimal(working_days)).quantize(Decimal('0.01'))

    def calculate_ot_amount(self):
        per_day = self.per_day_salary
        if self.ot_type == 'full_day':
            self.auto_ot_amount = per_day
        elif self.ot_type == 'hours' and self.ot_hours:
            per_hour = (per_day / Decimal('8')).quantize(Decimal('0.01'))
            self.auto_ot_amount = (per_hour * self.ot_hours).quantize(Decimal('0.01'))
        else:
            self.auto_ot_amount = Decimal('0')

    def save(self, *args, **kwargs):
        self.calculate_ot_amount()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.employee_id} | {self.date} | {self.ot_type} | ₹{self.final_ot_amount}"

    class Meta:
        ordering = ['-date', 'employee__employee_id']