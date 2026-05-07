from django.urls import path
from . import views

urlpatterns = [
    # Home & Auth
    path('', views.HomeView.as_view(), name='home'),
    path('register/', views.RegisterChoiceView.as_view(), name='register_choice'),
    path('register/recruiter/', views.RegisterRecruiterView.as_view(), name='register_recruiter'),
    path('register/applicant/', views.RegisterApplicantView.as_view(), name='register_applicant'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    
    # Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # Recruiter URLs
    path('jobs/create/', views.CreateJobView.as_view(), name='create_job'),
    path('jobs/<int:job_id>/', views.JobDetailView.as_view(), name='view_job'),
    path('jobs/<int:job_id>/edit/', views.EditJobView.as_view(), name='edit_job'),
    path('jobs/<int:job_id>/toggle/', views.ToggleJobStatusView.as_view(), name='toggle_job_status'),
    path('jobs/<int:job_id>/delete/', views.DeleteJobView.as_view(), name='delete_job'),
    path('jobs/<int:job_id>/match/', views.MatchCandidatesView.as_view(), name='match_candidates'),
    
    # Applicant URLs
    path('resume/upload/', views.UploadResumeView.as_view(), name='upload_resume'),
    path('resume/<int:resume_id>/', views.ResumeDetailView.as_view(), name='view_resume'),
    path('resume/<int:resume_id>/delete/', views.DeleteResumeView.as_view(), name='delete_resume'),
    path('jobs/browse/', views.BrowseJobsView.as_view(), name='browse_jobs'),
    
    # API
    path('api/match/<int:match_id>/', views.GetMatchDetailsView.as_view(), name='get_match_details'),
]