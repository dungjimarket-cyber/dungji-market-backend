"""
àð Áp˜ URL $
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UsedPhoneViewSet

router = DefaultRouter()
router.register(r'phones', UsedPhoneViewSet, basename='usedphone')

app_name = 'used_phones'

urlpatterns = [
    path('', include(router.urls)),
]