from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'prediction-sessions', views.PredictionSessionViewSet, basename='prediction-session')
router.register(r'saved-predictions', views.SavedPredictionViewSet, basename='saved-prediction')
router.register(r'career-sessions', views.CareerSessionViewSet, basename='career-session')
router.register(r'career-predictions', views.SavedCareerPredictionViewSet, basename='career-prediction')
router.register(r'admin-uploads', views.AdminUploadViewSet, basename='admin-upload')
router.register(r'chat-history', views.ChatHistoryViewSet, basename='chat-history')
router.register(r'feedback', views.FeedbackViewSet, basename='feedback')

urlpatterns = [
    # Include ViewSet routes
    path('', include(router.urls)),
    
    # Student endpoints
    path('chat/', views.ChatAPIView.as_view(), name='student-chat'),
    path('dashboard/', views.StudentDashboardView.as_view(), name='student-dashboard'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', views.register_student, name='register_student'),
    path('login/', views.login_student, name='login_student'),
    
    # Profile management endpoints
    path('auth/me/', views.get_current_user, name='get_current_user'),
    path('auth/update-profile/', views.update_user_profile, name='update_user_profile'),
    path('auth/change-password/', views.change_user_password, name='change_user_password'),
    path('auth/deactivate-account/', views.deactivate_user_account, name='deactivate_user_account'),
    path('auth/delete-account/', views.delete_user_account, name='delete_user_account'),
    
    # Admin Analytics endpoints
    path('admin/analytics/predictions/', views.admin_analytics_predictions, name='admin_analytics_predictions'),
    path('admin/analytics/careers/', views.admin_analytics_careers, name='admin_analytics_careers'),
    path('admin/analytics/users/', views.admin_analytics_users, name='admin_analytics_users'),

    # Admin endpoints
    path('admin/login/', views.admin_login, name='admin_login'),
    path('admin/register/', views.admin_register, name='admin_register'),
    path('admin/upload/', views.AdminUploadAPIView.as_view(), name='admin_upload'),
    path('admin/dashboard/', views.AdminDashboardAPIView.as_view(), name='admin_dashboard'),
    path('admin/reprocess-pdf/', views.ReprocessPDFView.as_view(), name='reprocess_pdf'),
    path('admin/verify/', views.AdminVerifyView.as_view(), name='admin_verify'),

    # Prediction endpoints (integrated into single view)
    path('predictions/', views.PredictionAPIView.as_view(), name='predictions'),
    path('predictions/save/', views.SavePredictionAPIView.as_view(), name='save-predictions'),
    path('models/status/', views.ModelStatusAPIView.as_view(), name='model-status'),

    # Recommendation endpoints
    path('recommendations/', views.RecommendationView.as_view(), name='recommendations'),
   
    
]  

