from django.urls import path
from .khalti_payments import khalti_initiate, khalti_return, khalti_verify


urlpatterns = [
    path(
        "khalti/init/<int:application_id>/",
        khalti_initiate,
        name="khalti_initiate",
    ),
    path("khalti/return/", khalti_return, name="khalti_return"),
    path("khalti/verify/", khalti_verify, name="khalti_verify"),
    
]
