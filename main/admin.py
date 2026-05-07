
from django.contrib import admin
from .models import (
    RecruiterProfile, ApplicantProfile, JobDescription,
    Resume, MatchResult
)

@admin.register(RecruiterProfile)
class RecruiterProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'company_name', 'industry', 'created_at']
    search_fields = ['user__username', 'company_name', 'industry']
    list_filter = ['industry', 'created_at']

@admin.register(ApplicantProfile)
class ApplicantProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'created_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']

@admin.register(JobDescription)
class JobDescriptionAdmin(admin.ModelAdmin):
    list_display = ['title', 'recruiter', 'location', 'employment_type', 'is_active', 'created_at']
    list_filter = ['is_active', 'employment_type', 'created_at']
    search_fields = ['title', 'description', 'recruiter__company_name']
    date_hierarchy = 'created_at'

@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ['applicant', 'filename', 'is_processed', 'uploaded_at']
    list_filter = ['is_processed', 'uploaded_at']
    search_fields = ['applicant__user__username', 'applicant__user__first_name', 'applicant__user__last_name']
    date_hierarchy = 'uploaded_at'

@admin.register(MatchResult)
class MatchResultAdmin(admin.ModelAdmin):
    list_display = ['resume', 'job', 'overall_score', 'created_at']
    list_filter = ['created_at']
    search_fields = ['resume__applicant__user__username', 'job__title']
    ordering = ['-overall_score']
