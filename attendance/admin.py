# attendance/admin.py

from django.contrib import admin
from .models import Student, Course, AttendanceRecord,Teacher

# Define a custom admin class for the Student model
class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'last_name', 'student_id')
    search_fields = ('name', 'last_name', 'student_id')

# Define a custom admin class for the Course model
class CourseAdmin(admin.ModelAdmin):
    list_display = ('course_name',)
    search_fields = ('course_name',)
    filter_horizontal = ('students',) # A more user-friendly widget for ManyToMany fields

# Define a custom admin class for the AttendanceRecord model
class AttendanceRecordAdmin(admin.ModelAdmin):
    # Columns to display in the list view
    list_display = ('student', 'course', 'date', 'status','period')
    
    # Filters that appear on the right sidebar
    list_filter = ('date', 'course', 'status')
    
    # Fields to search by
    search_fields = ('student__first_name', 'student__last_name', 'course__course_name')
    
    # Default ordering
    ordering = ('-date', 'course')

# Unregister the basic models if they were already registered
# (This is only needed if you are modifying this file after first registering them)
# If this is your first time, you can skip the unregister lines.
# admin.site.unregister(Student)
# admin.site.unregister(Course)
# admin.site.unregister(AttendanceRecord)

# Register the models with their custom admin classes
admin.site.register(Student, StudentAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(AttendanceRecord, AttendanceRecordAdmin)
admin.site.register(Teacher)