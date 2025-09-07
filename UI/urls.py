from django.urls import path
from .views import AdminView, AdminRegisterView, AdminLoginView, FeedbackManagementView, AdminProfileView
from . import views


urlpatterns = [
    path('admin-dashboard/', AdminView.as_view(), name= 'admin-dashboard'),  # Include API URLs for admin functionalities
    path('admin-register/', AdminRegisterView.as_view(), name='admin-register'),
    path('admin-reprocess/', views.AdminReprocessView.as_view(), name='admin-reprocess'),
    path('admin-analytics/', views.AdminAnalyticsView.as_view(), name='admin-analytics'),
    path('login/',views.AdminLoginView.as_view(),name='admin-login'),
    path('feedback-management/', FeedbackManagementView.as_view(), name='feedback-management'),
    path('admin-profile/', AdminProfileView.as_view(), name='admin-profile'),
   
]
