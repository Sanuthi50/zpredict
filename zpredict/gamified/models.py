from django.db import models
from django.conf import settings
from django.utils import timezone

class GameProfile(models.Model):
    """Extended profile for gamification features"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='game_profile')
    level = models.IntegerField(default=1)
    xp = models.IntegerField(default=0)
    coins = models.IntegerField(default=100)
    streak_days = models.IntegerField(default=0)
    last_login_date = models.DateField(null=True, blank=True)
    total_predictions = models.IntegerField(default=0)
    total_chat_messages = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - Level {self.level}"

    def add_xp(self, amount):
        """Add XP and handle level ups"""
        self.xp += amount
        old_level = self.level
        new_level = self.calculate_level()
        
        if new_level > old_level:
            self.level = new_level
            # Award coins for level up
            self.coins += new_level * 50
            
        self.save()
        return new_level > old_level  # Return True if leveled up

    def calculate_level(self):
        """Calculate level based on XP (100 XP per level)"""
        return max(1, (self.xp // 100) + 1)

    def add_coins(self, amount):
        """Add coins to profile"""
        self.coins += amount
        self.save()

    def update_streak(self):
        """Update login streak"""
        today = timezone.now().date()
        
        if self.last_login_date:
            days_diff = (today - self.last_login_date).days
            if days_diff == 1:
                # Consecutive day
                self.streak_days += 1
            elif days_diff > 1:
                # Streak broken
                self.streak_days = 1
            # Same day login doesn't change streak
        else:
            # First login
            self.streak_days = 1
            
        self.last_login_date = today
        self.save()

class Achievement(models.Model):
    """Achievement definitions"""
    ACHIEVEMENT_TYPES = [
        ('first_prediction', 'First Prediction'),
        ('prediction_master', 'Prediction Master'),
        ('chat_starter', 'Chat Starter'),
        ('chat_master', 'Chat Master'),
        ('knowledge_seeker', 'Knowledge Seeker'),
        ('streak_warrior', 'Streak Warrior'),
        ('level_up', 'Level Up'),
        ('coin_collector', 'Coin Collector'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    achievement_type = models.CharField(max_length=50, choices=ACHIEVEMENT_TYPES)
    icon = models.CharField(max_length=50, default='fas fa-trophy')
    xp_reward = models.IntegerField(default=50)
    coin_reward = models.IntegerField(default=25)
    requirement_value = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class UserAchievement(models.Model):
    """User's earned achievements"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'achievement']

    def __str__(self):
        return f"{self.user.username} - {self.achievement.name}"

class QuestLog(models.Model):
    """Track user's quest/activity history"""
    QUEST_TYPES = [
        ('prediction', 'University Prediction'),
        ('career', 'Career Prediction'),
        ('chat', 'AI Chat'),
        ('login', 'Daily Login'),
        ('profile_update', 'Profile Update'),
    ]
    
    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('in_progress', 'In Progress'),
        ('failed', 'Failed'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quest_logs')
    quest_type = models.CharField(max_length=50, choices=QUEST_TYPES)
    quest_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    xp_earned = models.IntegerField(default=0)
    coins_earned = models.IntegerField(default=0)
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.quest_name}"

    class Meta:
        ordering = ['-completed_at']
