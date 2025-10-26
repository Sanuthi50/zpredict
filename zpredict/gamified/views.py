from django.views.generic import TemplateView
from django.views import View
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
import json

class HomeView(View):
    def get(self, request):
        return render(request, 'gamifiedhome.html')

class ChatView(View):
    def get(self, request):
        return render(request, 'chatbot.html')

class LoginView(View):
    def get(self, request):
        return render(request, 'login.html')

class ProfileView(View):
    def get(self, request):
        return render(request, 'profile.html')

class RegisterView(View):
    def get(self, request):
        return render(request, 'register.html')

class ChatHistoryView(View):
    def get(self, request):
        return render(request, 'history-chatbot.html')

class RecommendationView(View):
    def get(self, request):
        return render(request, 'career.html')

class PredictionView(View):
    def get(self, request):
        return render(request, 'uni-prediction.html')

class AllPredictionsView(View):
    def get(self, request):
        return render(request, 'predictions.html')

class CareerPredictionsView(View):
    def get(self, request):
        return render(request, 'careerRecommendation.html')