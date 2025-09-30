"""
전자제품/가전 URL 설정
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UsedElectronicsViewSet, create_simple_review
from api.views_bump import get_bump_status, perform_bump

app_name = 'used_electronics'

router = DefaultRouter()
router.register('', UsedElectronicsViewSet, basename='electronics')

urlpatterns = [
    path('reviews/simple/', create_simple_review, name='simple-review'),  # router보다 먼저!

    # 끌올 관련 URLs
    path('<int:item_id>/bump/status/', lambda request, item_id: get_bump_status(request, 'electronics', item_id), name='electronics-bump-status'),
    path('<int:item_id>/bump/', lambda request, item_id: perform_bump(request, 'electronics', item_id), name='electronics-bump'),

    path('', include(router.urls)),
]