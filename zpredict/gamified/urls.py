from django.urls import path
from .views import HomeView, ChatView, LoginView, RegisterView
from . import views

urlpatterns = [
    # Main gamified pages
    path('', HomeView.as_view(), name='gamified_home'),
    path('login/', LoginView.as_view(), name='gamified_login'),
    path('register/', RegisterView.as_view(), name='gamified_register'),
    path('chat/', ChatView.as_view(), name='gamified_chat'),
    path('history-chatbot/', views.ChatHistoryView.as_view(), name='gamified_chat_history'),
    path('recommendation/', views.RecommendationView.as_view(), name='gamified_recommendation'),
    path('predict/', views.PredictionView.as_view(), name='gamified_predict'),
    path('student-profile/', views.ProfileView.as_view(), name='gamified_student_profile'),
    path('all-predictions/', views.AllPredictionsView.as_view(), name='gamified_all_predictions'),
    path('career-predictions/', views.CareerPredictionsView.as_view(), name='gamified_career_predictions'),

]
