from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models_partner import (
    Partner, ReferralRecord, PartnerSettlement, 
    PartnerLink, PartnerNotification
)
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class PartnerSerializer(serializers.ModelSerializer):
    """파트너 정보 시리얼라이저"""
    
    referral_link = serializers.SerializerMethodField()
    total_referrals = serializers.SerializerMethodField()
    active_subscribers = serializers.SerializerMethodField()
    available_settlement_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = Partner
        fields = [
            'id', 'partner_name', 'partner_code', 'commission_rate',
            'bank_name', 'account_number', 'account_holder',
            'is_active', 'minimum_settlement_amount',
            'referral_link', 'total_referrals', 'active_subscribers',
            'available_settlement_amount', 'created_at'
        ]
        read_only_fields = ['id', 'partner_code', 'created_at']
    
    def get_referral_link(self, obj):
        return obj.get_referral_link()
    
    def get_total_referrals(self, obj):
        return obj.get_total_referrals()
    
    def get_active_subscribers(self, obj):
        return obj.get_active_subscribers()
    
    def get_available_settlement_amount(self, obj):
        return obj.get_available_settlement_amount()


class DashboardSummarySerializer(serializers.Serializer):
    """대시보드 요약 정보 시리얼라이저"""
    
    monthly_signup = serializers.IntegerField()
    active_subscribers = serializers.IntegerField()
    monthly_revenue = serializers.IntegerField()
    available_settlement = serializers.IntegerField()


class ReferralRecordSerializer(serializers.ModelSerializer):
    """추천 기록 시리얼라이저"""
    
    member_name = serializers.SerializerMethodField()
    member_phone = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = ReferralRecord
        fields = [
            'id', 'member_name', 'member_phone', 'joined_date',
            'subscription_status', 'subscription_amount', 'ticket_count',
            'ticket_amount', 'total_amount', 'commission_amount',
            'settlement_status', 'status'
        ]
    
    def get_member_name(self, obj):
        """회원 이름 마스킹 처리"""
        if obj.referred_user.nickname:
            name = obj.referred_user.nickname
        else:
            name = obj.referred_user.username
        
        if len(name) <= 1:
            return name
        elif len(name) == 2:
            return name[0] + "○"
        else:
            return name[0] + "○" * (len(name) - 2) + name[-1]
    
    def get_member_phone(self, obj):
        """전화번호 마스킹 처리"""
        phone = obj.referred_user.phone_number
        if not phone:
            return ""
        
        # 010-1234-5678 -> 010-****-5678 형태로 마스킹
        if len(phone) >= 11:
            return phone[:3] + "-****-" + phone[-4:]
        return phone
    
    def get_status(self, obj):
        """상태 한글 표시"""
        status_map = {
            'active': '활성',
            'cancelled': '해지',
            'paused': '휴면'
        }
        return status_map.get(obj.subscription_status, obj.subscription_status)


