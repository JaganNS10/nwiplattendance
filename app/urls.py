# ============================================================
#  Neminath Wood Industry Pvt. Ltd.
#  Attendance System — urls.py
#  App: app
# ============================================================

from django.urls import path
from . import views

app_name = 'app'

urlpatterns = [

    # --------------------------------------------------------
    # DASHBOARD
    # --------------------------------------------------------
   path('', views.dashboard, name='dashboard'),

    # --------------------------------------------------------
    # DAILY ATTENDANCE  ⭐
    # --------------------------------------------------------
    path('attendance/daily/', views.daily_attendance, name='daily_attendance'),

    # --------------------------------------------------------
    # EMPLOYEE MANAGEMENT
    # --------------------------------------------------------
    path('employees/',                        views.employee_list,   name='employee_list'),
    path('employees/add/',                    views.employee_add,    name='employee_add'),
    path('employees/<str:employee_id>/edit/', views.employee_edit,   name='employee_edit'),
    path('employees/<str:employee_id>/',      views.employee_detail, name='employee_detail'),

    # --------------------------------------------------------
    # PERMISSION MANAGEMENT
    # --------------------------------------------------------
    path('permissions/',                    views.permission_list,   name='permission_list'),
    path('permissions/add/',                views.permission_add,    name='permission_add'),
    path('permissions/<int:perm_id>/delete/', views.permission_delete, name='permission_delete'),

    # --------------------------------------------------------
    # MONTHLY REPORT & DEBIT OVERRIDE
    # --------------------------------------------------------
   path('reports/monthly/',                          views.monthly_report,  name='monthly_report'),
   path('reports/debit-override/<str:employee_id>/', views.debit_override,  name='debit_override'),
   path('reports/export/csv/',                       views.export_monthly_csv, name='export_csv'),

    # --------------------------------------------------------
    # API
    # --------------------------------------------------------
   path('api/salary/<str:employee_id>/', views.api_salary_preview, name='api_salary_preview'),

    #   # Face check-in
   path('face/checkin/',
       views.face_checkin,
       name='face_checkin'),

   path('face/photo/<str:employee_id>/',
       views.employee_face_photo,
       name='employee_face_photo'),

   # Excel export
   path('reports/export/excel/',
       views.export_monthly_excel,
       name='export_excel'),

   # PDF export
   path('attendance/export/pdf/',
       views.export_daily_pdf,
       name='export_daily_pdf'),

   # OT Management
   path('overtime/',                    views.ot_list,     name='ot_list'),
   path('overtime/add/',                views.ot_add,      name='ot_add'),
   path('overtime/<int:ot_id>/delete/', views.ot_delete,   name='ot_delete'),
]


