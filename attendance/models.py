# attendance/models.py

from django.db import models
from django.contrib.auth.models import User

class Teacher(models.Model):
    teacher_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
class Student(models.Model):
    student_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} {self.student_id}"

class Course(models.Model):
    course_name = models.CharField(max_length=200)
    students = models.ManyToManyField(Student, related_name='courses')

    def __str__(self):
        return self.course_name

class AttendanceRecord(models.Model):
    STATUS_CHOICES = (
        ('present', 'حضور'),
        ('absent', 'غياب'),
        ('late', 'تأخير'),
    )
    PERIOD_CHOICES = (
        ('1','الأولى'),
        ('2','الثانية'),
        ('3','الثالثة'),
        ('4','الرابعة'),
        ('5','الخامسة'),
        ('6','السادسة'),
        ('7','السابعة'),
    )
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    period = models.CharField(max_length=1,choices=PERIOD_CHOICES)
    class Meta:
        # Ensures a student can only have one status per course per day
        unique_together = ('student', 'course', 'period','date')

    def __str__(self):
        return f"{self.student} - {self.course} on  {self.date} {self.period} : {self.status}"
