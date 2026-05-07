from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.views import View
from django.http import HttpResponseRedirect
from django.views.generic import (
    TemplateView, CreateView, UpdateView, DeleteView, 
    DetailView, ListView
)
from django.urls import reverse_lazy, reverse
from .models import (
    RecruiterProfile, ApplicantProfile, JobDescription, 
    Resume, MatchResult
)
from .forms import (
    RecruiterRegistrationForm, ApplicantRegistrationForm,
    JobDescriptionForm, ResumeUploadForm
)
from .matching_engine import DocumentParser, MatchingEngine
from django.core.exceptions import PermissionDenied


class RecruiterRequiredMixin(UserPassesTestMixin):
    """Verify user is a recruiter"""
    def test_func(self):
        return hasattr(self.request.user, 'recruiterprofile')
    
    def handle_no_permission(self):
        messages.error(self.request, 'Only recruiters can access this page.')
        return redirect('dashboard')


class ApplicantRequiredMixin(UserPassesTestMixin):
    """Verify user is an applicant"""
    def test_func(self):
        return hasattr(self.request.user, 'applicantprofile')
    
    def handle_no_permission(self):
        messages.error(self.request, 'Only applicants can access this page.')
        return redirect('dashboard')


# ==================== HOME & AUTH VIEWS ====================

class HomeView(TemplateView):
    """Home page view"""
    template_name = 'main/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_jobs'] = JobDescription.objects.filter(is_active=True).count()
        context['total_recruiters'] = RecruiterProfile.objects.count()
        context['total_applicants'] = ApplicantProfile.objects.count()
        return context


class RegisterChoiceView(TemplateView):
    """Choose registration type"""
    template_name = 'main/register_choice.html'


class RegisterRecruiterView(CreateView):
    """Register as a recruiter"""
    form_class = RecruiterRegistrationForm
    template_name = 'main/register_recruiter.html'
    success_url = reverse_lazy('dashboard')  # ← Use this instead of overriding
    
    def form_valid(self, form):
        # Create user but don't save to DB yet
        user = form.save(commit=False)
        # Save to DB
        user.save()
        
        # Create recruiter profile
        RecruiterProfile.objects.create(
            user=user,
            company_name=form.cleaned_data['company_name'],
            company_description=form.cleaned_data.get('company_description', ''),
            industry=form.cleaned_data.get('industry', ''),
            contact_phone=form.cleaned_data.get('contact_phone', '')
        )
        
        # Login the user
        login(self.request, user)
        messages.success(self.request, 'Registration successful! Welcome to Resume Matcher.')
        
        # Set self.object so get_success_url() works
        self.object = user
        
        # Let CBV handle the redirect properly
        return HttpResponseRedirect(self.get_success_url())


class RegisterApplicantView(CreateView):
    """Register as an applicant"""
    form_class = ApplicantRegistrationForm
    template_name = 'main/register_applicant.html'
    success_url = reverse_lazy('dashboard')
    
    def form_valid(self, form):
        # Create user
        user = form.save(commit=False)
        user.first_name = form.cleaned_data.get('first_name', '')
        user.last_name = form.cleaned_data.get('last_name', '')
        user.save()
        
        # Create applicant profile
        ApplicantProfile.objects.create(
            user=user,
            phone=form.cleaned_data.get('phone', ''),
            address=form.cleaned_data.get('address', ''),
            linkedin_url=form.cleaned_data.get('linkedin_url', ''),
            portfolio_url=form.cleaned_data.get('portfolio_url', '')
        )
        
        # Login the user
        login(self.request, user)
        messages.success(self.request, 'Registration successful! Welcome to Resume Matcher.')
        
        # Set self.object for success URL
        self.object = user
        
        return HttpResponseRedirect(self.get_success_url())


class LoginView(View):
    """Custom login view"""
    template_name = 'main/login.html'
    
    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
            return render(request, self.template_name)


class LogoutView(View):
    """Logout view"""
    def get(self, request):
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
        return redirect('home')


# ==================== DASHBOARD VIEW ====================

