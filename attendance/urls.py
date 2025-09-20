from django.urls import path
from . import views

urlpatterns = [
    path('mark/<int:course_id>/<int:period>/', views.mark_attendance, name='mark_attendance'),
    path('dashboard/', views.dashboard, name='class_dashboard'),
    path('upload/', views.bulk_upload_view, name='bulk_upload'),
    path('report/', views.daily_report_view, name='daily_report'),
    path('student/<int:student_id>/', views.student_report_view, name='student_report'),
    path('add-users/', views.bulk_user_add_view, name='bulk_user_add'),
    path('statistics/', views.statistics_view, name='statistics'),
    path('lookup/', views.student_lookup_view, name='student_lookup'),


]