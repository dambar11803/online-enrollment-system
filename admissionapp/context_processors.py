from .models import PersonalInfo, EducationalInfo


def profile_flags(request):
    if not request.user.is_authenticated:
        return {}
    personal_done = PersonalInfo.objects.filter(user=request.user).exists()
    edu_done = EducationalInfo.objects.filter(user=request.user).exists()
    return {
        "personal_done": personal_done,
        "edu_done": edu_done,
        "profile_ready": personal_done and edu_done,
    }
