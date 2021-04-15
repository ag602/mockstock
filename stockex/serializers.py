from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.validators import UniqueValidator


class CreateUserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False)

    password1 = serializers.CharField(write_only=True, required=False, style={
                                     "input_type":   "password"})
    password2 = serializers.CharField(
        style={"input_type": "password"}, required=False, write_only=True, label="Confirm password")

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password1",
            "password2",
            "first_name",
            "last_name"
        ]
        # extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        username = validated_data["username"]
        print(username)
        email = validated_data["email"]
        password1 = validated_data["password1"]
        password2 = validated_data["password2"]
        first_name = validated_data["first_name"]
        last_name = validated_data["last_name"]
        # if (email and User.objects.filter(email=email).exclude(username=username).exists()):
        #     raise serializers.ValidationError(
        #         {"email": "Email addresses must be unique."})
        if password1 != password2:
            raise serializers.ValidationError(
                {"password": "The two passwords differ."})
        user = User(username=username, email=email, first_name=first_name,last_name=last_name)
        user.set_password(password1)
        user.save()
        return user