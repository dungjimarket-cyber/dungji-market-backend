from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import Token
from django.contrib.auth import authenticate
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    JWT 토큰에 사용자 역할 정보를 추가하는 커스텀 시리얼라이저
    """
    
    def validate(self, attrs):
        try:
            data = super().validate(attrs)
            
            # 로그인 성공 후 판매자인 경우 사업자번호 검증
            user = authenticate(
                username=attrs.get('username'),
                password=attrs.get('password')
            )
            
            if user and user.role == 'seller':
                self._validate_seller_business_number(user)
                
        except serializers.ValidationError as e:
            # 기본 에러 메시지를 커스텀 메시지로 변경
            if 'No active account found with the given credentials' in str(e.detail.get('detail', '')):
                raise serializers.ValidationError(
                    {'detail': '아이디 또는 비밀번호가 일치하지 않습니다. 다시 확인해 주세요.'}
                )
            # 다른 에러는 그대로 전달
            raise e
        return data
    
    def _validate_seller_business_number(self, user):
        """판매자의 사업자번호 유효성 검사"""
        from .utils.business_verification_service import BusinessVerificationService
        from .models_verification import BusinessNumberVerification
        
        # 사업자번호가 없는 경우
        if not user.business_number:
            raise serializers.ValidationError({
                'detail': '등록된 사업자번호가 없습니다. 고객센터로 문의해주세요.',
                'business_verification_required': True
            })
        
        # 최근 검증 기록 확인 (24시간 이내)
        recent_verification = BusinessNumberVerification.objects.filter(
            user=user,
            business_number=user.business_number,
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).order_by('-created_at').first()
        
        # 최근 검증이 있고 유효한 경우 패스
        if recent_verification and recent_verification.status == 'valid':
            logger.info(f"판매자 {user.username} 사업자번호 검증 통과 (최근 검증 기록)")
            return
        
        # 실시간 검증 수행
        try:
            verification_service = BusinessVerificationService()
            result = verification_service.verify_business_number(user.business_number)
            
            # 검증 기록 저장
            BusinessNumberVerification.objects.create(
                user=user,
                business_number=user.business_number,
                status=result['status'],
                business_name=result['data'].get('business_name', '') if result['success'] else '',
                business_status=result['data'].get('business_status', '') if result['success'] else '',
                verified_at=timezone.now() if result['success'] and result['status'] == 'valid' else None,
                error_message=result.get('error_message', '') if not result['success'] else '',
                api_response=result.get('api_response', {})
            )
            
            # 검증 실패 시 로그인 차단
            if not result['success'] or result['status'] != 'valid':
                error_message = result['message']
                if result['status'] == 'invalid':
                    if '폐업' in error_message:
                        raise serializers.ValidationError({
                            'detail': '폐업한 사업자번호입니다. 사업자번호를 확인하거나 고객센터로 문의해주세요.',
                            'business_verification_failed': True,
                            'verification_status': 'closed'
                        })
                    else:
                        raise serializers.ValidationError({
                            'detail': '등록되지 않은 사업자번호입니다. 사업자번호를 확인하거나 고객센터로 문의해주세요.',
                            'business_verification_failed': True,
                            'verification_status': 'invalid'
                        })
                else:
                    raise serializers.ValidationError({
                        'detail': '사업자번호 검증 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
                        'business_verification_failed': True,
                        'verification_status': 'error'
                    })
            
            # 검증 성공 - 사용자 정보 업데이트
            if result['success'] and result['status'] == 'valid':
                user.is_business_verified = True
                user.save()
                logger.info(f"판매자 {user.username} 사업자번호 검증 성공")
                
        except Exception as e:
            logger.error(f"판매자 로그인 사업자번호 검증 오류 - user: {user.username}, error: {str(e)}")
            raise serializers.ValidationError({
                'detail': '사업자번호 검증 중 시스템 오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
                'business_verification_failed': True,
                'verification_status': 'system_error'
            })
    
    @classmethod
    def get_token(cls, user) -> Token:
        token = super().get_token(user)

        # 토큰에 사용자 역할 정보 추가
        # 슈퍼유저인 경우 role을 admin으로 설정
        if user.is_superuser:
            token['role'] = 'admin'
        else:
            token['role'] = user.role
        token['email'] = user.email
        token['is_superuser'] = user.is_superuser
        
        # 필요하다면 여기에 추가 정보(username 등)를 더 넣을 수 있습니다.
        token['username'] = user.username
        
        return token
