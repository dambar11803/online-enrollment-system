from django.contrib import admin
from .models import (
    CustomUser,
    CourseDetails,
    PersonalInfo,
    EducationalInfo,
    Application,
)

# Register your models here.


class CustomUserAdmin(admin.ModelAdmin):
    # Add new fields to the admin form
    list_display = ("username", "first_name", "last_name")


admin.site.register(CustomUser, CustomUserAdmin)


# ----------------
# CourseDetails Admin
# --------------------
class CourseDetailsAdmin(admin.ModelAdmin):
    list_display = ("degree", "course_name", "course_duration", "course_fee")


admin.site.register(CourseDetails, CourseDetailsAdmin)


# ----------------
# PersonalInfo Admin
# --------------------


class PersonalInfoAdmin(admin.ModelAdmin):
    list_display = ("father", "mother")


admin.site.register(PersonalInfo, PersonalInfoAdmin)

# ----------------
# EducationalInfo Admin
# --------------------


class EducationalInfoAdmin(admin.ModelAdmin):
    list_display = ("university_name", "level", "faculty", "user")

    def get_username(self, obj):
        return obj.user.username

    get_username.admin_order_field = "user__username"  # Makes column sortable
    # get_username.short_description = 'Username'


admin.site.register(EducationalInfo, EducationalInfoAdmin)

# -------------------------
# Application
# --------------------------


class ApplicationFormAdmin(admin.ModelAdmin):
    list_display = ("application_no", "application_status")


admin.site.register(Application, ApplicationFormAdmin)

