from django import forms
from .models import (
    CustomUser,
    CourseDetails,
    PersonalInfo,
    EducationalInfo,
    Application,
)
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import RegexValidator

# from django.contrib.auth.models import User

phone_regex = RegexValidator(
    regex=r"^\d{10}$", message="Phone number must be 10 digits long numbers."
)


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    mobile = forms.CharField(
        max_length=10, validators=[phone_regex], help_text="10 digits mobile number"
    )
    # profile_pic = forms.ImageField(required=False)

    class Meta:
        model = CustomUser
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "mobile",
            "password1",
            "password2",
        ]

    def save(self, commit=False):
        user = super().save(commit=False)
        user.is_active = False
        if commit:
            user.save()
        return user


# ---------------
# Course Details
# ----------------
# class CourseDetailsForm(forms.ModelForm):
#     class Meta:
#         model = CourseDetails
#         fields = ['degree','course_name','course_code','course_duration','total_seats','course_fee']


# ----------------------
# Personal Info
# ----------------------
class PersonalInfoForm(forms.ModelForm):
    dob = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )

    class Meta:
        model = PersonalInfo
        fields = [
            "dob",
            "gender",
            "address",
            "mother",
            "father",
            "grandfather",
            "citizenship_no",
            "profile_pic",
            "ctz_file",
        ]
        widgets = {
            "gender": forms.Select(attrs={"class": "form-select"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "mother": forms.TextInput(attrs={"class": "form-control"}),
            "father": forms.TextInput(attrs={"class": "form-control"}),
            "grandfather": forms.TextInput(attrs={"class": "form-control"}),
            "citizenship_no": forms.TextInput(attrs={"class": "form-control"}),
            "profile_pic": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "ctz_file": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


# ----------------------
# Educational Info
# ----------------------
class EducationalInfoForm(forms.ModelForm):
    class Meta:
        model = EducationalInfo
        fields = [
            "level",
            "faculty",
            "course_name",
            "university_name",
            "college_name",
            "passed_year",
            "grade_percent",
            "upload_transcript1",
            "upload_transcript2",
            "upload_character",
            "upload_license",
            "upload_other",
            "upload_other1",
        ]
        widgets = {
            "level": forms.Select(attrs={"class": "form-select"}),
            "faculty": forms.Select(attrs={"class": "form-select"}),
            "course_name": forms.TextInput(attrs={"class": "form-control"}),
            "university_name": forms.Select(attrs={"class": "form-select"}),
            "college_name": forms.TextInput(attrs={"class": "form-control"}),
            "passed_year": forms.NumberInput(
                attrs={"class": "form-control", "min": 1990}
            ),
            "grade_percent": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": 0, "max": 100}
            ),
            "upload_transcript1": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),
            "upload_transcript2": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),
            "upload_character": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),
            "upload_license": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "upload_other": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "upload_other1": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


# ----------------------
# Course Details
# ----------------------
class CourseDetailsForm(forms.ModelForm):
    class Meta:
        model = CourseDetails
        fields = [
            "degree",
            "course_name",
            "course_full_name",
            "course_code",
            "course_duration",
            "total_seats",
            "course_fee",
            "course_desc",
            "min_requirement",
            "bg_pic",
        ]
        widgets = {
            "degree": forms.Select(attrs={"class": "form-select"}),
            "course_name": forms.TextInput(attrs={"class": "form-control"}),
            "course_full_name": forms.TextInput(attrs={"class": "form-control"}),
            "course_code": forms.TextInput(attrs={"class": "form-control"}),
            "course_duration": forms.Select(attrs={"class": "form-select"}),
            "total_seats": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "seats_filled": forms.NumberInput(
                attrs={"class": "form-control", "min": 0}
            ),
            "course_fee": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": 0}
            ),
        }

    def clean(self):
        cleaned = super().clean()
        total = cleaned.get("total_seats")
        filled = cleaned.get("seats_filled")
        if total is not None and filled is not None and filled > total:
            self.add_error("seats_filled", "Seats filled cannot exceed total seats.")
        return cleaned


# -----------------------------------
# Application Form
# ------------------------------------


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ["application_no", "application_status"]


# -----------------------------------
# Reason to Rejection Form
# ------------------------------------


class RejectReasonForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ["reason_to_reject"]

        widgets = {
            "reason_to_reject": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter reason for rejection...",
                }
            ),
        }
