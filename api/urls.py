from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views




urlpatterns = [
    # Student endpoints
    path('chat/', views.ChatAPIView.as_view(), name='student-chat'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', views.register_student, name='register_student'),
    path('login/', views.login_student, name='login_student'),

    # Admin endpoints
    path('admin/login/', views.admin_login, name='admin_login'),
    path('admin/register/', views.admin_register, name='admin_register'),
    path('admin/upload/', views.AdminUploadAPIView.as_view(), name='admin_upload'),
    path('admin/dashboard/', views.AdminDashboardAPIView.as_view(), name='admin_dashboard'),
    path('admin/enhanced-dashboard/', views.EnhancedAdminDashboardView.as_view(), name='enhanced_admin_dashboard'),
    path('admin/reprocess-pdf/', views.ReprocessPDFView.as_view(), name='reprocess_pdf'),
    path('admin/verify/', views.AdminVerifyView.as_view(), name='admin_verify'),

    # Prediction endpoints (integrated into single view)
    path('predictions/', views.PredictionAPIView.as_view(), name='predictions'),
    path('models/status/', views.ModelStatusAPIView.as_view(), name='model-status'),
    
    
    # Legacy endpoints (keeping for backward compatibility)
    path('predictions/save/', views.SavePredictionAPIView.as_view(), name='save-prediction'),
    path('predictions/saved/<int:prediction_id>/', views.SavePredictionAPIView.as_view(), name='delete-saved-prediction'),
    path('predictions/history/', views.PredictionHistoryAPIView.as_view(), name='prediction-history'),

    # Recommendation endpoints
    path('recommendations/', views.RecommendationView.as_view(), name='recommendations'),
    
    # =============================
    # Feedback Management Endpoints
    # =============================
    path('feedback/', views.FeedbackListCreateView.as_view(), name='feedback-list-create'),
    path('feedback/<int:feedback_id>/', views.FeedbackDetailView.as_view(), name='feedback-detail'),
    path('feedback/user/', views.UserFeedbackView.as_view(), name='user-feedback'),
    path('admin/feedback/', views.AdminFeedbackManagementView.as_view(), name='admin-feedback-management'),
    path('admin/feedback/<int:feedback_id>/', views.AdminFeedbackManagementView.as_view(), name='admin-feedback-delete'),
    
    # =============================
    # Student Dashboard Endpoints
    # =============================
    path('student/dashboard/', views.StudentDashboardView.as_view(), name='student-dashboard'),
    path('student/profile/', views.StudentProfileView.as_view(), name='student-profile'),
    path('student/delete-account/', views.StudentDeleteAccountView.as_view(), name='student-delete-account'),
    
]  

