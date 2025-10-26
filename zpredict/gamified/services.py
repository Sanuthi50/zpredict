from django.contrib.auth.models import User
from django.db import transaction
from .models import GameProfile, Achievement, UserAchievement, QuestLog
import logging

logger = logging.getLogger(__name__)

class GamificationService:
    """Service class for handling gamification logic"""
    
    @staticmethod
    def get_or_create_game_profile(user):
        """Get or create game profile for user"""
        profile, created = GameProfile.objects.get_or_create(
            user=user,
            defaults={
                'level': 1,
                'xp': 0,
                'coins': 100,
                'streak_days': 0
            }
        )
        return profile, created

    @staticmethod
    def award_xp(user, amount, quest_name="General Activity", quest_type="general"):
        """Award XP to user and handle level ups"""
        try:
            with transaction.atomic():
                profile, _ = GamificationService.get_or_create_game_profile(user)
                
                # Add XP and check for level up
                leveled_up = profile.add_xp(amount)
                
                # Log the quest
                quest_log = QuestLog.objects.create(
                    user=user,
                    quest_type=quest_type,
                    quest_name=quest_name,
                    description=f"Earned {amount} XP",
                    xp_earned=amount,
                    status='completed'
                )
                
                # Check for achievements
                new_achievements = GamificationService.check_achievements(user, quest_type)
                
                return {
                    'xp_awarded': amount,
                    'total_xp': profile.xp,
                    'level': profile.level,
                    'leveled_up': leveled_up,
                    'new_achievements': new_achievements,
                    'quest_log_id': quest_log.id
                }
                
        except Exception as e:
            logger.error(f"Error awarding XP to user {user.id}: {str(e)}")
            return None

    @staticmethod
    def award_coins(user, amount, quest_name="Coin Reward"):
        """Award coins to user"""
        try:
            profile, _ = GamificationService.get_or_create_game_profile(user)
            profile.add_coins(amount)
            
            # Log the quest
            QuestLog.objects.create(
                user=user,
                quest_type='general',
                quest_name=quest_name,
                description=f"Earned {amount} coins",
                coins_earned=amount,
                status='completed'
            )
            
            return {
                'coins_awarded': amount,
                'total_coins': profile.coins
            }
            
        except Exception as e:
            logger.error(f"Error awarding coins to user {user.id}: {str(e)}")
            return None

    @staticmethod
    def update_login_streak(user):
        """Update user's login streak"""
        try:
            profile, _ = GamificationService.get_or_create_game_profile(user)
            old_streak = profile.streak_days
            profile.update_streak()
            
            # Award XP for login streak
            if profile.streak_days > old_streak:
                streak_xp = min(profile.streak_days * 5, 50)  # Max 50 XP
                GamificationService.award_xp(
                    user, 
                    streak_xp, 
                    f"Login Streak Day {profile.streak_days}",
                    "login"
                )
            
            return {
                'streak_days': profile.streak_days,
                'streak_increased': profile.streak_days > old_streak
            }
            
        except Exception as e:
            logger.error(f"Error updating login streak for user {user.id}: {str(e)}")
            return None

    @staticmethod
    def check_achievements(user, quest_type=None):
        """Check and award achievements based on user activity"""
        try:
            profile, _ = GamificationService.get_or_create_game_profile(user)
            new_achievements = []
            
            # Get all active achievements
            achievements = Achievement.objects.filter(is_active=True)
            
            # Get user's existing achievements
            user_achievement_ids = UserAchievement.objects.filter(
                user=user
            ).values_list('achievement_id', flat=True)
            
            for achievement in achievements:
                if achievement.id in user_achievement_ids:
                    continue  # User already has this achievement
                
                earned = False
                
                # Check different achievement types
                if achievement.achievement_type == 'first_prediction':
                    earned = profile.total_predictions >= achievement.requirement_value
                    
                elif achievement.achievement_type == 'prediction_master':
                    earned = profile.total_predictions >= achievement.requirement_value
                    
                elif achievement.achievement_type == 'chat_starter':
                    earned = profile.total_chat_messages >= achievement.requirement_value
                    
                elif achievement.achievement_type == 'chat_master':
                    earned = profile.total_chat_messages >= achievement.requirement_value
                    
                elif achievement.achievement_type == 'knowledge_seeker':
                    earned = profile.total_chat_messages >= achievement.requirement_value
                    
                elif achievement.achievement_type == 'streak_warrior':
                    earned = profile.streak_days >= achievement.requirement_value
                    
                elif achievement.achievement_type == 'level_up':
                    earned = profile.level >= achievement.requirement_value
                    
                elif achievement.achievement_type == 'coin_collector':
                    earned = profile.coins >= achievement.requirement_value
                
                if earned:
                    # Award the achievement
                    UserAchievement.objects.create(
                        user=user,
                        achievement=achievement
                    )
                    
                    # Award XP and coins
                    profile.add_xp(achievement.xp_reward)
                    profile.add_coins(achievement.coin_reward)
                    
                    new_achievements.append({
                        'name': achievement.name,
                        'description': achievement.description,
                        'icon': achievement.icon,
                        'xp_reward': achievement.xp_reward,
                        'coin_reward': achievement.coin_reward
                    })
            
            return new_achievements
            
        except Exception as e:
            logger.error(f"Error checking achievements for user {user.id}: {str(e)}")
            return []

    @staticmethod
    def increment_prediction_count(user):
        """Increment user's prediction count"""
        try:
            profile, _ = GamificationService.get_or_create_game_profile(user)
            profile.total_predictions += 1
            profile.save()
            
            # Check for prediction-related achievements
            return GamificationService.check_achievements(user, 'prediction')
            
        except Exception as e:
            logger.error(f"Error incrementing prediction count for user {user.id}: {str(e)}")
            return []

    @staticmethod
    def increment_chat_count(user):
        """Increment user's chat message count"""
        try:
            profile, _ = GamificationService.get_or_create_game_profile(user)
            profile.total_chat_messages += 1
            profile.save()
            
            # Check for chat-related achievements
            return GamificationService.check_achievements(user, 'chat')
            
        except Exception as e:
            logger.error(f"Error incrementing chat count for user {user.id}: {str(e)}")
            return []

    @staticmethod
    def get_user_stats(user):
        """Get comprehensive user game stats"""
        try:
            profile, _ = GamificationService.get_or_create_game_profile(user)
            
            # Get user achievements
            user_achievements = UserAchievement.objects.filter(
                user=user
            ).select_related('achievement').order_by('-earned_at')
            
            # Get recent quest logs
            recent_quests = QuestLog.objects.filter(
                user=user
            ).order_by('-completed_at')[:10]
            
            return {
                'profile': {
                    'level': profile.level,
                    'xp': profile.xp,
                    'coins': profile.coins,
                    'streak_days': profile.streak_days,
                    'total_predictions': profile.total_predictions,
                    'total_chat_messages': profile.total_chat_messages,
                    'xp_to_next_level': (profile.level * 100) - profile.xp,
                    'level_progress': (profile.xp % 100) / 100 * 100
                },
                'achievements': [
                    {
                        'name': ua.achievement.name,
                        'description': ua.achievement.description,
                        'icon': ua.achievement.icon,
                        'earned_at': ua.earned_at
                    } for ua in user_achievements
                ],
                'recent_quests': [
                    {
                        'quest_name': q.quest_name,
                        'quest_type': q.quest_type,
                        'xp_earned': q.xp_earned,
                        'coins_earned': q.coins_earned,
                        'completed_at': q.completed_at
                    } for q in recent_quests
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats for user {user.id}: {str(e)}")
            return None

    @staticmethod
    def get_leaderboard(limit=10):
        """Get top users by XP"""
        try:
            top_profiles = GameProfile.objects.select_related('user').order_by('-xp')[:limit]
            
            return [
                {
                    'username': profile.user.username,
                    'level': profile.level,
                    'xp': profile.xp,
                    'rank': idx + 1
                } for idx, profile in enumerate(top_profiles)
            ]
            
        except Exception as e:
            logger.error(f"Error getting leaderboard: {str(e)}")
            return []
