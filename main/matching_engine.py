import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import docx
import PyPDF2
import zipfile
from docx import Document
from io import BytesIO


class DocumentParser:
    @staticmethod
    def extract_text(file_obj):
        """
        Extract text from DOCX/PDF files.
        Handles corrupted DOCX files gracefully.
        """
        file_obj.seek(0)
        
        # Handle both file objects and file paths
        file_name = getattr(file_obj, 'name', '')
        if not file_name and hasattr(file_obj, 'filename'):
            file_name = file_obj.filename
        
        if file_name.endswith('.docx'):
            return DocumentParser._extract_docx(file_obj)
        elif file_name.endswith('.pdf'):
            return DocumentParser._extract_pdf(file_obj)
        else:
            raise ValueError(f"Unsupported file format: {file_name}")

    @staticmethod
    def _extract_docx(file_obj):
        """Extract text from DOCX with corruption handling"""
        try:
            doc = Document(file_obj)
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            return '\n'.join(paragraphs)
            
        except (zipfile.BadZipFile, Exception) as e:
            print(f"Standard DOCX parsing failed ({e}), trying fallback...")
            return DocumentParser._extract_docx_fallback(file_obj)

    @staticmethod
    def _extract_docx_fallback(file_obj):
        """Manual extraction from corrupted DOCX ZIP structure"""
        try:
            file_obj.seek(0)
            content = file_obj.read()
            
            with zipfile.ZipFile(BytesIO(content)) as zf:
                xml_data = zf.read('word/document.xml')
                
                import xml.etree.ElementTree as ET
                root = ET.fromstring(xml_data)
                
                texts = []
                for elem in root.iter():
                    if elem.tag.endswith('}t') and elem.text:
                        texts.append(elem.text)
                
                full_text = ''.join(texts)
                # Better formatting: split on sentence endings
                import re
                formatted = re.sub(r'([.!?])(\w)', r'\1\n\2', full_text)
                return formatted
                
        except Exception as e:
            raise ValueError(f"Could not extract from corrupted DOCX: {e}")

    @staticmethod
    def _extract_pdf(file_obj):
        """Extract text from PDF using PyPDF2"""
        try:
            file_obj.seek(0)
            pdf_reader = PyPDF2.PdfReader(file_obj)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            raise ValueError(f"Could not extract PDF: {e}")


class TextPreprocessor:
    """Preprocess text for matching"""

    # EXPANDED SKILL LIST - 50+ skills
    DEFAULT_SKILLS = [
        # Programming Languages
        'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'c', 
        'go', 'rust', 'php', 'ruby', 'swift', 'kotlin', 'scala', 'r',
        'matlab', 'perl', 'shell scripting', 'bash', 'powershell',
        
        # Web Development
        'html', 'css', 'react', 'angular', 'vue', 'svelte', 'next.js',
        'node.js', 'express', 'django', 'flask', 'fastapi', 'spring boot',
        'asp.net', 'laravel', 'rails', 'wordpress', 'web design',
        
        # Databases
        'sql', 'mysql', 'postgresql', 'mongodb', 'sqlite', 'redis',
        'elasticsearch', 'cassandra', 'dynamodb', 'firebase', 'oracle',
        'database design', 'database development',
        
        # Cloud & DevOps
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins',
        'git', 'github', 'gitlab', 'ci/cd', 'terraform', 'ansible',
        'linux', 'unix', 'windows server', 'nginx', 'apache',
        
        # Data & AI
        'machine learning', 'deep learning', 'ai', 'tensorflow', 
        'pytorch', 'scikit-learn', 'pandas', 'numpy', 'data analysis',
        'data science', 'computer vision', 'nlp', 'big data', 'spark',
        
        # Mobile
        'android', 'ios', 'react native', 'flutter', 'mobile development',
        
        # Other Technical
        'api development', 'rest api', 'graphql', 'microservices',
        'software engineering', 'software development', 'software documentation',
        'agile', 'scrum', 'jira', 'project management', 'system design',
        'oop', 'functional programming', 'testing', 'unit testing',
        'selenium', 'cybersecurity', 'networking', 'blockchain'
    ]

    @staticmethod
    def preprocess(text):
        text = text.lower()
        text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
        text = ' '.join(text.split())
        return text

    @classmethod
    def extract_skills(cls, text, skill_list=None):
        if skill_list is None:
            skill_list = cls.DEFAULT_SKILLS

        text_lower = text.lower()
        found_skills = []

        for skill in skill_list:
            # Use word boundary matching for accuracy
            pattern = r'(?:^|\s)' + re.escape(skill.lower()) + r'(?:\s|$|[^a-z])'
            if re.search(pattern, text_lower):
                found_skills.append(skill)

        return found_skills


