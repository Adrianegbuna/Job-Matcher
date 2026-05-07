
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import RecruiterProfile, ApplicantProfile, JobDescription, Resume

class RecruiterRegistrationForm(UserCreationForm):
    """Form for recruiter registration"""
    email = forms.EmailField(required=True)
    company_name = forms.CharField(max_length=200)
    company_description = forms.CharField(widget=forms.Textarea, required=False)
    industry = forms.CharField(max_length=100, required=False)
    contact_phone = forms.CharField(max_length=20, required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'company_name']

class ApplicantRegistrationForm(UserCreationForm):
    """Form for applicant registration"""
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    phone = forms.CharField(max_length=20, required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)
    linkedin_url = forms.URLField(required=False)
    portfolio_url = forms.URLField(required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']

class JobDescriptionForm(forms.ModelForm):
    """Form for creating job descriptions"""
    class Meta:
        model = JobDescription
        fields = [
            'title', 'department', 'description', 'requirements', 
            'responsibilities', 'required_skills', 'required_experience',
            'education_level', 'location', 'employment_type', 'salary_range'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'requirements': forms.Textarea(attrs={'rows': 4}),
            'responsibilities': forms.Textarea(attrs={'rows': 4}),
            'required_skills': forms.TextInput(attrs={'placeholder': 'e.g., Python, Django, SQL, JavaScript'}),
        }

class ResumeUploadForm(forms.ModelForm):
    class Meta:
        model = Resume
        fields = ['title', 'file']
        widgets = {
            'file': forms.FileInput(attrs={'accept': '.pdf,.docx,.doc'})
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            ext = file.name.split('.')[-1].lower()
            if ext not in ['pdf', 'docx', 'doc']:
                raise forms.ValidationError('Only PDF and Word documents are allowed.')
        return file
