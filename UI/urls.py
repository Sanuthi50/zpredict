from django.urls import path
from .views import HomeView, ChatView, LoginView, RegisterView, AdminView, AdminRegisterView
from . import views


urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('chat/', ChatView.as_view(), name='chat'),
    path('admin-dashboard/', AdminView.as_view(), name= 'admin-dashboard'),  # Include API URLs for admin functionalities
    path('admin-register/', AdminRegisterView.as_view(), name='admin-register'),
    path('admin-reprocess/', views.AdminReprocessView.as_view(), name='admin-reprocess'),
    path('prediction/', views.PredictionView.as_view(), name='prediction'),
    path('career-prediction/', views.CareerPredictionView.as_view(), name='career-prediction'),
    
    # =============================
    # Student Dashboard URLs
    # =============================
    path('student-dashboard/', views.StudentDashboardView.as_view(), name='student-dashboard'),
    path('student-profile/', views.StudentProfileView.as_view(), name='student-profile'),
    
    # =============================
    # Feedback System URLs
    # =============================
    path('feedback/', views.FeedbackView.as_view(), name='feedback'),
    path('feedback-management/', views.FeedbackManagementView.as_view(), name='feedback-management'),
    
    # =============================
    # Enhanced Admin URLs
    # =============================
    path('enhanced-admin-dashboard/', views.EnhancedAdminDashboardView.as_view(), name='enhanced-admin-dashboard'),
]