class DashboardView(LoginRequiredMixin, View):
    """User dashboard - different for recruiters and applicants"""
    
    def get(self, request):
        # Check if user is a recruiter
        if hasattr(request.user, 'recruiterprofile'):
            return self._recruiter_dashboard(request)
        
        # Check if user is an applicant
        elif hasattr(request.user, 'applicantprofile'):
            return self._applicant_dashboard(request)
        
        # Fallback
        return render(request, 'main/dashboard.html')
    
    def _recruiter_dashboard(self, request):
        recruiter = request.user.recruiterprofile
        jobs = JobDescription.objects.filter(recruiter=recruiter).order_by('-created_at')
        total_matches = MatchResult.objects.filter(job__recruiter=recruiter).count()

        context = {
            'is_recruiter': True,
            'recruiter': recruiter,
            'jobs': jobs,
            'total_jobs': jobs.count(),
            'active_jobs': jobs.filter(is_active=True).count(),
            'total_matches': total_matches,
        }
        return render(request, 'main/recruiter_dashboard.html', context)
    
    def _applicant_dashboard(self, request):
        applicant = request.user.applicantprofile
        resumes = Resume.objects.filter(applicant=applicant).order_by('-uploaded_at')
        available_jobs = JobDescription.objects.filter(is_active=True).order_by('-created_at')[:10]

        context = {
            'is_applicant': True,
            'applicant': applicant,
            'resumes': resumes,
            'available_jobs': available_jobs,
        }
        return render(request, 'main/applicant_dashboard.html', context)


# ==================== RECRUITER VIEWS ====================

class CreateJobView(LoginRequiredMixin, RecruiterRequiredMixin, CreateView):
    """Create a new job description"""
    model = JobDescription
    form_class = JobDescriptionForm
    template_name = 'main/create_job.html'
    
    def form_valid(self, form):
        job = form.save(commit=False)
        job.recruiter = self.request.user.recruiterprofile
        job.save()
        messages.success(self.request, 'Job posted successfully!')
        return redirect('view_job', job_id=job.id)


class JobDetailView(LoginRequiredMixin, DetailView):
    """View job details and matched candidates"""
    model = JobDescription
    template_name = 'main/view_job.html'
    context_object_name = 'job'
    pk_url_kwarg = 'job_id'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job = self.get_object()
        
        # Split required skills safely
        job_skills = []
        if job.required_skills:
            job_skills = [skill.strip() for skill in job.required_skills.split(',')]
        context['job_skills'] = job_skills
        
        # Check permissions and add matches if recruiter owns this job
        user = self.request.user
        if hasattr(user, 'recruiterprofile') and job.recruiter == user.recruiterprofile:
            context['is_recruiter'] = True
            context['matches'] = MatchResult.objects.filter(job=job).select_related(
                'resume', 'resume__applicant', 'resume__applicant__user'
            )
        else:
            context['is_recruiter'] = False
        
        return context
    
    def get(self, request, *args, **kwargs):
        job = self.get_object()
        
        # Permission check for recruiters
        if hasattr(request.user, 'recruiterprofile'):
            if job.recruiter != request.user.recruiterprofile:
                messages.error(request, 'You do not have permission to view this job.')
                return redirect('dashboard')
        
        return super().get(request, *args, **kwargs)


class EditJobView(LoginRequiredMixin, RecruiterRequiredMixin, UpdateView):
    """Edit job description"""
    model = JobDescription
    form_class = JobDescriptionForm
    template_name = 'main/edit_job.html'
    pk_url_kwarg = 'job_id'
    context_object_name = 'job'
    
    def get_success_url(self):
        return reverse('view_job', kwargs={'job_id': self.object.id})
    
    def form_valid(self, form):
        messages.success(self.request, 'Job updated successfully!')
        return super().form_valid(form)
    
    def get_object(self, queryset=None):
        job = super().get_object(queryset)
        # Verify ownership
        if job.recruiter != self.request.user.recruiterprofile:
            messages.error(self.request, 'You do not have permission to edit this job.')
            raise PermissionDenied("Not your job")
        return job


