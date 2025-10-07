from django.db import models
from django.db.models import UniqueConstraint
from django.contrib.auth.models import AbstractUser
from django.core.validators import (
    RegexValidator,
    MinValueValidator,
    MaxValueValidator,
)
from django.core.exceptions import ValidationError
from decimal import Decimal  # noqa: F401
import os
import uuid
import mimetypes
import re
from django.conf import settings

# Try python-magic; fall back gracefully if not present or libmagic is missing
try:
    import magic  # type: ignore

    _MAGIC = magic.Magic(mime=True)  # may raise if libmagic missing
except Exception:  # noqa: BLE001
    _MAGIC = None


# ----------------------
# Utility Functions
# ----------------------
def validate_file_extensions(value):
    ext = os.path.splitext(value.name)[1].lower()
    valid_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".pdf"]
    if ext not in valid_extensions:
        raise ValidationError("Only supports: jpg, jpeg, png, bmp and pdf files")


def _safe_username(instance):
    username = getattr(getattr(instance, "user", None), "username", "") or getattr(
        instance, "username", "anon"
    )
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", username)


def user_profile_pics(instance, filename):
    """
    Profile images -> profile_pics/<username>/<username>_<uid>.<ext>
    """
    _, ext = os.path.splitext(filename)
    ext = ext.lower() or ".bin"
    uname = _safe_username(instance)
    uid = uuid.uuid4().hex[:8]
    return os.path.join("profile_pics", uname, f"{uname}_{uid}{ext}")


def validate_file_size(value):
    """Validate file size is not greater than 100 MB."""
    max_size = 100 * 1024 * 1024
    if value.size > max_size:
        raise ValidationError("File size must be equal or less than 100 MB.")


def validate_file_content(value):
    """
    Validate by MIME sniffing (python-magic if available),
    else fall back to UploadedFile.content_type or mimetypes guess.
    """
    mime_type = None

    # Best-effort sniff with python-magic
    if _MAGIC:
        head = value.read(2048)
        value.seek(0)
        try:
            mime_type = _MAGIC.from_buffer(head) or None
        except Exception:  # noqa: BLE001
            mime_type = None

    # Fallbacks
    if not mime_type and hasattr(value, "content_type"):
        mime_type = value.content_type or None
    if not mime_type:
        mime_type = mimetypes.guess_type(value.name)[0]

    if not mime_type or not (
        mime_type.startswith("image/") or mime_type == "application/pdf"
    ):
        raise ValidationError("Only images and PDFs are allowed.")


phone_regax = RegexValidator(
    regex=r"^\d{10}$",
    message="Phone Number must be 10 digits long.",
)


# ----------------------
# Models
# ----------------------
class CustomUser(AbstractUser):
    """Custom user model with mobile and email fields."""

    mobile = models.CharField(
        max_length=10,
        unique=True,
        null=True,
        blank=True,
        default=None,
        help_text="10 digit mobile number",
    )
    email = models.EmailField(unique=True)
    user_created_at = models.DateField(auto_now_add=True, blank=True, null=True)
    is_admin = models.BooleanField(default=False)
    is_user = models.BooleanField(default=True)

    def __str__(self):
        return self.username

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


