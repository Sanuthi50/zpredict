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
    path('admin/reprocess-pdf/', views.ReprocessPDFView.as_view(), name='reprocess_pdf'),
    path('admin/verify/', views.AdminVerifyView.as_view(), name='admin_verify'),

    # Prediction endpoints (integrated into single view)
    path('predictions/', views.PredictionAPIView.as_view(), name='predictions'),
    path('models/status/', views.ModelStatusAPIView.as_view(), name='model-status'),
    
    
    # Legacy endpoints (keeping for backward compatibility)
    path('predictions/save/', views.SavePredictionAPIView.as_view(), name='save-prediction'),
    path('predictions/saved/<int:prediction_id>/', views.SavePredictionAPIView.as_view(), name='delete-saved-prediction'),
    path('predictions/history/', views.PredictionHistoryAPIView.as_view(), name='prediction-history'),
]  

