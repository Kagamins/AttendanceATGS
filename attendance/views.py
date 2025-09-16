from django.shortcuts import render,get_object_or_404,redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required

from .models import Course, Student, AttendanceRecord
import datetime
from django.contrib import messages
import pandas as pd

from django.utils import timezone # Make sure to import this
from collections import defaultdict

@login_required
def daily_report_view(request):
    report_date_str = request.GET.get('report_date', timezone.now().strftime('%Y-%m-%d'))
    report_date = timezone.datetime.strptime(report_date_str, '%Y-%m-%d').date()
    status_filter = request.GET.get('status', '')

    courses = Course.objects.all() 
    
    records_query = AttendanceRecord.objects.filter(
        course__in=courses,
        date=report_date
    ).order_by('student__name'  ) # Order by student name

    if status_filter:
        records_query = records_query.filter(status=status_filter)

    records = records_query.select_related('student', 'course')

    # --- NEW: Restructure data for collation ---
    # Create a nested dictionary: {course_name: {student_name: {'status': status, 'periods': [p1, p2]}}}
    collated_attendance = defaultdict(lambda: defaultdict(lambda: {'periods': [], 'status': ''}))

    for record in records:
        student_name = f"{record.student.name}  "
        course_name = record.course.course_name
        
        # Store the status and append the period
        collated_attendance[course_name][student_name]['status'] = record.get_status_display()
        collated_attendance[course_name][student_name]['periods'].append(record.get_period_display())
    
    # Sort the final dictionary for consistent ordering
    sorted_attendance = {
        course: dict(sorted(students.items()))
        for course, students in sorted(collated_attendance.items())
    }

    context = {
        'report_date': report_date,
        'attendance_by_course': sorted_attendance, # Pass the new collated data
        'has_records': bool(records),
        'status_choices': AttendanceRecord.STATUS_CHOICES,
        'current_status': status_filter
    }
    return render(request, 'attendance/daily_report.html', context)

@login_required
def mark_attendance(request, course_id,period):
    course = get_object_or_404(Course, pk=course_id)
    students = course.students.all()
    today = datetime.date.today()

    if request.method == 'POST':
        for student in students:
            status = request.POST.get(f'status_{student.id}')

            if status:
                # Update or create an attendance record
                AttendanceRecord.objects.update_or_create(
                    student=student,
                    course=course,
                    date=today,
                    period = period,
                    defaults={'status': status   }
                )

    # Get existing records for today to display them
      # --- START OF CHANGES ---

    # 1. Get existing records for this specific period
    attendance_records = AttendanceRecord.objects.filter(course=course, date=today, period=period)
    
    # 2. Create a dictionary for quick lookups (student_id -> status)
    attendance_status_map = {record.student.id: record.status for record in attendance_records}

    # 3. Attach the status directly to each student object
    for student in students:
        # Use .get() to avoid errors if a student has no record yet
        student.current_status = attendance_status_map.get(student.id)

    context = {
        'course': course,
        'students': students, # Pass the updated students list
        'period': period,
        # 'attendance_today' is no longer needed in the context
    }
    
    # --- END OF CHANGES ---
    
    return render(request, 'attendance/mark_attendance.html', context)

@login_required
def dashboard(request):
 

    # Handle POST request when a student enrolls or drops a course
    if request.method == 'POST':
        course_id = request.POST.get('course_id')
        course = get_object_or_404(Course, id=course_id)

 

    # For GET request, display the dashboard
    all_courses = Course.objects.all()
 
    context = {
        'courses': all_courses,
 
    }
    return render(request, 'attendance/dashboard.html', context)
# attendance/views.py



 
def home_view(request):
    # If user is already logged in, redirect them to the dashboard
    if request.user.is_authenticated:
        return redirect('class_dashboard')

    error_message = None
    # If the form is submitted
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        # If authentication is successful
        if user is not None:
            login(request, user)
            return redirect('class_dashboard') # Redirect to the dashboard
        else:
            # If authentication fails
            error_message = "اسم المستخدم أو كلمة المرور غير صحيحة."

    context = {
        'error': error_message
    }
    return render(request, 'attendance/home.html', context)
@login_required
def bulk_upload_view(request):
    if request.method == 'POST':
        # Check if an Excel file was uploaded
        if 'excel_file' not in request.FILES:
            messages.error(request, "لم يتم رفع أي ملف.")
            return redirect('bulk_upload')

        excel_file = request.FILES['excel_file']

        # Check for valid file extension
        if not excel_file.name.endswith(('.xlsx', '.xls')):
            messages.error(request, "تنسيق الملف غير صالح. الرجاء رفع ملف Excel.")
            return redirect('bulk_upload')

        try:
            # --- Process Students Sheet ---
            df_students = pd.read_excel(excel_file, sheet_name='Students')
            students_created_count = 0
            for index, row in df_students.iterrows():
                _, created = Student.objects.update_or_create(
                    student_id=str(row['student_id']),
                    defaults={
                        'name': row['name'],
                     }
                )
                if created:
                    students_created_count += 1

            # --- Process Courses Sheet ---
            df_courses = pd.read_excel(excel_file, sheet_name='Courses')
            courses_created_count = 0
            for index, row in df_courses.iterrows():
                course, created = Course.objects.update_or_create(
                    course_name=row['course_name'],
                     
                )
                if created:
                    courses_created_count += 1

                # Link students to the course
                student_ids_str = str(row['student_ids']).split(',')
                student_ids = [s_id.strip() for s_id in student_ids_str]
                students_to_add = Student.objects.filter(student_id__in=student_ids)
                course.students.set(students_to_add)

            messages.success(request, f"تمت المعالجة بنجاح! {students_created_count} طالب جديد، و {courses_created_count} صف جديد.")

        except Exception as e:
            # Provide a user-friendly error message
            messages.error(request, f"حدث خطأ أثناء معالجة الملف: {e}. الرجاء التأكد من أن أسماء الأعمدة وأوراق العمل صحيحة.")

        return redirect('bulk_upload')

    return render(request, 'attendance/bulk_upload.html')