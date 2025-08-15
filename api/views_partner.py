from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q, Sum, Count
from django.http import HttpResponse
from datetime import datetime, timedelta
import csv
import io
import xlsxwriter

from .models_partner import (
    Partner, ReferralRecord, PartnerSettlement, 
    PartnerLink, PartnerNotification
)
from .serializers_partner import (
    PartnerSerializer, DashboardSummarySerializer, ReferralRecordSerializer,
    PartnerSettlementSerializer, PartnerSettlementRequestSerializer,
    PartnerLinkSerializer, PartnerNotificationSerializer,
    ExportDataSerializer, PartnerAccountSerializer, PartnerAccountUpdateSerializer
)
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class IsPartner(permissions.BasePermission):
    """파트너 권한 확인"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and
            hasattr(request.user, 'partner_profile')
        )


class StandardResultsSetPagination(PageNumberPagination):
    """표준 페이지네이션"""
    page_size = 20
    page_size_query_param = 'limit'
    max_page_size = 100


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def partner_login(request):
    """파트너 로그인"""
    partner_id = request.data.get('partner_id')
    password = request.data.get('password')
    
    if not partner_id or not password:
        return Response({
            'error': '파트너 ID와 비밀번호를 입력해주세요.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # 파트너 코드로 파트너 찾기
        partner = Partner.objects.get(partner_code=partner_id)
        user = partner.user
        
        # 사용자 인증
        if not user.check_password(password):
            return Response({
                'error': '잘못된 로그인 정보입니다.'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if not partner.is_active:
            return Response({
                'error': '비활성화된 파트너 계정입니다.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # JWT 토큰 생성
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        
        # 파트너 정보 반환
        partner_serializer = PartnerSerializer(partner)
        
        return Response({
            'access_token': access_token,
            'refresh_token': str(refresh),
            'partner_info': partner_serializer.data
        })
        
    except Partner.DoesNotExist:
        return Response({
            'error': '잘못된 로그인 정보입니다.'
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@permission_classes([IsPartner])
def dashboard_summary(request):
    """대시보드 요약 정보"""
    partner = request.user.partner_profile
    now = timezone.now()
    
    # 이번달 신규 가입자 수
    monthly_signup = partner.referral_records.filter(
        created_at__year=now.year,
        created_at__month=now.month
    ).count()
    
    # 활성 구독자 수
    active_subscribers = partner.get_active_subscribers()
    
    # 이번달 수익
    monthly_revenue = partner.get_monthly_revenue(now.year, now.month)
    
    # 정산 가능 금액
    available_settlement = partner.get_available_settlement_amount()
    
    data = {
        'monthly_signup': monthly_signup,
        'active_subscribers': active_subscribers,
        'monthly_revenue': monthly_revenue,
        'available_settlement': available_settlement
    }
    
    serializer = DashboardSummarySerializer(data)
    return Response(serializer.data)


class ReferralRecordListView(generics.ListAPIView):
    """추천 회원 목록"""
    serializer_class = ReferralRecordSerializer
    permission_classes = [IsPartner]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        partner = self.request.user.partner_profile
        queryset = partner.referral_records.all()
        
        # 필터링
        status_filter = self.request.query_params.get('status')
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(subscription_status=status_filter)
        
        # 검색
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(referred_user__username__icontains=search) |
                Q(referred_user__nickname__icontains=search) |
                Q(referred_user__phone_number__icontains=search)
            )
        
        # 날짜 필터
        date_range = self.request.query_params.get('date_range')
        if date_range:
            now = timezone.now()
            if date_range == 'today':
                start_date = now.date()
                queryset = queryset.filter(created_at__date=start_date)
            elif date_range == 'week':
                start_date = now - timedelta(days=7)
                queryset = queryset.filter(created_at__gte=start_date)
            elif date_range == 'month':
                start_date = now - timedelta(days=30)
                queryset = queryset.filter(created_at__gte=start_date)
        
        return queryset.order_by('-created_at')


@api_view(['GET'])
@permission_classes([IsPartner])
def referral_link(request):
    """추천 링크 정보"""
    partner = request.user.partner_profile
    
    return Response({
        'partner_code': partner.partner_code,
        'full_url': partner.get_referral_link(),
        'short_url': f"https://dng.kr/{partner.partner_code.lower()}",
        'qr_code_url': f"/api/partners/qr-code/{partner.partner_code}/"
    })


@api_view(['GET'])
@permission_classes([IsPartner])
def account_info(request):
    """계좌 정보 조회"""
    partner = request.user.partner_profile
    serializer = PartnerAccountSerializer(partner)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsPartner])
def update_account(request):
    """계좌 정보 수정"""
    partner = request.user.partner_profile
    serializer = PartnerAccountUpdateSerializer(partner, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return Response({'message': '계좌 정보가 수정되었습니다.'})
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PartnerSettlementListView(generics.ListAPIView):
    """정산 내역 목록"""
    serializer_class = PartnerSettlementSerializer
    permission_classes = [IsPartner]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        partner = self.request.user.partner_profile
        return partner.settlements.all().order_by('-requested_at')


@api_view(['POST'])
@permission_classes([IsPartner])
def request_settlement(request):
    """정산 요청"""
    partner = request.user.partner_profile
    
    # 계좌 정보 확인
    if not all([partner.bank_name, partner.account_number, partner.account_holder]):
        return Response({
            'error': '정산을 위해서는 계좌 정보 등록이 필요합니다.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 진행중인 정산 요청 확인
    pending_settlement = partner.settlements.filter(
        status__in=['pending', 'processing']
    ).first()
    
    if pending_settlement:
        return Response({
            'error': '이미 처리중인 정산 요청이 있습니다.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = PartnerSettlementRequestSerializer(
        data=request.data,
        context={'partner': partner}
    )
    
    if serializer.is_valid():
        settlement = serializer.save()
        response_serializer = PartnerSettlementSerializer(settlement)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsPartner])
def export_data(request):
    """데이터 내보내기"""
    partner = request.user.partner_profile
    
    serializer = ExportDataSerializer(data=request.query_params)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    export_format = data.get('format', 'excel')
    
    # 데이터 조회
    queryset = partner.referral_records.all()
    
    # 날짜 필터링
    if data.get('start_date'):
        queryset = queryset.filter(created_at__date__gte=data['start_date'])
    if data.get('end_date'):
        queryset = queryset.filter(created_at__date__lte=data['end_date'])
    
    # 상태 필터링
    status_filter = data.get('status_filter')
    if status_filter and status_filter != 'all':
        queryset = queryset.filter(subscription_status=status_filter)
    
    # 개인정보 마스킹된 데이터 생성
    records = []
    for record in queryset.order_by('-created_at'):
        # 이름 마스킹
        name = record.referred_user.nickname or record.referred_user.username
        if len(name) > 1:
            masked_name = name[0] + "○" * (len(name) - 2) + (name[-1] if len(name) > 2 else "")
        else:
            masked_name = name
        
        # 전화번호 마스킹
        phone = record.referred_user.phone_number or ""
        if len(phone) >= 11:
            masked_phone = phone[:3] + "-****-" + phone[-4:]
        else:
            masked_phone = phone
        
        records.append({
            '가입일자': record.created_at.strftime('%Y.%m.%d'),
            '회원정보': masked_name,
            '전화번호': masked_phone,
            '구독권': '✓' if record.subscription_status == 'active' else '✗',
            '구독금액': f"{record.subscription_amount:,}원" if record.subscription_amount else '-',
            '견적티켓': f"{record.ticket_count}개" if record.ticket_count else '-',
            '티켓금액': f"{record.ticket_amount:,}원" if record.ticket_amount else '-',
            '총 결제': f"{record.total_amount:,}원",
            '예정수수료': f"{record.commission_amount:,}원",
            '상태': {'active': '활성', 'cancelled': '해지', 'paused': '휴면'}.get(
                record.subscription_status, record.subscription_status
            )
        })
    
    # 파일 생성
    if export_format == 'csv':
        return _generate_csv_response(records, partner.partner_name)
    else:
        return _generate_excel_response(records, partner.partner_name)


def _generate_csv_response(records, partner_name):
    """CSV 파일 생성"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{partner_name}_referral_data.csv"'
    
    # UTF-8 BOM 추가 (Excel에서 한글이 깨지지 않도록)
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    if records:
        # 헤더 작성
        writer.writerow(records[0].keys())
        
        # 데이터 작성
        for record in records:
            writer.writerow(record.values())
    
    return response


