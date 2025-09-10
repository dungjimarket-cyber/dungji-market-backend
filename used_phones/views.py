"""
Used Phones API Views
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.shortcuts import get_object_or_404
from django.db.models import Q, F
from django_filters.rest_framework import DjangoFilterBackend
from .models import UsedPhone, UsedPhoneImage, UsedPhoneFavorite, UsedPhoneOffer
from .serializers import (
    UsedPhoneListSerializer, UsedPhoneDetailSerializer, 
    UsedPhoneCreateSerializer, UsedPhoneOfferSerializer,
    UsedPhoneFavoriteSerializer
)


class UsedPhoneViewSet(viewsets.ModelViewSet):
    """Used Phone ViewSet"""
    queryset = UsedPhone.objects.filter(status='active')
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['brand', 'condition_grade', 'accept_offers']
    search_fields = ['model', 'description']
    ordering_fields = ['price', 'created_at', 'view_count']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create' or self.action == 'update':
            return UsedPhoneCreateSerializer
        elif self.action == 'list':
            return UsedPhoneListSerializer
        return UsedPhoneDetailSerializer
    
    def perform_create(self, serializer):
        """Set seller automatically when creating"""
        serializer.save(seller=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        """Increment view count on detail view"""
        instance = self.get_object()
        instance.view_count = F('view_count') + 1
        instance.save(update_fields=['view_count'])
        
        # F() expression 사용 후 객체 다시 로드
        instance.refresh_from_db()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        """Toggle favorite"""
        phone = self.get_object()
        favorite, created = UsedPhoneFavorite.objects.get_or_create(
            user=request.user,
            phone=phone
        )
        
        if not created:
            favorite.delete()
            phone.favorite_count = F('favorite_count') - 1
            phone.save(update_fields=['favorite_count'])
            phone.refresh_from_db()  # F() expression 사용 후 객체 다시 로드
            return Response({'status': 'unfavorited', 'favorite_count': phone.favorite_count})
        
        phone.favorite_count = F('favorite_count') + 1
        phone.save(update_fields=['favorite_count'])
        phone.refresh_from_db()  # F() expression 사용 후 객체 다시 로드
        return Response({'status': 'favorited', 'favorite_count': phone.favorite_count})