class MatchingEngine:
    """Main matching engine"""

    def __init__(self, use_ai=False):
        self.use_ai = use_ai
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2)
        )

        if self.use_ai:
            self.ai_model = AIModelInterface()
            self.ai_model.load_model()

    def calculate_similarity(self, resume_text, job_description):
        preprocessor = TextPreprocessor()
        clean_resume = preprocessor.preprocess(resume_text)
        clean_job = preprocessor.preprocess(job_description)

        if self.use_ai:
            return self._ai_matching(clean_resume, clean_job, resume_text, job_description)

        return self._tfidf_matching(clean_resume, clean_job, resume_text, job_description)

    def _extract_experience_years(self, text):
        """Extract years of experience mentioned in text"""
        import re
        # Look for patterns like "5 years", "3+ years", "2020 - 2024"
        patterns = [
            r'(\d+)\+?\s*years?',
            r'(\d{4})\s*-\s*(?:present|current|\d{4})',
        ]
        years = []
        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            years.extend([int(m) if isinstance(m, str) and m.isdigit() else m for m in matches])
        return years

    def _extract_education_level(self, text):
        """Detect education level from text"""
        education_keywords = {
            'phd': 5, 'doctorate': 5, 'doctoral': 5,
            'masters': 4, 'mba': 4, 'msc': 4, 'ma': 4,
            'bachelors': 3, 'bs': 3, 'ba': 3, 'b.sc': 3, 'beng': 3,
            'associate': 2, 'diploma': 2,
            'high school': 1, 'secondary': 1
        }
        text_lower = text.lower()
        max_level = 0
        for keyword, level in education_keywords.items():
            if keyword in text_lower:
                max_level = max(max_level, level)
        return max_level

    def _tfidf_matching(self, clean_resume, clean_job, raw_resume, raw_job):
        try:
            # Use fit_transform on combined corpus for better results
            all_texts = [clean_job, clean_resume]
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            similarity_score = cosine_similarity(
                tfidf_matrix[0:1], tfidf_matrix[1:2]
            )[0][0]

            # Skills matching
            preprocessor = TextPreprocessor()
            resume_skills = preprocessor.extract_skills(raw_resume)
            job_skills = preprocessor.extract_skills(raw_job)

            if job_skills:
                matched_skills = [s for s in resume_skills if s in job_skills]
                missing_skills = [s for s in job_skills if s not in resume_skills]
                skills_score = len(matched_skills) / len(job_skills)
            else:
                matched_skills = resume_skills
                missing_skills = []
                skills_score = 0.0

            # Experience matching (NEW)
            resume_exp = self._extract_experience_years(raw_resume)
            job_exp = self._extract_experience_years(raw_job)
            if job_exp and resume_exp:
                # Simple scoring: any experience mentioned vs required
                exp_score = min(len(resume_exp), 2) / max(len(job_exp), 1)
            else:
                exp_score = 0.5  # Neutral if not specified

            # Education matching (NEW)
            resume_edu = self._extract_education_level(raw_resume)
            job_edu = self._extract_education_level(raw_job)
            if job_edu > 0 and resume_edu > 0:
                edu_score = min(resume_edu, job_edu) / max(job_edu, resume_edu)
            else:
                edu_score = 0.5  # Neutral if not specified

            # Weighted overall score
            overall_score = (
                similarity_score * 0.4 +      # Semantic similarity
                skills_score * 0.3 +           # Skills match
                exp_score * 0.2 +              # Experience match
                edu_score * 0.1                # Education match
            )

            return {
                'similarity_score': float(similarity_score),
                'skills_match_score': float(skills_score),
                'experience_match_score': float(exp_score),
                'education_match_score': float(edu_score),
                'overall_score': float(overall_score),
                'matched_skills': matched_skills,
                'missing_skills': missing_skills,
            }

        except Exception as e:
            return {
                'similarity_score': 0.0,
                'skills_match_score': 0.0,
                'experience_match_score': 0.0,
                'education_match_score': 0.0,
                'overall_score': 0.0,
                'matched_skills': [],
                'missing_skills': [],
                'error': str(e)
            }

    def _ai_matching(self, clean_resume, clean_job, raw_resume, raw_job):
        try:
            # Get semantic similarity from AI
            resume_emb, job_emb = self.ai_model.encode([clean_resume, clean_job])
            similarity = self.ai_model.calculate_similarity(resume_emb, job_emb)

            # Still use rule-based for skills/experience/education
            preprocessor = TextPreprocessor()
            resume_skills = preprocessor.extract_skills(raw_resume)
            job_skills = preprocessor.extract_skills(raw_job)

            if job_skills:
                matched_skills = [s for s in resume_skills if s in job_skills]
                missing_skills = [s for s in job_skills if s not in resume_skills]
                skills_score = len(matched_skills) / len(job_skills)
            else:
                matched_skills = resume_skills
                missing_skills = []
                skills_score = 0.0

            # Experience & Education
            exp_score = self._extract_experience_years(raw_resume)
            edu_score = self._extract_education_level(raw_resume)

            # AI-enhanced overall score
            overall_score = (
                float(similarity) * 0.5 +      # AI semantic similarity (higher weight)
                skills_score * 0.3 +
                (1.0 if exp_score else 0.5) * 0.1 +
                (1.0 if edu_score >= 3 else 0.5) * 0.1
            )

            return {
                'similarity_score': float(similarity),
                'skills_match_score': float(skills_score),
                'experience_match_score': float(exp_score) if isinstance(exp_score, (int, float)) else 0.5,
                'education_match_score': float(edu_score) if isinstance(edu_score, (int, float)) else 0.5,
                'overall_score': float(overall_score),
                'matched_skills': matched_skills,
                'missing_skills': missing_skills,
            }

        except Exception as e:
            return {
                'similarity_score': 0.0,
                'skills_match_score': 0.0,
                'experience_match_score': 0.0,
                'education_match_score': 0.0,
                'overall_score': 0.0,
                'matched_skills': [],
                'missing_skills': [],
                'error': str(e)
            }

    def rank_candidates(self, resumes_data, job_description):
        results = []

        for resume_data in resumes_data:
            match_result = self.calculate_similarity(
                resume_data['text'],
                job_description
            )
            match_result['resume_id'] = resume_data['id']
            match_result['applicant_name'] = resume_data.get('applicant_name', 'Unknown')
            results.append(match_result)

        results.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
        return results


class AIModelInterface:
    def __init__(self, model_name='sentence-bert'):
        self.model_name = model_name
        self.model = None

    def load_model(self):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def encode(self, texts):
        return self.model.encode(texts)

    def calculate_similarity(self, emb1, emb2):
        return float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))