class PartnerSettlementSerializer(serializers.ModelSerializer):
    """파트너 정산 시리얼라이저"""
    
    partner_name = serializers.CharField(source='partner.partner_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = PartnerSettlement
        fields = [
            'id', 'partner_name', 'settlement_amount', 'tax_invoice_requested',
            'status', 'status_display', 'bank_name', 'account_number',
            'account_holder', 'requested_at', 'processed_at', 'memo'
        ]
        read_only_fields = ['id', 'requested_at', 'processed_at']


class PartnerSettlementRequestSerializer(serializers.ModelSerializer):
    """정산 요청 시리얼라이저"""
    
    class Meta:
        model = PartnerSettlement
        fields = ['settlement_amount', 'tax_invoice_requested', 'memo']
    
    def validate_settlement_amount(self, value):
        """정산 금액 검증"""
        partner = self.context['partner']
        
        # 최소 정산 금액 확인
        if value < partner.minimum_settlement_amount:
            raise serializers.ValidationError(
                f"최소 정산 금액은 {partner.minimum_settlement_amount:,}원입니다."
            )
        
        # 정산 가능 금액 확인
        available_amount = partner.get_available_settlement_amount()
        if value > available_amount:
            raise serializers.ValidationError(
                f"정산 가능 금액({available_amount:,}원)을 초과할 수 없습니다."
            )
        
        return value
    
    def create(self, validated_data):
        partner = self.context['partner']
        
        # 파트너 계좌 정보 복사
        settlement = PartnerSettlement.objects.create(
            partner=partner,
            bank_name=partner.bank_name,
            account_number=partner.account_number,
            account_holder=partner.account_holder,
            **validated_data
        )
        
        # 관련 추천 기록들의 정산 상태를 '요청됨'으로 변경
        ReferralRecord.objects.filter(
            partner=partner,
            settlement_status='pending'
        ).update(settlement_status='requested')
        
        return settlement


class PartnerLinkSerializer(serializers.ModelSerializer):
    """파트너 링크 시리얼라이저"""
    
    conversion_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = PartnerLink
        fields = [
            'id', 'original_url', 'short_code', 'short_url',
            'click_count', 'conversion_count', 'conversion_rate',
            'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'short_code', 'short_url', 'created_at']
    
    def get_conversion_rate(self, obj):
        """전환율 계산"""
        if obj.click_count == 0:
            return 0
        return round((obj.conversion_count / obj.click_count) * 100, 2)


class PartnerNotificationSerializer(serializers.ModelSerializer):
    """파트너 알림 시리얼라이저"""
    
    type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    
    class Meta:
        model = PartnerNotification
        fields = [
            'id', 'notification_type', 'type_display', 'title', 'message',
            'is_read', 'read_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PartnerStatsSerializer(serializers.Serializer):
    """파트너 통계 시리얼라이저"""
    
    period = serializers.CharField()
    signup_count = serializers.IntegerField()
    revenue = serializers.IntegerField()
    subscription_count = serializers.IntegerField()
    
    
class ExportDataSerializer(serializers.Serializer):
    """데이터 내보내기 시리얼라이저"""
    
    FORMAT_CHOICES = [
        ('excel', 'Excel'),
        ('csv', 'CSV')
    ]
    
    format = serializers.ChoiceField(choices=FORMAT_CHOICES, default='excel')
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    status_filter = serializers.ChoiceField(
        choices=ReferralRecord.SUBSCRIPTION_STATUS_CHOICES + (('all', '전체'),),
        default='all',
        required=False
    )
    
    def validate(self, data):
        """날짜 범위 검증"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError(
                    "시작 날짜는 종료 날짜보다 이전이어야 합니다."
                )
            
            # 최대 1년 범위 제한
            if (end_date - start_date).days > 365:
                raise serializers.ValidationError(
                    "최대 1년 범위까지만 내보내기가 가능합니다."
                )
        
        return data


class PartnerAccountSerializer(serializers.ModelSerializer):
    """파트너 계좌 정보 시리얼라이저"""
    
    masked_account_number = serializers.SerializerMethodField()
    
    class Meta:
        model = Partner
        fields = ['bank_name', 'masked_account_number', 'account_holder']
    
    def get_masked_account_number(self, obj):
        """계좌번호 마스킹 처리"""
        account = obj.account_number
        if not account or len(account) < 4:
            return account
        
        # 뒤 4자리만 보이도록 마스킹
        return "*" * (len(account) - 4) + account[-4:]


class PartnerAccountUpdateSerializer(serializers.ModelSerializer):
    """파트너 계좌 정보 업데이트 시리얼라이저"""
    
    class Meta:
        model = Partner
        fields = ['bank_name', 'account_number', 'account_holder']
    
    def validate_account_number(self, value):
        """계좌번호 형식 검증"""
        # 숫자와 하이픈만 허용
        import re
        if not re.match(r'^[\d-]+$', value):
            raise serializers.ValidationError(
                "계좌번호는 숫자와 하이픈(-)만 입력 가능합니다."
            )
        
        # 길이 검증 (일반적으로 10-20자리)
        clean_number = value.replace('-', '')
        if len(clean_number) < 10 or len(clean_number) > 20:
            raise serializers.ValidationError(
                "올바른 계좌번호 형식이 아닙니다."
            )
        
        return value