# ------------------------------------
# Student Personal Info
# ------------------------------------
class PersonalInfo(models.Model):
    """Personal information for students."""

    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
    ]

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="personal_info",
    )
    dob = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    address = models.CharField(max_length=100, default="Itahari-20")
    mother = models.CharField(max_length=100, default="Sita")
    father = models.CharField(max_length=100, default="Ram")
    grandfather = models.CharField(max_length=100, default="Hari")
    citizenship_no = models.CharField(max_length=100, default="123789")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    profile_pic = models.ImageField(
        upload_to=user_profile_pics,
        validators=[validate_file_extensions, validate_file_size],
        blank=True,
        null=True,
    )
    ctz_file = models.FileField(
        upload_to="citizenship/",
        validators=[
            validate_file_extensions,
            validate_file_size,
            validate_file_content,
        ],
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"{self.user.username} - Personal Info"


# ------------------------------------
# Educational Details
# ------------------------------------
def educational_document_path(instance, filename):
    """Generate upload path for educational documents."""
    return f"uploads/{instance.user.username}/{filename}"


class EducationalInfo(models.Model):
    """Educational information for students."""

    LEVEL_CHOICES = [
        ("SEE", "SEE"),
        ("Plus2", "Plus2"),
        ("Bachelor", "Bachelor"),
        ("Master", "Master"),
    ]

    FACULTY_CHOICES = [
        ("Math", "Math"),
        ("Science", "Science"),
        ("Management", "Management"),
        ("IT", "IT"),
        ("Commerce", "Commerce"),
        ("Engineering", "Engineering"),
    ]

    UNIVERSITY_CHOICES = [
        ("Nepal Board", "Nepal Board"),
        ("Pokhara University", "Pokhara University"),
        ("Purbanchal University", "Purbanchal University"),
        ("Tribhuvan University", "Tribhuvan University"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="educational_infos",
    )
    level = models.CharField(max_length=50, choices=LEVEL_CHOICES, default="SEE")
    faculty = models.CharField(
        max_length=50, choices=FACULTY_CHOICES, default="Commerce"
    )
    course_name = models.CharField(max_length=50)
    university_name = models.CharField(
        max_length=100,
        choices=UNIVERSITY_CHOICES,
        default="Tribhuvan University",
    )
    college_name = models.CharField(max_length=100)
    passed_year = models.IntegerField(
        validators=[MinValueValidator(1990), MaxValueValidator(2100)]
    )
    grade_percent = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    upload_transcript1 = models.FileField(
        upload_to=educational_document_path,
        validators=[
            validate_file_extensions,
            validate_file_size,
            validate_file_content,
        ],
        help_text="(pdf or jpg)",
    )
    upload_transcript2 = models.FileField(
        upload_to=educational_document_path,
        validators=[
            validate_file_extensions,
            validate_file_size,
            validate_file_content,
        ],
        help_text="(pdf or jpg)",
        blank=True,
        null=True,
    )
    upload_character = models.FileField(
        upload_to=educational_document_path,
        validators=[
            validate_file_extensions,
            validate_file_size,
            validate_file_content,
        ],
        help_text="(pdf or jpg)",
    )
    upload_license = models.FileField(
        upload_to=educational_document_path,
        validators=[
            validate_file_extensions,
            validate_file_size,
            validate_file_content,
        ],
        help_text="(pdf or jpg)",
        blank=True,
    )
    upload_other = models.FileField(
        upload_to=educational_document_path,
        validators=[
            validate_file_extensions,
            validate_file_size,
            validate_file_content,
        ],
        help_text="(pdf or jpg)",
        blank=True,
    )
    upload_other1 = models.FileField(
        upload_to=educational_document_path,
        validators=[
            validate_file_extensions,
            validate_file_size,
            validate_file_content,
        ],
        help_text="(pdf or jpg)",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - Educational Detail"

    class Meta:
        constraints = [
            UniqueConstraint(fields=["user", "level"], name="uniq_user_level"),
        ]


# ------------------------------------
# Admin Related Models: CourseDetails
# ------------------------------------
def course_bg_upload_path(instance, filename):
    """Generate upload path for course background images."""
    return f"course_bg/{instance.course_code}/{filename}"


class CourseDetails(models.Model):
    """Course details model for managing courses."""

    DEGREE_CHOICES = [
        ("Master", "Master"),
        ("Bachelor", "Bachelor"),
        ("Plus2", "Plus2"),
    ]

    COURSE_DURATION = [
        ("2 Years", "2 Years"),
        ("3 Years", "3 Years"),
        ("4 Years", "4 Years"),
        ("5 Years", "5 Years"),
    ]

    degree = models.CharField(max_length=50, choices=DEGREE_CHOICES)
    course_name = models.CharField(max_length=10, unique=True,
                                   verbose_name="Course Name(short form)")
    course_full_name = models.CharField(max_length=100, unique=True, blank=True,
                                    verbose_name="Course Full Name")
    course_code = models.CharField(max_length=10, unique=True)
    course_duration = models.CharField(max_length=10, choices=COURSE_DURATION)
    total_seats = models.PositiveIntegerField(default=40)
    seats_filled = models.PositiveIntegerField(default=0)
    course_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    course_add_date = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    course_desc = models.TextField(blank=True, help_text="Overview, curriculum etc"
                                   ,verbose_name="Course Description")
    min_requirement = models.TextField(
        blank=True,
        verbose_name="Minimum Requirement",
        help_text="Write as bullet sentences",
    )
    bg_pic = models.ImageField(
        upload_to=course_bg_upload_path,
        blank=True,
        null=True,
        help_text="Upload a background image for the course",
        verbose_name="Background Picture"
    )

    @property
    def remaining_seat(self):
        return self.total_seats - self.seats_filled

    def __str__(self):
        return f"{self.degree} - {self.course_name}"


# -------------------------------
# Online Admission Application
# -------------------------------
def generate_application_no():
    """Generate unique application number."""
    return f"APP{uuid.uuid4().hex[:5].upper()}"


class Application(models.Model):
    """Application model for course admissions."""

    APP_STATUS = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("re-submit", "Re-submit"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="applications",
    )
    course = models.ForeignKey(
        "CourseDetails",
        on_delete=models.PROTECT,
        related_name="applications",
    )
    application_no = models.CharField(
        max_length=15,
        unique=True,
        default=generate_application_no,
    )
    application_status = models.CharField(
        max_length=50,
        choices=APP_STATUS,
        default="pending",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    approved_rejected_date = models.DateTimeField(null=True, blank=True)
    reason_to_reject = models.TextField(null=True, blank=True) 
    is_paid = models.BooleanField(default=False)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["user", "course"], name="unique_user_course"),
        ]

    def clean(self):
        if self.application_status == "approved" and self.course.remaining_seat <= 0:
            raise ValidationError("No seats available for this course.")

    def __str__(self):
        return f"{self.user.username} - {self.course.course_name}"

#-------------------------------
#Contactform Model 
#-------------------------------
class UserContact(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=13)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name}-message"
    
#----------------------------------------
#E-Sewa Payment Model 
#----------------------------------------

class PaymentDetail(models.Model):
    STATUS_CHOICES = [
        ("INITIATED", "Initiated"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="esewa_payments",
    )
    application = models.OneToOneField(
        "admissionapp.Application",
        on_delete=models.CASCADE,
        related_name="payment",)

    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],)
    
    is_payment_completed = models.BooleanField(default=False)

    # eSewa essentials
    transaction_uuid = models.CharField(max_length=64, unique=True)
    transaction_reference = models.CharField(max_length=64, null=True, blank=True)
    product_code = models.CharField(max_length=64, blank=True)  # e.g. EPAYTEST (sandbox)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="INITIATED")
    payment_method = models.CharField(
        max_length=50,
        choices=[("Khalti", "Khalti"), ("e-Sewa", "e-Sewa"), ("cash", "Cash")],
        default="e-Sewa",
    )
    payment_date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["application"], name="unique_payment_per_application"
            )
        ]

    def __str__(self):
        return f"{self.transaction_uuid} • {self.status}"    
    