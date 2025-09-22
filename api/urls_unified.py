"""
통합 찜/후기 URL 설정
"""
from django.urls import path
from .views_unified import (
    # 찜 관련
    toggle_favorite,
    favorite_status,
    my_favorites,

    # 후기 관련
    create_review,
    user_reviews,
    check_review_written,
)

urlpatterns = [
    # 찜 관련 API
    path('favorites/toggle/', toggle_favorite, name='unified_toggle_favorite'),
    path('favorites/status/<str:item_type>/<int:item_id>/', favorite_status, name='unified_favorite_status'),
    path('favorites/my/', my_favorites, name='unified_my_favorites'),

    # 후기 관련 API
    path('reviews/create/', create_review, name='unified_create_review'),
    path('reviews/user/<str:username>/', user_reviews, name='unified_user_reviews'),
    path('reviews/check/<str:item_type>/<int:transaction_id>/', check_review_written, name='unified_check_review'),
]