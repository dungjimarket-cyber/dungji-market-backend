"""
결제 관련 serializers
"""

from rest_framework import serializers
from .models_payment import Payment, RefundRequest
from django.contrib.auth import get_user_model

User = get_user_model()


class PaymentSerializer(serializers.ModelSerializer):
    """결제 정보 serializer"""
    
    class Meta:
        model = Payment
        fields = [
            'id', 'order_id', 'payment_method', 'amount', 'product_name',
            'status', 'buyer_name', 'buyer_tel', 'buyer_email', 'tid',
            'created_at', 'completed_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'completed_at', 'updated_at']


class RefundRequestSerializer(serializers.ModelSerializer):
    """환불 요청 serializer"""
    
    user_info = serializers.SerializerMethodField()
    payment_info = serializers.SerializerMethodField()
    can_refund_info = serializers.SerializerMethodField()
    
    class Meta:
        model = RefundRequest
        fields = [
            'id', 'reason', 'status', 'request_amount', 'admin_note',
            'refund_method', 'refund_amount', 'created_at', 'updated_at',
            'processed_at', 'user_info', 'payment_info', 'can_refund_info'
        ]
        read_only_fields = [
            'id', 'status', 'admin_note', 'processed_at', 'refund_method', 
            'refund_amount', 'created_at', 'updated_at', 'user_info', 
            'payment_info', 'can_refund_info'
        ]
    
    def get_user_info(self, obj):
        """사용자 정보"""
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'email': obj.user.email,
            'nickname': getattr(obj.user, 'nickname', ''),
        }
    
    def get_payment_info(self, obj):
        """결제 정보"""
        return {
            'order_id': obj.payment.order_id,
            'tid': obj.payment.tid,
            'amount': obj.payment.amount,
            'pay_method': obj.payment.payment_method,
            'created_at': obj.payment.created_at.isoformat() if obj.payment.created_at else None,
            'product_name': obj.payment.product_name,
        }
    
    def get_can_refund_info(self, obj):
        """환불 가능 여부 정보"""
        can_refund, reason = obj.can_refund
        return {
            'can_refund': can_refund,
            'reason': reason
        }


class RefundRequestCreateSerializer(serializers.ModelSerializer):
    """환불 요청 생성 serializer"""
    
    payment_id = serializers.CharField(write_only=True)
    
    class Meta:
        model = RefundRequest
        fields = ['payment_id', 'reason']
    
    def validate_payment_id(self, value):
        """결제 ID 검증"""
        try:
            payment = Payment.objects.get(id=value, user=self.context['request'].user)
        except Payment.DoesNotExist:
            raise serializers.ValidationError("해당 결제 정보를 찾을 수 없습니다.")
        
        # 이미 환불 요청이 있는지 확인
        if RefundRequest.objects.filter(payment=payment).exists():
            raise serializers.ValidationError("이미 환불 요청이 접수된 결제입니다.")
        
        return value
    
    def create(self, validated_data):
        """환불 요청 생성"""
        payment_id = validated_data.pop('payment_id')
        payment = Payment.objects.get(id=payment_id, user=self.context['request'].user)
        
        # 환불 가능 여부 확인
        refund_request = RefundRequest(
            user=self.context['request'].user,
            payment=payment,
            request_amount=payment.amount,
            **validated_data
        )
        
        can_refund, reason = refund_request.can_refund
        if not can_refund:
            raise serializers.ValidationError(f"환불 불가: {reason}")
        
        refund_request.save()
        return refund_request


class RefundRequestAdminSerializer(serializers.ModelSerializer):
    """관리자용 환불 요청 serializer"""
    
    user_info = serializers.SerializerMethodField()
    payment_info = serializers.SerializerMethodField()
    
    class Meta:
        model = RefundRequest
        fields = [
            'id', 'reason', 'status', 'request_amount', 'admin_note',
            'refund_method', 'refund_amount', 'created_at', 'updated_at',
            'processed_at', 'user_info', 'payment_info'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_info', 'payment_info']
    
    def get_user_info(self, obj):
        """사용자 정보"""
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'email': obj.user.email,
            'nickname': getattr(obj.user, 'nickname', ''),
        }
    
    def get_payment_info(self, obj):
        """결제 정보"""
        return {
            'order_id': obj.payment.order_id,
            'tid': obj.payment.tid,
            'amount': obj.payment.amount,
            'pay_method': obj.payment.payment_method,
            'created_at': obj.payment.created_at.isoformat() if obj.payment.created_at else None,
            'completed_at': obj.payment.completed_at.isoformat() if obj.payment.completed_at else None,
            'product_name': obj.payment.product_name,
        }
    
    def update(self, instance, validated_data):
        """관리자 처리"""
        from django.utils import timezone
        
        # 상태 변경 시 처리일시와 처리자 설정
        if 'status' in validated_data and validated_data['status'] != instance.status:
            validated_data['processed_at'] = timezone.now()
            validated_data['processed_by'] = self.context['request'].user
        
        return super().update(instance, validated_data)