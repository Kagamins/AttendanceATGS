from django.http import HttpResponseForbidden
from django.shortcuts import render,get_object_or_404,redirect
from django.contrib.auth import authenticate, login,logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, F # Add Q and F to imports
from django.db.models.functions import TruncDate
from .models import Course, Student, AttendanceRecord, Teacher
import datetime
from django.contrib import messages
import pandas as pd
import calendar
from datetime import date
from collections import defaultdict


from django.utils import timezone # Make sure to import this
from collections import defaultdict
from django.shortcuts import redirect

def logout_view(request):
    logout(request)
    return redirect('home') # Redirect to your homepage

# attendance/views.py

@login_required
def statistics_view(request):
    # --- Filter Logic Start ---
    selected_course_id = request.GET.get('course_id', '')
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')

    all_courses = Course.objects.all()
    records = AttendanceRecord.objects.all()

    if selected_course_id:
        records = records.filter(course_id=selected_course_id)
    
    if start_date_str and end_date_str:
        start_date = timezone.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = timezone.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        records = records.filter(date__range=[start_date, end_date])
    # --- Filter Logic End ---

    # 1. Overall Attendance Stats
    overall_stats = records.values('status').annotate(count=Count('status'))
    summary = {'present': 0, 'absent': 0, 'late': 0}
    for item in overall_stats:
        summary[item['status']] = item['count']

    # 2. Daily Attendance Trend
    if not (start_date_str and end_date_str):
        thirty_days_ago = timezone.now().date() - timezone.timedelta(days=30)
        daily_records = records.filter(date__gte=thirty_days_ago)
    else:
        daily_records = records

    # Add .exclude(date__isnull=True) to prevent the error
    daily_trend = daily_records.exclude(date__isnull=True)\
        .annotate(day=TruncDate('date'))\
        .values('day').annotate(
            present_count=Count('id', filter=Q(status='present')),
            absent_count=Count('id', filter=Q(status='absent'))
        ).order_by('day')

    context = {
        'summary': summary,
        'daily_trend_labels': [item['day'].strftime('%b %d') for item in daily_trend],
        'daily_trend_present': [item['present_count'] for item in daily_trend],
        'daily_trend_absent': [item['absent_count'] for item in daily_trend],
        'all_courses': all_courses,
        'selected_course_id': selected_course_id,
        'start_date': start_date_str,
        'end_date': end_date_str,
    }
    return render(request, 'attendance/statistics.html', context)

@login_required
def student_report_view(request, student_id):
    student = get_object_or_404(Student, id=student_id)

    # Date range filtering
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    records = AttendanceRecord.objects.filter(student=student).order_by('-date')

    if start_date_str and end_date_str:
        start_date = timezone.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = timezone.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        records = records.filter(date__range=[start_date, end_date])

    # Calculate summary statistics
    stats = records.values('status').annotate(count=Count('status'))
    summary = {item['status']: item['count'] for item in stats}

    context = {
        'student': student,
        'records': records,
        'summary': {
            'present': summary.get('present', 0),
            'absent': summary.get('absent', 0),
            'late': summary.get('late', 0)
        },
        'start_date': start_date_str,
        'end_date': end_date_str
    }
    return render(request, 'attendance/student_report.html', context)
# attendance/views.py
from django.contrib.auth.models import User # Make sure User is imported

@login_required
def bulk_user_add_view(request):
    # Optional: Restrict this page to superusers
    if not request.user.is_superuser:
        return HttpResponseForbidden("You are not authorized to access this page.")

    if request.method == 'POST':
        if 'excel_file' not in request.FILES:
            messages.error(request, "لم يتم رفع أي ملف.")
            return redirect('bulk_user_add')

        excel_file = request.FILES['excel_file']
        if not excel_file.name.endswith(('.xlsx', '.xls')):
            messages.error(request, "تنسيق الملف غير صالح. الرجاء رفع ملف Excel.")
            return redirect('bulk_user_add')

        try:
            df = pd.read_excel(excel_file)
            users_created_count = 0

            for index, row in df.iterrows():
                username = str(row['username'])
                password = str(row['password'])
                name = str(row['name'])
                 

                # Skip if user already exists
                if User.objects.filter(username=username).exists():
                    continue

                # Create the Django User
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    first_name=name,
 
                )

                # Create the corresponding Teacher profile
                Teacher.objects.create(
                    user=user,
                    name=name,
                    teacher_id=username
                 )
                users_created_count += 1

            messages.success(request, f"تم إنشاء {users_created_count} مستخدم جديد بنجاح.")

        except Exception as e:
            messages.error(request, f"حدث خطأ أثناء معالجة الملف: {e}. تأكد من تطابق أسماء الأعمدة.")

        return redirect('bulk_user_add')

    return render(request, 'attendance/bulk_user_add.html')

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
        student_id = record.student.id # Get student ID

        # Store the status and append the period
        collated_attendance[course_name][student_name]['id'] = student_id
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
def student_lookup_view(request):
    query = request.GET.get('q', '')
    students = None

    if query:
        # Search by first name, last name, or student ID
        students = Student.objects.filter(
            Q(name__icontains=query) |
            Q(student_id__icontains=query)
        )

    context = {
        'students': students,
        'query': query
    }
    return render(request, 'attendance/student_lookup.html', context)

@login_required
def dashboard(request):
 
    try:
        teacher = request.user.teacher
    except Teacher.DoesNotExist:
            try:

                year = int(request.GET.get('year', date.today().year))
                month = int(request.GET.get('month', date.today().month))
                current_month_date = date(year, month, 1)
            except (ValueError, TypeError):
        # Default to today if GET params are invalid
                current_month_date = date.today()
                year, month = current_month_date.year, current_month_date.month
            first_day = current_month_date.replace(day=1)
            last_day_num = calendar.monthrange(year, month)[1]
            last_day = current_month_date.replace(day=last_day_num)

            # Create a list of all date objects for the current month
            days_in_month = [first_day + timezone.timedelta(days=d) for d in range(last_day_num)]

            # Calculate previous and next months for navigation links
            prev_month_date = first_day - timezone.timedelta(days=1)
            next_month_date = last_day + timezone.timedelta(days=1)
            course = request.user.classroom.course
            students = course.students.all().order_by('name', 'student_id')
            records = AttendanceRecord.objects.filter(
                student__in=students,
                date__range=[first_day, last_day]
                )
            # Process records into a grid for easy lookup in the template
            # Structure: {student_id: {date: status}}
            attendance_grid = defaultdict(dict)
            for record in records:
                attendance_grid[record.student_id][record.date] = record
            
            context = {
            'course': course,
            'students': students,
            'days_in_month': days_in_month,
            'attendance_grid': attendance_grid,
            'current_month_display': first_day.strftime('%B %Y'),
            'prev_month_url_params': f'?year={prev_month_date.year}&month={prev_month_date.month}',
            'next_month_url_params': f'?year={next_month_date.year}&month={next_month_date.month}',
        }
            return render(request, 'attendance/classroomDashboard.html',context)
    
    # Handle POST request when a student enrolls or drops a course
    if request.method == 'POST':
        course_id = request.POST.get('course_id')
        course = get_object_or_404(Course, id=course_id)

 

    # For GET request, display the dashboard
    all_courses = Course.objects.all()
    total_students_count = Student.objects.filter(courses__in=all_courses).distinct().count()

    context = {
        'courses': all_courses,
         'teacher': teacher,
        'total_students_count': total_students_count, # Add this to the context

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