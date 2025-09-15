from django.shortcuts import render,get_object_or_404,redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required

from .models import Course, Student, AttendanceRecord
import datetime

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