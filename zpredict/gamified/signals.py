from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from .models import GameProfile, QuestLog
from .services import GamificationService

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_game_profile(sender, instance, created, **kwargs):
    """Automatically create a game profile when a new user is created"""
    if created:
        # Create the game profile
        profile, _ = GameProfile.objects.get_or_create(user=instance)
        
        # Log the registration quest
        QuestLog.objects.create(
            user=instance,
            quest_type='registration',
            quest_name='Welcome to Zpredict!',
            description='Successfully registered an account',
            xp_earned=10,
            coins_earned=10,
            status='completed'
        )
        
        # Award initial XP for registration
        GamificationService.award_xp(
            instance,
            amount=10,
            quest_name='Account Created',
            quest_type='registration'
        )

def user_logged_in(sender, request, user, **kwargs):
    """Handle user login events"""
    # Update login streak
    streak_update = GamificationService.update_login_streak(user)
    
    # Log the login quest
    QuestLog.objects.create(
        user=user,
        quest_type='login',
        quest_name='Daily Login',
        description=f'Logged in (streak: {streak_update["streak_days"]} days)',
        xp_earned=5 if streak_update['streak_increased'] else 2,
        coins_earned=2 if streak_update['streak_increased'] else 0,
        status='completed'
    )
    
    # Check for achievements
    GamificationService.check_achievements(user, 'login')

# Connect the login signal
from django.contrib.auth.signals import user_logged_in as auth_user_logged_in
auth_user_logged_in.connect(user_logged_in)

@receiver(post_save, sender=QuestLog)
def log_quest_completion(sender, instance, created, **kwargs):
    """Handle quest completion events"""
    if created and instance.status == 'completed':
        # Update user's game profile based on quest type
        if instance.quest_type == 'prediction':
            GamificationService.increment_prediction_count(instance.user)
        elif instance.quest_type == 'chat':
            GamificationService.increment_chat_count(instance.user)

# Connect the signals
post_save.connect(create_user_game_profile, sender=User)
post_save.connect(log_quest_completion, sender=QuestLog)
