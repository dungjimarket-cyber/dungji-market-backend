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
    purchase_bid_tokens, get_bid_tokens, get_remote_sales_status
)
from api.views_inicis import (
    prepare_inicis_payment, verify_inicis_payment, cancel_inicis_payment,
    inicis_webhook, inicis_return, inicis_close, generate_mobile_hash
)
from api.views_region import RegionViewSet
from api.views_notification import NotificationViewSet
from api.admin_views import (
    AdminViewSet, adjust_user_bid_tokens, get_seller_detail, add_bid_permission_endpoint,
    get_seller_detail_with_full_info, adjust_bid_tokens, grant_subscription, search_users
)
from api.views_consent import ParticipantConsentViewSet, start_consent_process
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)
from api.views_auth import CustomTokenObtainPairView, register_user_v2, check_username, check_nickname, check_email, find_username, reset_password, withdraw_user, get_user_profile, update_user_profile, user_profile, send_password_reset_email, verify_password_reset_email, reset_password_with_email, update_referral_code, check_referral_status
from api.views_auth_token import refresh_user_token, verify_token_role
from api.views_social import social_login_dispatch, kakao_callback, check_kakao_user_exists
from api.views_verification import send_verification_code, verify_code, check_verification_status, verify_business_number, get_business_verification_history, check_business_number_format, verify_business_number_registration
from api.views_phone_verification import send_phone_verification, verify_phone, check_phone_verification_status, update_phone_number
# voting 관련 import는 voting 상태 제거로 인해 삭제됨
from api.views_final_selection import (
    buyer_final_decision, seller_final_decision, 
    get_final_decision_status, get_contact_info,
    get_buyer_confirmation_stats
)
from api.views_noshow import NoShowReportViewSet, check_noshow_report_eligibility, batch_report_buyer_noshow
from api.views_banner import BannerListView, EventListView, EventDetailView, get_main_banners
from api.views_health import health_check
from api.views_cron import update_groupbuy_status_cron, send_reminder_notifications_cron, cron_health_check
from api.views_partner import (
    partner_login, dashboard_summary, ReferralRecordListView, referral_link,
    account_info, update_account, PartnerSettlementListView, request_settlement,
    export_data, PartnerNotificationListView, mark_notification_read,
    mark_all_notifications_read, statistics, generate_qr_code
)
from api.views_partner_bank import (
    register_bank_account, get_bank_account, delete_bank_account, verify_bank_account
)
from api.views_inquiry import InquiryViewSet
from api.views_notice import NoticeViewSet
from api.views_auth_email import (
    request_password_reset, verify_reset_token, reset_password as reset_password_with_token,
    send_verification_email, verify_email_code, change_email
)

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
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'admin', AdminViewSet, basename='admin')
router.register(r'consents', ParticipantConsentViewSet, basename='consent')
router.register(r'noshow-reports', NoShowReportViewSet, basename='noshow-report')
router.register(r'inquiries', InquiryViewSet, basename='inquiry')
router.register(r'notices', NoticeViewSet, basename='notice')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include([
        path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
        path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
        path('register/', register_user_v2, name='register'),  # 새로운 회원가입 API 사용
        path('register-old/', register_user, name='register_old'),  # 기존 API 보존
        path('check-username/', check_username, name='check_username'),
        path('check-nickname/', check_nickname, name='check_nickname'),
        path('check-email/', check_email, name='check_email'),
        path('find-username/', find_username, name='find_username'),
        path('find-username-by-phone/', find_username, name='find_username_by_phone'),
        path('reset-password/', reset_password, name='reset_password'),
        path('reset-password-by-phone/', reset_password, name='reset_password_by_phone'),
        # 이메일 기반 비밀번호 재설정 API
        path('password-reset/send-email/', send_password_reset_email, name='send_password_reset_email'),
        path('password-reset/verify-email/', verify_password_reset_email, name='verify_password_reset_email'),
        path('password-reset/reset/', reset_password_with_email, name='reset_password_with_email'),
        path('withdraw/', withdraw_user, name='withdraw_user'),
        path('sns-login/', create_sns_user, name='sns_login'),
        path('profile/', user_profile, name='profile'),
        path('update-referral-code/', update_referral_code, name='update_referral_code'),
        path('check-referral-status/', check_referral_status, name='check_referral_status'),
        path('social/<str:provider>/', social_login_dispatch, name='social_login'),
        path('callback/kakao/', kakao_callback, name='kakao_callback'),
        path('check-kakao-user/', check_kakao_user_exists, name='check_kakao_user_exists'),
        # 휴대폰 인증 API
        path('phone/send-code/', send_verification_code, name='send_verification_code'),
        path('phone/verify/', verify_code, name='verify_code'),
        path('phone/status/', check_verification_status, name='check_verification_status'),
        # 사업자번호 검증 API
        path('business/verify/', verify_business_number, name='verify_business_number'),
        path('business/verify-registration/', verify_business_number_registration, name='verify_business_number_registration'),
        path('business/history/', get_business_verification_history, name='business_verification_history'),
        path('business/check-format/', check_business_number_format, name='check_business_number_format'),
        # 토큰 갱신 및 검증 API
        path('token/refresh-force/', refresh_user_token, name='refresh_user_token'),
        path('token/verify-role/', verify_token_role, name='verify_token_role'),
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
    # 이니시스 결제 API
    path('api/payments/inicis/prepare/', prepare_inicis_payment, name='prepare_inicis_payment'),
    path('api/payments/inicis/verify/', verify_inicis_payment, name='verify_inicis_payment'),
    path('api/payments/inicis/cancel/', cancel_inicis_payment, name='cancel_inicis_payment'),
    path('api/payments/inicis/webhook/', inicis_webhook, name='inicis_webhook'),
    path('api/payments/inicis/return/', inicis_return, name='inicis_return'),
    path('api/payments/inicis/close/', inicis_close, name='inicis_close'),
    path('api/payments/inicis/mobile-hash/', generate_mobile_hash, name='generate_mobile_hash'),
    # 비대면 판매인증 상태 조회 API
    path('api/users/me/remote-sales-status/', get_remote_sales_status, name='get_remote_sales_status'),
    
    # 휴대폰 인증 API
    path('api/phone/send-verification/', send_phone_verification, name='send_phone_verification'),
    path('api/phone/verify/', verify_phone, name='verify_phone'),
    path('api/phone/status/', check_phone_verification_status, name='check_phone_verification_status'),
    path('api/phone/update/', update_phone_number, name='update_phone_number'),
    # 사용자 참여 정보 API
    path('api/users/me/participations/', ParticipationViewSet.as_view({'get': 'me'}), name='user_participations'),
    # 동의 프로세스 시작 API
    path('api/groupbuys/<int:pk>/start-consent/', start_consent_process, name='start_consent_process'),
    # 투표 관련 API는 voting 상태 제거로 인해 삭제됨
    # 최종선택 관련 API
    path('api/groupbuys/<int:groupbuy_id>/buyer-decision/', buyer_final_decision, name='buyer_final_decision'),
    path('api/groupbuys/<int:groupbuy_id>/seller-decision/', seller_final_decision, name='seller_final_decision'),
    path('api/groupbuys/<int:groupbuy_id>/decision-status/', get_final_decision_status, name='get_final_decision_status'),
    path('api/groupbuys/<int:groupbuy_id>/contact-info/', get_contact_info, name='get_contact_info'),
    path('api/groupbuys/<int:groupbuy_id>/buyer-confirmation-stats/', get_buyer_confirmation_stats, name='get_buyer_confirmation_stats'),
    # 노쇼 신고 관련 API
    path('api/noshow-reports/check-eligibility/', check_noshow_report_eligibility, name='check_noshow_report_eligibility'),
    path('api/noshow-reports/batch-report/', batch_report_buyer_noshow, name='batch_report_buyer_noshow'),
    # 배너 및 이벤트 API
    path('api/banners/', BannerListView.as_view(), name='banner_list'),
    path('api/banners/main/', get_main_banners, name='main_banners'),
    path('api/events/', EventListView.as_view(), name='event_list'),
    path('api/events/<slug:slug>/', EventDetailView.as_view(), name='event_detail'),
    # Health check API
    path('api/health/', health_check, name='health_check'),
    # Cron job APIs
    path('api/cron/update-status/', update_groupbuy_status_cron, name='cron_update_status'),
    path('api/cron/send-reminders/', send_reminder_notifications_cron, name='cron_send_reminders'),
    path('api/cron/health/', cron_health_check, name='cron_health_check'),
    
    # Partner APIs
    path('api/partners/auth/login/', partner_login, name='partner_login'),
    path('api/partners/dashboard/summary/', dashboard_summary, name='partner_dashboard_summary'),
    path('api/partners/members/', ReferralRecordListView.as_view(), name='partner_members'),
    path('api/partners/referral-link/', referral_link, name='partner_referral_link'),
    path('api/partners/account/', account_info, name='partner_account_info'),
    path('api/partners/account/update/', update_account, name='partner_update_account'),
    path('api/partners/settlements/', PartnerSettlementListView.as_view(), name='partner_settlements'),
    path('api/partners/settlements/request/', request_settlement, name='partner_request_settlement'),
    path('api/partners/export/', export_data, name='partner_export_data'),
    path('api/partners/notifications/', PartnerNotificationListView.as_view(), name='partner_notifications'),
    path('api/partners/notifications/<int:notification_id>/read/', mark_notification_read, name='partner_mark_notification_read'),
    path('api/partners/notifications/read-all/', mark_all_notifications_read, name='partner_mark_all_notifications_read'),
    path('api/partners/statistics/', statistics, name='partner_statistics'),
    path('api/partners/qr-code/<str:partner_code>/', generate_qr_code, name='partner_qr_code'),
    
    # 파트너 은행계좌 관리
    path('api/partners/bank-account/', get_bank_account, name='partner_get_bank_account'),
    path('api/partners/bank-account/verify/', verify_bank_account, name='partner_verify_bank_account'),
    path('api/partners/bank-account/register/', register_bank_account, name='partner_register_bank_account'),
    path('api/partners/bank-account/delete/', delete_bank_account, name='partner_delete_bank_account'),
    
    # Admin APIs for bid token management (API 경로로 변경)
    path('api/admin/user/<int:user_id>/adjust-tokens/', adjust_user_bid_tokens, name='admin_adjust_user_bid_tokens'),
    
    # Admin API endpoints that frontend expects
    path('api/admin/sellers/<int:seller_id>/', get_seller_detail_with_full_info, name='admin_get_seller_detail'),
    path('api/admin/add_bid_permission/<int:user_id>/', add_bid_permission_endpoint, name='admin_add_bid_permission'),
    path('api/admin/bid-tokens/adjust/', adjust_bid_tokens, name='admin_adjust_bid_tokens'),
    path('api/admin/bid-tokens/grant-subscription/', grant_subscription, name='admin_grant_subscription'),
    path('api/admin/users/search/', search_users, name='admin_search_users'),
    
    # 이메일 인증 관련 API
    path('api/auth/email/request-reset/', request_password_reset, name='request_password_reset'),
    path('api/auth/email/verify-token/', verify_reset_token, name='verify_reset_token'),
    path('api/auth/email/reset-password/', reset_password_with_token, name='reset_password_with_token'),
    path('api/auth/email/send-verification/', send_verification_email, name='send_verification_email'),
    path('api/auth/email/verify-code/', verify_email_code, name='verify_email_code'),
    path('api/auth/email/change/', change_email, name='change_email'),
]

# 개발 환경에서는 Django가 정적 파일 제공
# 운영 환경에서는 웹 서버가 정적 파일 제공을 담당하는 것이 좋지만, 운영 환경에서도 작동하도록 설정
if settings.DEBUG or True:  # 운영 환경에서도 Django가 정적 파일 제공
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)