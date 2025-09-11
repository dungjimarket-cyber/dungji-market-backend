"""
Used Phones URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UsedPhoneViewSet, UsedPhoneOfferViewSet, UsedPhoneFavoriteViewSet

router = DefaultRouter()
router.register(r'phones', UsedPhoneViewSet, basename='usedphone')
router.register(r'offers', UsedPhoneOfferViewSet, basename='usedphoneoffer')
router.register(r'favorites', UsedPhoneFavoriteViewSet, basename='usedphonefavorite')

app_name = 'used_phones'

urlpatterns = [
    path('', include(router.urls)),
]
