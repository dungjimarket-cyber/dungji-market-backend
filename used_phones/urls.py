"""
Used Phones URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UsedPhoneViewSet, UsedPhoneOfferViewSet

router = DefaultRouter()
router.register(r'phones', UsedPhoneViewSet, basename='usedphone')
router.register(r'offers', UsedPhoneOfferViewSet, basename='usedphoneoffer')

app_name = 'used_phones'

urlpatterns = [
    path('', include(router.urls)),
    # offer cancel을 위한 명시적 경로 (phones/{id}/offers/{offer_id}/cancel 형태로 사용하려면)
    path('phones/<int:phone_id>/offers/<int:pk>/cancel/', 
         UsedPhoneOfferViewSet.as_view({'post': 'cancel_offer'}), 
         name='offer-cancel'),
]
