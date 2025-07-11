from rest_framework import serializers
from .models_region import Region

class RegionSerializer(serializers.ModelSerializer):
    """
    지역 정보 시리얼라이저
    """
    class Meta:
        model = Region
        fields = ['code', 'name', 'full_name', 'level', 'is_active']


class RegionDetailSerializer(serializers.ModelSerializer):
    """
    지역 상세 정보 시리얼라이저 (하위 지역 포함)
    """
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = Region
        fields = ['code', 'name', 'full_name', 'level', 'is_active', 'children']
    
    def get_children(self, obj):
        """하위 지역 목록 반환"""
        children = obj.get_children()
        return RegionSerializer(children, many=True).data


class RegionTreeSerializer(serializers.ModelSerializer):
    """
    지역 트리 구조 시리얼라이저 (계층 구조 표현)
    """
    ancestors = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = Region
        fields = ['code', 'name', 'full_name', 'level', 'is_active', 'ancestors', 'children']
    
    def get_ancestors(self, obj):
        """상위 지역 목록 반환 (자신 제외)"""
        ancestors = obj.get_ancestors()
        if ancestors and ancestors[-1].code == obj.code:
            ancestors = ancestors[:-1]  # 자신 제외
        return RegionSerializer(ancestors, many=True).data
    
    def get_children(self, obj):
        """하위 지역 목록 반환"""
        children = obj.get_children()
        return RegionSerializer(children, many=True).data