def _generate_excel_response(records, partner_name):
    """Excel 파일 생성"""
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('추천회원데이터')
    
    # 스타일 정의
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#D7E4BD',
        'border': 1
    })
    
    cell_format = workbook.add_format({
        'border': 1
    })
    
    if records:
        # 헤더 작성
        headers = list(records[0].keys())
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # 데이터 작성
        for row, record in enumerate(records, 1):
            for col, value in enumerate(record.values()):
                worksheet.write(row, col, value, cell_format)
        
        # 열 너비 자동 조정
        for col, header in enumerate(headers):
            max_length = max(len(str(header)), 15)
            worksheet.set_column(col, col, max_length)
    
    workbook.close()
    
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{partner_name}_referral_data.xlsx"'
    
    return response


class PartnerNotificationListView(generics.ListAPIView):
    """파트너 알림 목록"""
    serializer_class = PartnerNotificationSerializer
    permission_classes = [IsPartner]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        partner = self.request.user.partner_profile
        return partner.notifications.all().order_by('-created_at')


@api_view(['POST'])
@permission_classes([IsPartner])
def mark_notification_read(request, notification_id):
    """알림 읽음 처리"""
    partner = request.user.partner_profile
    
    try:
        notification = partner.notifications.get(id=notification_id)
        notification.mark_as_read()
        return Response({'message': '알림을 읽음 처리했습니다.'})
    except PartnerNotification.DoesNotExist:
        return Response({
            'error': '알림을 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsPartner])
def mark_all_notifications_read(request):
    """모든 알림 읽음 처리"""
    partner = request.user.partner_profile
    
    partner.notifications.filter(is_read=False).update(
        is_read=True,
        read_at=timezone.now()
    )
    
    return Response({'message': '모든 알림을 읽음 처리했습니다.'})


@api_view(['GET'])
@permission_classes([IsPartner])
def statistics(request):
    """통계 데이터"""
    partner = request.user.partner_profile
    period = request.query_params.get('period', 'month')
    
    now = timezone.now()
    stats = []
    
    if period == 'month':
        # 최근 12개월 데이터
        for i in range(11, -1, -1):
            month_start = (now - timedelta(days=30*i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if i == 0:
                month_end = now
            else:
                month_end = (now - timedelta(days=30*(i-1))).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            records = partner.referral_records.filter(
                created_at__gte=month_start,
                created_at__lt=month_end
            )
            
            stats.append({
                'period': month_start.strftime('%Y-%m'),
                'signup_count': records.count(),
                'revenue': records.aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0,
                'subscription_count': records.filter(subscription_status='active').count()
            })
    
    return Response(stats)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def generate_qr_code(request, partner_code):
    """QR 코드 생성"""
    try:
        import qrcode
        from django.http import HttpResponse
        import io
        
        # QR 코드 생성
        partner = Partner.objects.get(partner_code=partner_code)
        referral_url = partner.get_referral_link()
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(referral_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 이미지를 HTTP 응답으로 반환
        response = HttpResponse(content_type="image/png")
        img.save(response, "PNG")
        return response
        
    except Partner.DoesNotExist:
        return Response({
            'error': '파트너를 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)
    except ImportError:
        return Response({
            'error': 'QR 코드 생성 라이브러리가 설치되지 않았습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)