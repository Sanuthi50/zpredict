from rest_framework import serializers
from .models import (
    User, PredictionSession, SavedPrediction, AdminUpload, 
    ChatHistory, Feedback,CareerSession, SavedCareerPrediction
)


# =============================
# User Serializers
# =============================
class UserSerializer(serializers.ModelSerializer):
    """Base user serializer"""
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'user_type', 'date_joined', 'active']
        read_only_fields = ['id', 'date_joined']


class StudentSerializer(serializers.ModelSerializer):
    """Student registration serializer"""
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'password', 'date_joined', 'active', 'user_type']
        extra_kwargs = {
            'password': {'write_only': True},
            'user_type': {'default': 'student'}
        }

    def create(self, validated_data):
        # Ensure user_type is set to student
        validated_data['user_type'] = 'student'
        student = User(**validated_data)
        student.set_password(validated_data['password'])
        student.save()
        return student


class AdminSerializer(serializers.ModelSerializer):
    """Admin registration serializer"""
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'password', 'date_joined', 'active', 'user_type']
        extra_kwargs = {
            'password': {'write_only': True},
            'user_type': {'default': 'admin'}
        }

    def create(self, validated_data):
        # Ensure user_type is set to admin
        validated_data['user_type'] = 'admin'
        validated_data['is_staff'] = True
        admin = User(**validated_data)
        admin.set_password(validated_data['password'])
        admin.save()
        return admin


class UserProfileSerializer(serializers.ModelSerializer):
    """User profile update serializer"""
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'user_type', 'date_joined', 'active']
        read_only_fields = ['id', 'user_type', 'date_joined']


# =============================
# Prediction Session Serializers
# =============================
class PredictionSessionSerializer(serializers.ModelSerializer):
    """Prediction session serializer"""
    student_name = serializers.ReadOnlyField(source='student.get_full_name')
    student_email = serializers.ReadOnlyField(source='student.email')
    
    class Meta:
        model = PredictionSession
        fields = [
            'id', 'student', 'student_name', 'student_email', 'year', 'z_score', 
            'stream', 'district', 'total_predictions_generated', 'confidence_level', 
            'predicted_at', 'active'
        ]
        read_only_fields = ['id', 'predicted_at', 'total_predictions_generated']

    def validate_year(self, value):
        if value < 1900 or value > 2100:
            raise serializers.ValidationError('Year must be between 1900 and 2100')
        return value

    def validate_z_score(self, value):
        if not (0 <= value <= 3):
            raise serializers.ValidationError('Z-score must be between 0 and 3')
        return value


class PredictionSessionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating prediction sessions"""
    class Meta:
        model = PredictionSession
        fields = ['year', 'z_score', 'stream', 'district']

    def validate_year(self, value):
        if value < 1900 or value > 2100:
            raise serializers.ValidationError('Year must be between 1900 and 2100')
        return value

    def validate_z_score(self, value):
        if not (0 <= value <= 3):
            raise serializers.ValidationError('Z-score must be between 0 and 3')
        return value


# =============================
# Saved Prediction Serializers
# =============================
class SavedPredictionSerializer(serializers.ModelSerializer):
    """Saved prediction serializer"""
    student_name = serializers.ReadOnlyField(source='student.get_full_name')
    session_info = serializers.ReadOnlyField(source='session.id')
    probability_percentage = serializers.ReadOnlyField()
    selection_likely = serializers.ReadOnlyField()
    
    class Meta:
        model = SavedPrediction
        fields = [
            'id', 'student', 'student_name', 'session', 'session_info',
            'university_name', 'course_name', 'predicted_cutoff', 
            'predicted_probability', 'probability_percentage', 'selection_likely',
            'aptitude_test_required', 'all_island_merit', 'recommendation',
            'rank_in_results', 'saved_at', 'notes', 'active'
        ]
        read_only_fields = ['id', 'saved_at', 'probability_percentage', 'selection_likely']

    def validate_predicted_probability(self, value):
        if not (0 <= value <= 1):
            raise serializers.ValidationError('Predicted probability must be between 0 and 1')
        return value

    def validate_predicted_cutoff(self, value):
        if value < 0:
            raise serializers.ValidationError('Predicted cutoff cannot be negative')
        return value


class SavedPredictionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating saved predictions"""
    class Meta:
        model = SavedPrediction
        fields = [
            'session', 'university_name', 'course_name', 'predicted_cutoff',
            'predicted_probability', 'aptitude_test_required', 'all_island_merit',
            'recommendation', 'rank_in_results', 'notes'
        ]

    def validate_predicted_probability(self, value):
        if not (0 <= value <= 1):
            raise serializers.ValidationError('Predicted probability must be between 0 and 1')
        return value

    def validate_predicted_cutoff(self, value):
        if value < 0:
            raise serializers.ValidationError('Predicted cutoff cannot be negative')
        return value


# =============================
# Admin Upload Serializers
# =============================
class AdminUploadSerializer(serializers.ModelSerializer):
    """Admin upload serializer"""
    admin_name = serializers.ReadOnlyField(source='admin.get_full_name')
    file_size_display = serializers.ReadOnlyField(source='get_file_size_display')
    
    class Meta:
        model = AdminUpload
        fields = [
            'id', 'admin', 'admin_name', 'pdf_file', 'original_filename',
            'file_size', 'file_size_display', 'vectorstore_path', 'uploaded_at',
            'processed_at', 'processing_status', 'active', 'description'
        ]
        read_only_fields = ['id', 'uploaded_at', 'file_size', 'file_size_display']


class AdminUploadCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating admin uploads"""
    class Meta:
        model = AdminUpload
        fields = ['pdf_file', 'description']

    def validate_pdf_file(self, value):
        if not value.name.lower().endswith('.pdf'):
            raise serializers.ValidationError('Only PDF files are allowed')
        return value


# =============================
# Chat History Serializers
# =============================
class ChatHistorySerializer(serializers.ModelSerializer):
    """Chat history serializer"""
    student_name = serializers.ReadOnlyField(source='student.get_full_name')
    
    class Meta:
        model = ChatHistory
        fields = ['id', 'student', 'student_name', 'question', 'answer', 'asked_at', 'active']
        read_only_fields = ['id', 'asked_at']


class ChatHistoryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating chat history"""
    class Meta:
        model = ChatHistory
        fields = ['question']


# =============================
# Feedback Serializers
# =============================
class FeedbackSerializer(serializers.ModelSerializer):
    """Feedback serializer"""
    student_name = serializers.ReadOnlyField(source='student.get_full_name')
    student_email = serializers.ReadOnlyField(source='student.email')
    rating_display = serializers.ReadOnlyField(source='get_rating_display')

    class Meta:
        model = Feedback
        fields = [
            'id', 'student', 'student_name', 'student_email', 'feedback', 
            'rating', 'rating_display', 'submitted_at', 'active'
        ]
        read_only_fields = ['id', 'submitted_at', 'student_name', 'student_email', 'rating_display']


class FeedbackCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating feedback"""
    class Meta:
        model = Feedback
        fields = ['feedback', 'rating']

    def validate_rating(self, value):
        if value is not None and value not in [1, 2, 3, 4, 5]:
            raise serializers.ValidationError('Rating must be between 1 and 5')
        return value


# =============================
# Career Recommendation Serializers
# =============================
class SkillSerializer(serializers.Serializer):
    """Serializer for skill data."""
    Element_Name = serializers.CharField()
    Data_Value = serializers.FloatField()


class AbilitySerializer(serializers.Serializer):
    """Serializer for ability data."""
    Element_Name = serializers.CharField()
    Data_Value = serializers.FloatField()


class RecommendationSerializer(serializers.Serializer):
    """Serializer for career recommendation data."""
    Sri_Lankan_Occupation = serializers.CharField()
    Number_of_Vacancies = serializers.IntegerField()
    ONET_SOC_Code = serializers.CharField()
    ONET_Title = serializers.CharField()
    Similarity_Score = serializers.FloatField()
    Skills = SkillSerializer(many=True)
    Abilities = AbilitySerializer(many=True)
    Combined_Score = serializers.FloatField()


# =============================
# Dashboard Serializers
# =============================
class DashboardStatsSerializer(serializers.Serializer):
    """Dashboard statistics serializer"""
    total_students = serializers.IntegerField()
    total_admins = serializers.IntegerField()
    total_uploads = serializers.IntegerField()
    total_chats = serializers.IntegerField()
    total_predictions = serializers.IntegerField()
    total_saved_predictions = serializers.IntegerField()
    total_feedbacks = serializers.IntegerField()
    pending_uploads = serializers.IntegerField()


class StudentDashboardSerializer(serializers.Serializer):
    """Student dashboard serializer"""
    user = UserSerializer()
    statistics = DashboardStatsSerializer()
    recent_sessions = PredictionSessionSerializer(many=True)
    recent_saved_predictions = SavedPredictionSerializer(many=True)


# =============================
# Career Session Serializers
# =============================
class CareerSessionSerializer(serializers.ModelSerializer):
    """Career session serializer"""
    student_name = serializers.ReadOnlyField(source='student.get_full_name')
    student_email = serializers.ReadOnlyField(source='student.email')
    
    class Meta:
        model = CareerSession
        fields = [
            'id', 'student', 'student_name', 'student_email', 'degree_program',
            'created_at', 'num_career_predictions', 'active'
        ]
        read_only_fields = ['id', 'created_at', 'num_career_predictions']


class CareerSessionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating career sessions"""
    class Meta:
        model = CareerSession
        fields = ['degree_program', 'num_career_predictions']


# =============================
# Saved Career Prediction Serializers
# =============================
class SavedCareerPredictionSerializer(serializers.ModelSerializer):
    """Saved career prediction serializer"""
    student_name = serializers.ReadOnlyField(source='student.get_full_name')
    session_info = serializers.ReadOnlyField(source='session.id')
    match_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = SavedCareerPrediction
        fields = [
            'id', 'student', 'student_name', 'session', 'session_info',
            'career_title', 'career_code', 'match_score', 'match_percentage',
            'recommended_level', 'saved_at', 'notes'
        ]
        read_only_fields = ['id', 'saved_at', 'match_percentage']

    def validate_match_score(self, value):
        if not (0 <= value <= 1):
            raise serializers.ValidationError('Match score must be between 0 and 1')
        return value


class SavedCareerPredictionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating saved career predictions"""
    session_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = SavedCareerPrediction
        fields = [
            'session_id', 'career_title', 'career_code', 'match_score',
            'recommended_level', 'notes'
        ]

    def validate_match_score(self, value):
        if not (0 <= value <= 1):
            raise serializers.ValidationError('Match score must be between 0 and 1')
        return value
    
    def validate_session_id(self, value):
        # Validate that the session exists and belongs to the current user
        try:
            session = CareerSession.objects.get(id=value)
            request = self.context.get('request')
            if request and hasattr(request, 'user') and session.student != request.user:
                raise serializers.ValidationError('Session does not belong to current user')
            return value
        except CareerSession.DoesNotExist:
            raise serializers.ValidationError('Career session does not exist')
    
    def create(self, validated_data):
        session_id = validated_data.pop('session_id')
        session = CareerSession.objects.get(id=session_id)
        validated_data['session'] = session
        return super().create(validated_data)