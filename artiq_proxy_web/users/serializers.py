from rest_framework import serializers


class LoginSerializer(serializers.Serializer):  # pylint: disable=abstract-method
    username = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)
