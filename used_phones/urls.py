"""
Used Phones URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UsedPhoneViewSet, UsedPhoneOfferViewSet, UsedPhoneFavoriteViewSet,
    UsedPhoneTransactionViewSet, UsedPhoneReviewViewSet
)

router = DefaultRouter()
router.register(r'phones', UsedPhoneViewSet, basename='usedphone')
router.register(r'offers', UsedPhoneOfferViewSet, basename='usedphoneoffer')
router.register(r'favorites', UsedPhoneFavoriteViewSet, basename='usedphonefavorite')
router.register(r'transactions', UsedPhoneTransactionViewSet, basename='usedphonetransaction')
router.register(r'reviews', UsedPhoneReviewViewSet, basename='usedphonereview')

app_name = 'used_phones'

urlpatterns = [
    path('', include(router.urls)),
]
