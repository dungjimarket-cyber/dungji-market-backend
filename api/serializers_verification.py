from rest_framework import serializers
from .models_verification import PhoneVerification

class PhoneVerificationSerializer(serializers.ModelSerializer):
    """휴대폰 인증 시리얼라이저"""
    
    class Meta:
        model = PhoneVerification
        fields = [
            'id',
            'phone_number',
            'status',
            'purpose',
            'created_at',
            'expires_at',
            'verified_at',
        ]
        read_only_fields = [
            'id',
            'status',
            'created_at',
            'expires_at',
            'verified_at',
        ]

class SendVerificationSerializer(serializers.Serializer):
    """인증 코드 발송 요청 시리얼라이저"""
    
    phone_number = serializers.CharField(
        max_length=20,
        required=True,
        help_text='휴대폰 번호 (010-1234-5678 형식)'
    )
    purpose = serializers.ChoiceField(
        choices=['signup', 'reset_password', 'change_phone'],
        default='signup',
        help_text='인증 용도'
    )

class VerifyCodeSerializer(serializers.Serializer):
    """인증 코드 확인 요청 시리얼라이저"""
    
    phone_number = serializers.CharField(
        max_length=20,
        required=True,
        help_text='휴대폰 번호'
    )
    code = serializers.CharField(
        max_length=6,
        min_length=6,
        required=True,
        help_text='6자리 인증 코드'
    )
    purpose = serializers.ChoiceField(
        choices=['signup', 'reset_password', 'change_phone'],
        default='signup',
        help_text='인증 용도'
    )
    
    def validate_code(self, value):
        """인증 코드 형식 검증"""
        if not value.isdigit():
            raise serializers.ValidationError('인증 코드는 숫자만 입력 가능합니다.')
        return value