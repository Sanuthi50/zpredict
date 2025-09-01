from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError


def validate_file_extension(value):
    """Validate that uploaded file is a PDF"""
    if not value.name.lower().endswith('.pdf'):
        raise ValidationError('Only PDF files are allowed.')


# =============================
# Custom User Manager
# =============================
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        if extra_fields.get('user_type') != 'admin':
            raise ValueError('Superuser must have user_type=admin.')

        return self.create_user(email, password, **extra_fields)


# =============================
# Custom User Model
# =============================
class User(AbstractUser):
    USER_TYPES = [
        ('student', 'Student'),
        ('admin', 'Admin'),
    ]

    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='student')
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100, default='')
    last_name = models.CharField(max_length=100, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    # Remove username field; use email as the unique identifier
    username = None
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = CustomUserManager()

    def __str__(self):
        if self.user_type == 'student':
            return f"{self.first_name} {self.last_name} ({self.email})"
        return f"Admin: {self.first_name} {self.last_name} ({self.email})"

    @property
    def is_admin(self):
        return self.user_type == 'admin'

    @property
    def is_student(self):
        return self.user_type == 'student'


# =============================
# Prediction Session Model
# =============================
class PredictionSession(models.Model):
    CONFIDENCE_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    STREAM_CHOICES = [
        ('Biological Science', 'Biological Science'),
        ('Physical Science', 'Physical Science'),
        ('Commerce', 'Commerce'),
        ('Arts', 'Arts'),
        ('Engineering Technology', 'Engineering Technology'),
        ('Biosystems Technology', 'Biosystems Technology'),
        ('Other', 'Other'),
    ]

    DISTRICT_CHOICES = [
        ('COLOMBO', 'COLOMBO'),
        ('GAMPAHA', 'GAMPAHA'),
        ('KALUTARA', 'KALUTARA'),
        ('KANDY', 'KANDY'),
        ('MATALE', 'MATALE'),
        ('NUWARA ELIYA', 'NUWARA ELIYA'),
        ('GALLE', 'GALLE'),
        ('MATARA', 'MATARA'),
        ('HAMBANTOTA', 'HAMBANTOTA'),
        ('JAFFNA', 'JAFFNA'),
        ('KILINOCHCHI', 'KILINOCHCHI'),
        ('MANNAR', 'MANNAR'),
        ('VAVUNIYA', 'VAVUNIYA'),
        ('MULLAITIVU', 'MULLAITIVU'),
        ('BATTICALOA', 'BATTICALOA'),
        ('AMPARA', 'AMPARA'),
        ('TRINCOMALEE', 'TRINCOMALEE'),
        ('KURUNEGALA', 'KURUNEGALA'),
        ('PUTTALAM', 'PUTTALAM'),
        ('ANURADHAPURA', 'ANURADHAPURA'),
        ('POLONNARUWA', 'POLONNARUWA'),
        ('BADULLA', 'BADULLA'),
        ('MONERAGALA', 'MONERAGALA'),
        ('RATNAPURA', 'RATNAPURA'),
        ('KEGALLE', 'KEGALLE'),
    ]

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'student'},
        related_name='prediction_sessions'
    )
    # Student input data
    year = models.IntegerField(default=2024)
    z_score = models.FloatField(default=0.0)
    stream = models.CharField(max_length=50, choices=STREAM_CHOICES, default='Other')
    district = models.CharField(max_length=50, choices=DISTRICT_CHOICES, default='COLOMBO')

    # Session metadata
    total_predictions_generated = models.IntegerField(default=0)
    confidence_level = models.CharField(max_length=10, choices=CONFIDENCE_LEVELS, default='medium')
    predicted_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-predicted_at']

    def clean(self):
        if self.year < 1900 or self.year > 2100:
            raise ValidationError('Year must be between 1900 and 2100')
        if not (0 <= self.z_score <= 3):
            raise ValidationError('Z-score must be between 0 and 3')

    def __str__(self):
        return f"{self.student.email} - {self.stream} ({self.year})"


