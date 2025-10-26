from django.views.generic import TemplateView
from django.views import View
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
import json

class HomeView(TemplateView):
    template_name = 'index.html'

class ChatView(View):
    def get(self, request):
        return render(request, 'chat.html')

class LoginView(View):
    def get(self, request):
        return render(request, 'signIn.html')

class ProfileView(View):
    def get(self, request):
        return render(request, 'studentprofile.html')

class RegisterView(View):
    def get(self, request):
        return render(request, 'signup.html')

class ChatHistoryView(View):
    def get(self, request):
        return render(request, 'chat-history.html')

class RecommendationView(View):
    def get(self, request):
        return render(request, 'recommendation.html')

class PredictionView(View):
    def get(self, request):
        return render(request, 'predict.html')

class AllPredictionsView(View):
    def get(self, request):
        return render(request, 'all-predictions.html')

class CareerPredictionsView(View):
    def get(self, request):
        return render(request, 'career-predictions.html')