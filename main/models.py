from django.db import models
from django.contrib.auth.models import User
import os

class RecruiterProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=200)
    company_description = models.TextField(blank=True)
    industry = models.CharField(max_length=100, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.company_name} - {self.user.username}"

class ApplicantProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    linkedin_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.user.username}"

class JobDescription(models.Model):
    recruiter = models.ForeignKey(RecruiterProfile, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    department = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    requirements = models.TextField()
    responsibilities = models.TextField()
    required_skills = models.TextField(help_text="Comma-separated skills")
    required_experience = models.CharField(max_length=50, blank=True)
    education_level = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=200, blank=True)
    employment_type = models.CharField(
        max_length=50,
        choices=[
            ('full_time', 'Full Time'),
            ('part_time', 'Part Time'),
            ('contract', 'Contract'),
            ('internship', 'Internship'),
        ],
        default='full_time'
    )
    salary_range = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} at {self.recruiter.company_name}"

class Resume(models.Model):
    applicant = models.ForeignKey(ApplicantProfile, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, blank=True)
    job = models.ForeignKey(JobDescription, on_delete=models.CASCADE, null=True, blank=True)
    file = models.FileField(upload_to='resumes/%Y/%m/')
    extracted_text = models.TextField(blank=True)
    skills = models.TextField(blank=True)
    education = models.TextField(blank=True)
    experience = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False)

    def filename(self):
        return os.path.basename(self.file.name)

    def __str__(self):
        return f"Resume - {self.applicant.user.get_full_name()}"

class MatchResult(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE)
    job = models.ForeignKey(JobDescription, on_delete=models.CASCADE)
    similarity_score = models.FloatField(default=0.0)
    skills_match_score = models.FloatField(default=0.0)
    experience_match_score = models.FloatField(default=0.0)
    education_match_score = models.FloatField(default=0.0)
    overall_score = models.FloatField(default=0.0)
    matched_skills = models.TextField(blank=True)
    missing_skills = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-overall_score']

    def __str__(self):
        return f"Match: {self.resume.applicant.user.get_full_name()} - {self.job.title} ({self.overall_score:.2f})"
