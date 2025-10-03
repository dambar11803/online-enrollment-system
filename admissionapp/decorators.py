from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from .models import PersonalInfo, EducationalInfo


def profile_complete_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        user = request.user
        personal_done = PersonalInfo.objects.filter(user=user).exists()
        educational_done = EducationalInfo.objects.filter(user=user).exists()

        if not personal_done:
            messages.warning(request, "Please, Complete Your Personal Information")
            return redirect("personal_info")

        if not educational_done:
            messages.warning(request, "Please, Add at least one Educational Record")
            return redirect("educational_info")

        return view_func(request, *args, **kwargs)

    return _wrapped