class ToggleJobStatusView(LoginRequiredMixin, RecruiterRequiredMixin, View):
    """Toggle job active/inactive status"""
    
    def post(self, request, job_id):
        job = get_object_or_404(JobDescription, id=job_id)
        
        if job.recruiter != request.user.recruiterprofile:
            messages.error(request, 'Permission denied.')
            return redirect('dashboard')
        
        job.is_active = not job.is_active
        job.save()
        status = 'activated' if job.is_active else 'deactivated'
        messages.success(request, f'Job {status} successfully!')
        return redirect('view_job', job_id=job.id)


class DeleteJobView(LoginRequiredMixin, RecruiterRequiredMixin, DeleteView):
    """Delete a job"""
    model = JobDescription
    template_name = 'main/delete_job.html'
    pk_url_kwarg = 'job_id'
    context_object_name = 'job'
    success_url = reverse_lazy('dashboard')
    
    def get_object(self, queryset=None):
        job = super().get_object(queryset)
        if job.recruiter != self.request.user.recruiterprofile:
            messages.error(self.request, 'Permission denied.')
            raise PermissionDenied("Not your job")
        return job
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Job deleted successfully!')
        return super().delete(request, *args, **kwargs)


class MatchCandidatesView(LoginRequiredMixin, RecruiterRequiredMixin, View):
    """Run matching algorithm for a job"""
    
    def post(self, request, job_id):
        job = get_object_or_404(JobDescription, id=job_id)
        
        if job.recruiter != request.user.recruiterprofile:
            messages.error(request, 'Permission denied.')
            return redirect('dashboard')
        
        # Get all resumes that haven't been matched for this job
        existing_resume_ids = MatchResult.objects.filter(job=job).values_list('resume_id', flat=True)
        resumes = Resume.objects.exclude(id__in=existing_resume_ids).select_related('applicant', 'applicant__user')

        if not resumes.exists():
            messages.info(request, 'No new resumes to match.')
            return redirect('view_job', job_id=job.id)

        # Initialize matching engine
        engine = MatchingEngine(use_ai=True)

        # Prepare job text
        job_text = f"{job.title} {job.description} {job.requirements} {job.responsibilities} {job.required_skills}"

        matched_count = 0
        for resume in resumes:
            # Extract text if not already done
            if not resume.extracted_text:
                try:
                    resume.file.seek(0)
                    resume.extracted_text = DocumentParser.extract_text(resume.file)
                    resume.is_processed = True
                    resume.save()
                except Exception as e:
                    continue

            # Calculate match
            result = engine.calculate_similarity(resume.extracted_text, job_text)

            # Save match result
            MatchResult.objects.create(
                resume=resume,
                job=job,
                similarity_score=result['similarity_score'],
                skills_match_score=result['skills_match_score'],
                experience_match_score=result['experience_match_score'],
                education_match_score=result['education_match_score'],
                overall_score=result['overall_score'],
                matched_skills=result['matched_skills'],
                missing_skills=result['missing_skills']
            )
            matched_count += 1

        messages.success(request, f'Matching complete! {matched_count} candidates processed.')
        return redirect('view_job', job_id=job.id)


# ==================== APPLICANT VIEWS ====================

class UploadResumeView(LoginRequiredMixin, ApplicantRequiredMixin, CreateView):
    """Upload a resume"""
    model = Resume
    form_class = ResumeUploadForm
    template_name = 'main/upload_resume.html'
    success_url = reverse_lazy('dashboard')
    
    def form_valid(self, form):
        # Save form but don't commit yet
        self.object = form.save(commit=False)
        self.object.applicant = self.request.user.applicantprofile
        
        try:
            # Get the file
            file_obj = self.request.FILES['file']
            
            # Process the resume
            self.object.extracted_text = DocumentParser.extract_text(file_obj)
            self.object.is_processed = True
            
            # Extract skills
            from .matching_engine import TextPreprocessor
            preprocessor = TextPreprocessor()
            skills = preprocessor.extract_skills(self.object.extracted_text)
            self.object.skills = ', '.join(skills)
            
            # Save the object
            self.object.save()
            
            # Store for success message
            messages.success(self.request, 'Resume uploaded and processed successfully!')
            
            # Let CBV handle the redirect properly
            return super().form_valid(form)
            
        except Exception as e:
            messages.error(self.request, f'Error processing resume: {str(e)}')
            # Print full traceback for debugging
            import traceback
            print("RESUME UPLOAD ERROR:")
            print(traceback.format_exc())
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        """Handle form validation errors"""
        print("Form errors:", form.errors)
        return super().form_invalid(form)


