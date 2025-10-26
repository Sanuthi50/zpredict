from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
from .services import GamificationService
from .models import GameProfile, Achievement, UserAchievement, QuestLog

class GameStatsAPIView(APIView):
    """API endpoint for getting user game statistics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            stats = GamificationService.get_user_stats(request.user)
            if stats:
                return Response(stats, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'error': 'Failed to retrieve user stats'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AwardXPAPIView(APIView):
    """API endpoint for awarding XP to users"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            data = request.data
            amount = data.get('amount', 0)
            quest_name = data.get('quest_name', 'General Activity')
            quest_type = data.get('quest_type', 'general')
            
            if amount <= 0:
                return Response(
                    {'error': 'Amount must be greater than 0'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            result = GamificationService.award_xp(
                request.user, 
                amount, 
                quest_name, 
                quest_type
            )
            
            if result:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'error': 'Failed to award XP'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AwardCoinsAPIView(APIView):
    """API endpoint for awarding coins to users"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            data = request.data
            amount = data.get('amount', 0)
            quest_name = data.get('quest_name', 'Coin Reward')
            
            if amount <= 0:
                return Response(
                    {'error': 'Amount must be greater than 0'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            result = GamificationService.award_coins(
                request.user, 
                amount, 
                quest_name
            )
            
            if result:
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'error': 'Failed to award coins'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class LeaderboardAPIView(APIView):
    """API endpoint for getting leaderboard"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            limit = int(request.GET.get('limit', 10))
            leaderboard = GamificationService.get_leaderboard(limit)
            return Response({'leaderboard': leaderboard}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AchievementsAPIView(APIView):
    """API endpoint for getting user achievements"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # Get user's earned achievements
            user_achievements = UserAchievement.objects.filter(
                user=request.user
            ).select_related('achievement').order_by('-earned_at')
            
            # Get all available achievements
            all_achievements = Achievement.objects.filter(is_active=True)
            
            earned_ids = set(ua.achievement.id for ua in user_achievements)
            
            earned = [
                {
                    'id': ua.achievement.id,
                    'name': ua.achievement.name,
                    'description': ua.achievement.description,
                    'icon': ua.achievement.icon,
                    'xp_reward': ua.achievement.xp_reward,
                    'coin_reward': ua.achievement.coin_reward,
                    'earned_at': ua.earned_at,
                    'earned': True
                } for ua in user_achievements
            ]
            
            available = [
                {
                    'id': a.id,
                    'name': a.name,
                    'description': a.description,
                    'icon': a.icon,
                    'xp_reward': a.xp_reward,
                    'coin_reward': a.coin_reward,
                    'requirement_value': a.requirement_value,
                    'achievement_type': a.achievement_type,
                    'earned': False
                } for a in all_achievements if a.id not in earned_ids
            ]
            
            return Response({
                'earned_achievements': earned,
                'available_achievements': available
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class QuestLogAPIView(APIView):
    """API endpoint for getting user's quest history"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            limit = int(request.GET.get('limit', 20))
            quest_logs = QuestLog.objects.filter(
                user=request.user
            ).order_by('-completed_at')[:limit]
            
            quests = [
                {
                    'id': q.id,
                    'quest_type': q.quest_type,
                    'quest_name': q.quest_name,
                    'description': q.description,
                    'status': q.status,
                    'xp_earned': q.xp_earned,
                    'coins_earned': q.coins_earned,
                    'completed_at': q.completed_at
                } for q in quest_logs
            ]
            
            return Response({'quest_logs': quests}, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Django view functions for AJAX calls
@login_required
@csrf_exempt
def award_xp_view(request):
    """Django view for awarding XP"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            amount = data.get('amount', 0)
            quest_name = data.get('quest_name', 'General Activity')
            quest_type = data.get('quest_type', 'general')
            
            result = GamificationService.award_xp(
                request.user, 
                amount, 
                quest_name, 
                quest_type
            )
            
            if result:
                return JsonResponse(result)
            else:
                return JsonResponse({'error': 'Failed to award XP'}, status=500)
                
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def get_game_stats_view(request):
    """Django view for getting game stats"""
    try:
        stats = GamificationService.get_user_stats(request.user)
        if stats:
            return JsonResponse(stats)
        else:
            return JsonResponse({'error': 'Failed to retrieve stats'}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@csrf_exempt
def increment_prediction_view(request):
    """Django view for incrementing prediction count"""
    if request.method == 'POST':
        try:
            achievements = GamificationService.increment_prediction_count(request.user)
            return JsonResponse({
                'success': True,
                'new_achievements': achievements
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
@csrf_exempt
def increment_chat_view(request):
    """Django view for incrementing chat count"""
    if request.method == 'POST':
        try:
            achievements = GamificationService.increment_chat_count(request.user)
            return JsonResponse({
                'success': True,
                'new_achievements': achievements
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
@csrf_exempt
def update_login_streak_view(request):
    """Django view for updating login streak"""
    if request.method == 'POST':
        try:
            result = GamificationService.update_login_streak(request.user)
            return JsonResponse(result if result else {'error': 'Failed to update streak'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)
