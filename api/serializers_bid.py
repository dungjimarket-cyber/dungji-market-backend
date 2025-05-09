from rest_framework import serializers
from .models import Bid, Settlement
from django.contrib.auth import get_user_model

User = get_user_model()

class BidSerializer(serializers.ModelSerializer):
    """
    입찰 관리를 위한 시리얼라이저
    """
    seller_name = serializers.CharField(source='seller.username', read_only=True)
    groupbuy_title = serializers.CharField(source='groupbuy.title', read_only=True)
    product_name = serializers.CharField(source='groupbuy.product.name', read_only=True)
    deadline = serializers.CharField(source='groupbuy.end_time', read_only=True)
    participants_count = serializers.IntegerField(source='groupbuy.current_participants', read_only=True)
    
    class Meta:
        model = Bid
        fields = [
            'id', 'seller', 'seller_name', 'groupbuy', 'groupbuy_title', 
            'product_name', 'bid_type', 'amount', 'message', 'status', 
            'created_at', 'updated_at', 'deadline', 'participants_count'
        ]
        read_only_fields = ['status', 'created_at', 'updated_at']
        extra_kwargs = {
            'seller': {'required': False},
            'groupbuy': {'required': True},
            'amount': {'required': True, 'min_value': 1},
        }
    
    def validate(self, data):
        """
        입찰 데이터 유효성 검사
        """
        # 판매자가 아닌 경우 예외 발생
        user = self.context['request'].user
        if user.role != 'seller':
            raise serializers.ValidationError("판매회원만 입찰할 수 있습니다.")
        
        # 이미 종료된 공구에는 입찰할 수 없음
        groupbuy = data.get('groupbuy')
        if groupbuy and groupbuy.status not in ['recruiting', 'bidding']:
            raise serializers.ValidationError("모집 중이거나 입찰 중인 공구만 입찰할 수 있습니다.")
        
        return data


class SettlementSerializer(serializers.ModelSerializer):
    """
    정산 내역을 위한 시리얼라이저
    """
    groupbuy_title = serializers.CharField(source='groupbuy.title', read_only=True)
    product_name = serializers.CharField(source='groupbuy.product.name', read_only=True)
    participants_count = serializers.IntegerField(source='groupbuy.current_participants', read_only=True)
    
    class Meta:
        model = Settlement
        fields = [
            'id', 'seller', 'groupbuy', 'groupbuy_title', 'product_name',
            'total_amount', 'fee_amount', 'net_amount', 'participants_count',
            'settlement_date', 'payment_status', 'receipt_url'
        ]
        read_only_fields = ['seller', 'groupbuy', 'total_amount', 'fee_amount', 
                           'net_amount', 'settlement_date', 'payment_status']
