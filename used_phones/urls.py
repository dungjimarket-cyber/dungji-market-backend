"""
Used Phones URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UsedPhoneViewSet, UsedPhoneOfferViewSet, UsedPhoneFavoriteViewSet,
    UsedPhoneTransactionViewSet, UsedPhoneReviewViewSet, UsedPhoneReportViewSet,
    UsedPhonePenaltyViewSet, UserRatingView, create_simple_review
)

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
    path('', include(router.urls)),  # router.urls는 마지막에
]
