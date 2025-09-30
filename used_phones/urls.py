"""
Used Phones URL Configuration
"""
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from rest_framework.routers import DefaultRouter
from .views import (
    UsedPhoneViewSet, UsedPhoneOfferViewSet, UsedPhoneFavoriteViewSet,
    UsedPhoneTransactionViewSet, UsedPhoneReviewViewSet, UsedPhoneReportViewSet,
    UsedPhonePenaltyViewSet, UserRatingView, create_simple_review
)
from api.views_bump import get_bump_status, perform_bump, get_today_bump_count

router = DefaultRouter()
router.register(r'phones', UsedPhoneViewSet, basename='usedphone')
router.register(r'offers', UsedPhoneOfferViewSet, basename='usedphoneoffer')
router.register(r'favorites', UsedPhoneFavoriteViewSet, basename='usedphonefavorite')
router.register(r'transactions', UsedPhoneTransactionViewSet, basename='usedphonetransaction')
router.register(r'reviews', UsedPhoneReviewViewSet, basename='usedphonereview')
router.register(r'reports', UsedPhoneReportViewSet, basename='usedphonereport')
router.register(r'penalties', UsedPhonePenaltyViewSet, basename='usedphonepenalty')

app_name = 'used_phones'

urlpatterns = [
    path('reviews/simple/', create_simple_review, name='simple-review'),  # 새로운 간단한 리뷰 API - router보다 먼저!
    path('users/<int:user_id>/rating/', UserRatingView.as_view(), name='user-rating'),

    # 끌올 관련 URLs
    path('phones/<int:item_id>/bump/status/', lambda request, item_id: get_bump_status(request, 'phone', item_id), name='phone-bump-status'),
    path('phones/<int:item_id>/bump/', csrf_exempt(lambda request, item_id: perform_bump(request, 'phone', item_id)), name='phone-bump'),
    path('bump/today-count/', get_today_bump_count, name='bump-today-count'),

    path('', include(router.urls)),  # router.urls는 마지막에
]