# =============================
# Saved Prediction Model
# =============================
class SavedPrediction(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'student'},
        related_name='saved_predictions'
    )
    session = models.ForeignKey(
        PredictionSession,
        on_delete=models.CASCADE,
        related_name='saved_predictions'
    )

    # Data from prediction model
    university_name = models.CharField(max_length=200, default='')
    course_name = models.CharField(max_length=200, default='')
    predicted_cutoff = models.FloatField(default=0.0, help_text="Predicted Z-score cutoff")
    predicted_probability = models.FloatField(default=0.0, help_text="Probability of selection (0-1)")
    aptitude_test_required = models.BooleanField(default=False)
    all_island_merit = models.BooleanField(default=True)
    recommendation = models.CharField(max_length=100, default='', help_text="Recommendation level, e.g., 'Recommended'")

    # Additional metadata
    rank_in_results = models.IntegerField(default=0, help_text="Rank when this prediction was generated")
    saved_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default='', help_text="Student's personal notes")
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-saved_at']
        unique_together = ['student', 'session', 'university_name', 'course_name']

    def clean(self):
        if not (0 <= self.predicted_probability <= 1):
            raise ValidationError('Predicted probability must be between 0 and 1')
        if self.predicted_cutoff < 0:
            raise ValidationError('Predicted cutoff cannot be negative')

    def __str__(self):
        return f"{self.course_name} at {self.university_name} - {self.student.email}"

    @property
    def probability_percentage(self):
        return self.predicted_probability * 100

    @property
    def selection_likely(self):
        return self.predicted_probability >= 0.5


# =============================
# Legacy Prediction Model (DEPRECATED - Use PredictionSession instead)
# =============================
# class Prediction(models.Model):
#     CONFIDENCE_LEVELS = [
#         ('low', 'Low'),
#         ('medium', 'Medium'),
#         ('high', 'High'),
#     ]

#     student = models.ForeignKey(
#         User,
#         on_delete=models.CASCADE,
#         limit_choices_to={'user_type': 'student'}
#     )
#     stream = models.CharField(max_length=100, default='')
#     year = models.IntegerField(default=2024)
#     z_score = models.FloatField(default=0.0)
#     confidence_level = models.CharField(max_length=10, choices=CONFIDENCE_LEVELS, default='medium')
#     predicted_at = models.DateTimeField(auto_now_add=True)
#     active = models.BooleanField(default=True)

#     class Meta:
#         ordering = ['-predicted_at']

#     def clean(self):
#         if self.year < 1900 or self.year > 2100:
#             raise ValidationError('Year must be between 1900 and 2100')

#     def __str__(self):
#         return f"{self.stream} - {self.year} ({self.student.email})"


# =============================
# Admin Upload Model
# =============================
class AdminUpload(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ]

    admin = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'admin'}
    )
    pdf_file = models.FileField(
        upload_to='ugc_pdfs/',
        max_length=500,
        validators=[validate_file_extension],
        default='ugc_pdfs/original_file.pdf'
    )
    original_filename = models.CharField(max_length=255, default='original_file.pdf')
    file_size = models.BigIntegerField(default=0, help_text="File size in bytes")
    vectorstore_path = models.CharField(max_length=500, blank=True, default='')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    active = models.BooleanField(default=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.original_filename} - {self.uploaded_at}"

    def get_file_size_display(self):
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


# =============================
# Chat History Model
# =============================
class ChatHistory(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'student'}
    )
    question = models.TextField(default='')
    answer = models.TextField(default="Try again later")
    asked_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-asked_at']
        verbose_name_plural = "Chat Histories"

    def __str__(self):
        return f"Chat by {self.student.email} - {self.asked_at}"


# =============================
# Feedback Model
# =============================
class Feedback(models.Model):
    RATING_CHOICES = [
        (1, 'Very Poor'),
        (2, 'Poor'),
        (3, 'Average'),
        (4, 'Good'),
        (5, 'Excellent'),
    ]

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'student'}
    )
    feedback = models.TextField(default='')
    rating = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Feedback from {self.student.email} - {self.submitted_at}"

# =============================
# Career Session Model
# =============================
class CareerSession(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'student'},
        related_name='career_sessions'
    )
    degree_program = models.CharField(max_length=200, default='', help_text="The degree program used for career prediction")
    created_at = models.DateTimeField(auto_now_add=True)
    num_career_predictions = models.IntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Career Session by {self.student.email} - {self.created_at}"


# =============================
# Saved Career Prediction Model
# =============================
class SavedCareerPrediction(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'student'},
        related_name='saved_career_predictions'
    )
    session = models.ForeignKey(
        CareerSession,
        on_delete=models.CASCADE,
        related_name='saved_predictions'
    )

    career_title = models.CharField(max_length=200, default='')
    career_code = models.CharField(max_length=20, default='', help_text="SOC/O*NET code")
    match_score = models.FloatField(default=0.0, help_text="Match score between 0 and 1")
    recommended_level = models.CharField(max_length=50, default='Recommended')
    saved_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-saved_at']
        unique_together = ['student', 'session', 'career_code']

    def clean(self):
        if not (0 <= self.match_score <= 1):
            raise ValidationError('Match score must be between 0 and 1')

    def __str__(self):
        return f"{self.career_title} ({self.career_code}) - {self.student.email}"

    @property
    def match_percentage(self):
        return self.match_score * 100
