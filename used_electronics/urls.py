"""
전자제품/가전 URL 설정
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UsedElectronicsViewSet, create_simple_review

app_name = 'used_electronics'

router = DefaultRouter()
router.register('', UsedElectronicsViewSet, basename='electronics')

urlpatterns = [
    path('reviews/simple/', create_simple_review, name='simple-review'),  # router보다 먼저!
    path('', include(router.urls)),
]