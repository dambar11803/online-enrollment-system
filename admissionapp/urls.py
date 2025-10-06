from django.urls import path 
from django.contrib.auth import views as auth_views  
from . import views
from .views import (
    AddCourseView,
    CourseListView,
    CourseUpdateView,
    CourseDeleteView,
    CourseDetailView,
)

urlpatterns = [
    path("", views.login_page, name="login_page"),
    path("register/", views.register, name="register"),
    path("redirect/", views.custom_redirect_url, name="custom_redirect_url"),
    path("logout/", views.log_out, name="logout"),
    path("activate/<uidb64>/<token>/", views.activate, name="activate"),
    path("student-dashboard/", views.student_dashboard, name="student_dashboard"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("course/add/", AddCourseView.as_view(), name="add_course"),
    path("course-list/", CourseListView.as_view(), name="course_list"),
    path("course/update/<int:pk>/", CourseUpdateView.as_view(), name="course_update"),
    path("course/delete/<int:pk>/", CourseDeleteView.as_view(), name="course_delete"),
    path("course/detail/<int:pk>/", CourseDetailView.as_view(), name="course_detail"),
    path("personal-info/", views.PersonalInfo_view, name="personal_info"),
    path("educational-info/", views.EducationalInfo_view, name="educational_info"),
    path("user-profile/", views.profile, name="profile"),
    path(
        "personalinfo-detail/<int:pk>/",
        views.PersonalInfo_Detail,
        name="personalinfo_detail",
    ),
    path(
        "educationalinfo-detail/<int:pk>/",
        views.EducationalInfo_Detail,
        name="educationalinfo_detail",
    ),
    path("education-list/", views.education_list_view, name="education_list"),
    path(
        "edit-personalinfo/<int:pk>/",
        views.edit_personal_info,
        name="edit_personalinfo",
    ),
    path(
        "edit-educationalinfo/<int:pk>/",
        views.edit_educational_info,
        name="edit_educationalinfo",
    ),
    path("select-course/<int:pk>/", views.select_course, name="select_course"),
    path("apply-course/<int:pk>/", views.apply_course, name="apply_course"),
    path("application-list/", views.application_list, name="application_list"),
    path(
        "course-application-list/",
        views.course_application_list,
        name="course_application_list",
    ),
    path(
        "course-application-detail/<int:pk>/",
        views.course_applicant_detail,
        name="course_applicant_detail",
    ),
    path(
        "approval-rejection/<int:pk>/",
        views.approval_rejection,
        name="approval_rejection",
    ),
    path(
        "reason-to-reject/<int:pk>/", views.reason_to_rejection, name="reason_to_reject"
    ),
    path(
        "re-submit-application/<int:pk>/",
        views.re_submit_application,
        name="re_submit_application",
    ),
    path("reports/", views.reports, name="reports"),
    path(
        "total-applications/",
        views.total_applications_report,
        name="total_applications",
    ),
    path("total-approved/", views.total_approved_report, name="total_approved"),
    path("total-pending/", views.total_pending_report, name="total_pending"),
    path("total-rejected/", views.total_rejected_report, name="total_rejected"),
    path(
        "reports/export-total-application/",
        views.export_total_applications,
        name="export_total_applications",
    ),
    path(
        "export-approved-application/",
        views.export_approved_applications,
        name="export_approved_applications",
    ),
    path(
        "export-rejected-application/",
        views.export_rejected_applications,
        name="export_rejected_applications",
    ),
    path(
        "pay/khalti/init/<int:application_id>/",
        views.khalti_initiate,
        name="khalti_initiate",
    ),
    path("pay/khalti/return/", views.khalti_return, name="khalti_return"),
    path("pay/khalti/verify/", views.khalti_verify, name="khalti_verify"),
    path('contact/', views.contact, name='contact'),
     
    # Password change URLs
    path('password_change/', 
         auth_views.PasswordChangeView.as_view(template_name='password_change/password_change_form.html'), 
         name='password_change'),
    path('password_change/done/', 
         auth_views.PasswordChangeDoneView.as_view(template_name='password_change/password_change_done.html'), 
         name='password_change_done'),
    
    #password reset
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="password_reset/password_reset_form.html",
            email_template_name="password_reset/password_reset_email.html",
            subject_template_name="password_reset/password_reset_subject.txt",
            success_url="/password-reset/done/",
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="password_reset/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="password_reset/password_reset_confirm.html",
            success_url="/reset/complete/",
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="password_reset/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    
   
    
]
