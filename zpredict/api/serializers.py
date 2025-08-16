from rest_framework import serializers
class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['id', 'first_name', 'last_name', 'email', 'username', 'password', 'date_joined', 'active']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        student = Student(**validated_data)
        student.set_password(validated_data['password'])
        student.save()
        return student