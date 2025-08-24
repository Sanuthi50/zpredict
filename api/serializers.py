from rest_framework import serializers
from .models import Feedback, User

class StudentSerializer(serializers.ModelSerializer):
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


class FeedbackSerializer(serializers.ModelSerializer):
    student_email = serializers.ReadOnlyField(source='student.email')

    class Meta:
        model = Feedback
        fields = ['id', 'student', 'student_email', 'feedback', 'rating', 'submitted_at', 'active']
        read_only_fields = ['submitted_at', 'student_email']