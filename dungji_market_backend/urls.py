"""
URL configuration for dungji_market_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from api.views import (
    CategoryViewSet, ProductViewSet, GroupBuyViewSet,
    ParticipationViewSet, WishlistViewSet, ReviewViewSet,
    register_user, create_sns_user, UserProfileView, get_category_fields,
    SellerViewSet
)
from api.views_bid import BidViewSet, SettlementViewSet, group_buy_bids
from api.views_seller import (
    SellerProfileView, get_bid_summary, SellerSalesView, get_seller_sale_detail,
    purchase_bid_tokens, get_bid_tokens
)
from api.views_region import RegionViewSet
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)
from api.views_auth import CustomTokenObtainPairView
from api.views_social import social_login_dispatch, kakao_callback

router = DefaultRouter()
router.register('categories', CategoryViewSet)
router.register('products', ProductViewSet)
router.register('groupbuys', GroupBuyViewSet)
router.register('participations', ParticipationViewSet)
router.register(r'wishlists', WishlistViewSet, basename='wishlist')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'bids', BidViewSet, basename='bid')
router.register(r'settlements', SettlementViewSet, basename='settlement')
router.register(r'seller', SellerViewSet, basename='seller')
router.register(r'regions', RegionViewSet, basename='region')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include([
        path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
        path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
        path('register/', register_user, name='register'),
        path('sns-login/', create_sns_user, name='sns_login'),
        path('profile/', UserProfileView.as_view(), name='profile'),
        path('social/<str:provider>/', social_login_dispatch, name='social_login'),
        path('callback/kakao/', kakao_callback, name='kakao_callback'),
        path('find-username/', __import__('api.views_auth').views_auth.FindUsernameView.as_view(), name='find_username'),
        path('reset-password/', __import__('api.views_auth').views_auth.ResetPasswordView.as_view(), name='reset_password'),
    ])),

    path('api/', include(router.urls)),
    path('api/categories/<int:category_id>/fields/', get_category_fields, name='category_fields'),
    path('api/groupbuys/<int:groupbuy_id>/bids/', group_buy_bids, name='groupbuy_bids'),
    # 판매자 마이페이지 API
    path('api/users/me/seller-profile/', SellerProfileView.as_view(), name='seller_profile'),
    path('api/users/me/bids/summary/', get_bid_summary, name='bid_summary'),
    path('api/users/me/sales/', SellerSalesView.as_view(), name='seller_sales'),
    path('api/users/me/sales/<int:bid_id>/', get_seller_sale_detail, name='seller_sale_detail'),
    # 입찰권 관련 API
    path('api/bid-tokens/purchase/', purchase_bid_tokens, name='purchase_bid_tokens'),
    path('api/bid-tokens/', get_bid_tokens, name='get_bid_tokens'),
]

# 개발 환경에서는 Django가 정적 파일 제공
# 운영 환경에서는 웹 서버가 정적 파일 제공을 담당하는 것이 좋지만, 운영 환경에서도 작동하도록 설정
if settings.DEBUG or True:  # 운영 환경에서도 Django가 정적 파일 제공
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)