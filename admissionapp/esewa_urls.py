# admissionapp/urls_payments.py or payment/urls.py
from django.urls import path
from .esewa_payments import esewa_initiate, esewa_success, esewa_failure

urlpatterns = [
    # path("esewa/initiate/<int:application_id>/", esewa_initiate, name="esewa_initiate"),
    # path("esewa/success/", esewa_success, name="esewa_success"),
    # path("esewa/failure/", esewa_failure, name="esewa_failure"),
     path('payment/esewa/initiate/<int:application_id>/', 
         esewa_initiate, 
         name='esewa_initiate'),
    
    path('payment/esewa/success/', 
         esewa_success, 
         name='esewa_success'),
    
    path('payment/esewa/failure/', 
         esewa_failure, 
         name='esewa_failure'),
]
