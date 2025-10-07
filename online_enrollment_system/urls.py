# online_enrollment_system/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("", include("admissionapp.urls")),
    path("pay/", include("admissionapp.esewa_urls")),
    path("pay/", include("admissionapp.khalti_urls"),)
    # path("pay/", include("payment.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
