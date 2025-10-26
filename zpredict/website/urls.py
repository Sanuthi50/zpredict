from django.urls import path
from .views import HomeView, ChatView, LoginView, RegisterView
from . import views


urlpatterns = [
    path('', HomeView.as_view(), name='website_home'),  # Changed from 'home/' to ''
    path('login/', LoginView.as_view(), name='website_login'),
    path('register/', RegisterView.as_view(), name='website_register'),
    path('chat/', ChatView.as_view(), name='website_chat'),
    path('chat-history/', views.ChatHistoryView.as_view(), name='chat_history'),
    path('recommendation/', views.RecommendationView.as_view(), name='recommendation'),
    path('predict/', views.PredictionView.as_view(), name='predict'),
    path('student-profile/', views.ProfileView.as_view(), name='student_profile'),
    path('all-predictions/', views.AllPredictionsView.as_view(), name='all_predictions'),
    path('career-predictions/', views.CareerPredictionsView.as_view(), name='career_predictions'),
]
