from django.urls import path
from . import views

urlpatterns = [
    path('mark/<int:course_id>/<int:period>/', views.mark_attendance, name='mark_attendance'),
    path('dashboard/', views.dashboard, name='class_dashboard'),
    path('upload/', views.bulk_upload_view, name='bulk_upload'),
    path('report/', views.daily_report_view, name='daily_report'),

]