class ResumeDetailView(LoginRequiredMixin, DetailView):
    """View resume details"""
    model = Resume
    template_name = 'main/view_resume.html'
    context_object_name = 'resume'
    pk_url_kwarg = 'resume_id'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        resume = self.get_object()
        
        # Get match results
        context['match_results'] = MatchResult.objects.filter(
            resume=resume
        ).select_related('job', 'job__recruiter')
        
        # Split skills
        skills_list = []
        if resume.skills:
            skills_list = [skill.strip() for skill in resume.skills.split(",") if skill.strip()]
        context['skills_list'] = skills_list
        
        return context
    
    def get_object(self, queryset=None):
        resume = super().get_object(queryset)
        user = self.request.user
        
        # Check permissions
        if hasattr(user, 'applicantprofile'):
            if resume.applicant != user.applicantprofile:
                messages.error(self.request, 'Permission denied.')
                raise PermissionDenied("Not your resume")
        elif hasattr(user, 'recruiterprofile'):
            # Recruiters can view if resume is matched to their jobs
            if not MatchResult.objects.filter(
                resume=resume,
                job__recruiter=user.recruiterprofile
            ).exists():
                messages.error(self.request, 'Permission denied.')
                raise PermissionDenied("Resume not matched to your jobs")
        
        return resume


class DeleteResumeView(LoginRequiredMixin, ApplicantRequiredMixin, DeleteView):
    """Delete a resume"""
    model = Resume
    template_name = 'main/delete_resume.html'
    pk_url_kwarg = 'resume_id'
    context_object_name = 'resume'
    success_url = reverse_lazy('dashboard')
    
    def get_object(self, queryset=None):
        resume = super().get_object(queryset)
        if resume.applicant != self.request.user.applicantprofile:
            messages.error(self.request, 'Permission denied.')
            raise PermissionDenied("Not your resume")
        return resume
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Resume deleted successfully!')
        return super().delete(request, *args, **kwargs)


class BrowseJobsView(LoginRequiredMixin, ListView):
    """Browse available jobs"""
    model = JobDescription
    template_name = 'main/browse_jobs.html'
    context_object_name = 'jobs'
    
    def get_queryset(self):
        jobs = JobDescription.objects.filter(is_active=True).order_by('-created_at')
        
        query = self.request.GET.get('q')
        if query:
            jobs = jobs.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(required_skills__icontains=query) |
                Q(recruiter__company_name__icontains=query)
            )
        return jobs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add skills_list to each job
        for job in context['jobs']:
            if job.required_skills:
                job.skills_list = [skill.strip() for skill in job.required_skills.split(',')]
            else:
                job.skills_list = []
        
        context['query'] = self.request.GET.get('q', '')
        return context


class GetMatchDetailsView(LoginRequiredMixin, View):
    """Get match details as JSON"""
    
    def get(self, request, match_id):
        match = get_object_or_404(MatchResult, id=match_id)
        
        # Check permission
        if hasattr(request.user, 'recruiterprofile'):
            if match.job.recruiter != request.user.recruiterprofile:
                return JsonResponse({'error': 'Permission denied'}, status=403)
        elif hasattr(request.user, 'applicantprofile'):
            if match.resume.applicant != request.user.applicantprofile:
                return JsonResponse({'error': 'Permission denied'}, status=403)
        
        data = {
            'overall_score': match.overall_score,
            'similarity_score': match.similarity_score,
            'skills_match_score': match.skills_match_score,
            'experience_match_score': match.experience_match_score,
            'education_match_score': match.education_match_score,
            'matched_skills': match.matched_skills,
            'missing_skills': match.missing_skills,
        }
        
        return JsonResponse(data)