"""
크롤러 관리 Admin
- 크롤링 실행 (백그라운드)
- 결과 엑셀 다운로드
- 이메일 캠페인 발송
"""

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.contrib import messages
from django.core.files.base import ContentFile
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.utils.decorators import method_decorator

from .models_crawler import CrawlSession, CrawlResult, EmailCampaign
from .services.crawler_service import (
    run_crawler, run_all_crawlers, export_to_excel,
    get_emails_from_data, CRAWLER_MAP,
    crawl_local_business_emails, get_local_business_categories, get_local_business_regions
)

import json
import logging
import threading
from datetime import datetime
from io import BytesIO

logger = logging.getLogger(__name__)

# 진행 중인 크롤링 작업 추적
_crawling_progress = {}


# ============== Admin ModelAdmin ==============

@admin.register(CrawlSession)
class CrawlSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'crawler_type', 'status', 'total_count', 'email_count', 'created_by', 'created_at', 'completed_at']
    list_filter = ['status', 'crawler_type', 'created_at']
    search_fields = ['id']
    readonly_fields = ['created_at', 'completed_at', 'total_count', 'email_count']
    ordering = ['-created_at']

    actions = ['download_excel']

    def download_excel(self, request, queryset):
        """선택한 세션의 결과를 엑셀로 다운로드"""
        all_data = []
        for session in queryset:
            for result in session.results.all():
                all_data.append({
                    '업종': result.get_category_display(),
                    '성명': result.name,
                    '사무소명': result.office_name,
                    '소속': result.affiliation,
                    '주소': result.address,
                    '지역': result.region,
                    '전화번호': result.phone,
                    '이메일': result.email,
                    '전문분야': result.specialty,
                })

        if not all_data:
            self.message_user(request, "다운로드할 데이터가 없습니다.", messages.WARNING)
            return

        excel_file = export_to_excel(all_data)
        if excel_file:
            response = HttpResponse(
                excel_file.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="crawl_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
            return response

    download_excel.short_description = "선택한 세션 엑셀 다운로드"


@admin.register(CrawlResult)
class CrawlResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'category', 'name', 'office_name', 'region', 'phone', 'email', 'email_sent', 'created_at']
    list_filter = ['category', 'region', 'email_sent', 'created_at']
    search_fields = ['name', 'office_name', 'email', 'phone']
    readonly_fields = ['created_at']
    ordering = ['-created_at']

    actions = ['export_selected', 'mark_email_sent']

    def export_selected(self, request, queryset):
        """선택한 결과를 엑셀로 다운로드"""
        data = []
        for result in queryset:
            data.append({
                '업종': result.get_category_display(),
                '성명': result.name,
                '사무소명': result.office_name,
                '소속': result.affiliation,
                '주소': result.address,
                '지역': result.region,
                '전화번호': result.phone,
                '이메일': result.email,
                '전문분야': result.specialty,
            })

        excel_file = export_to_excel(data)
        if excel_file:
            response = HttpResponse(
                excel_file.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="selected_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
            return response

    export_selected.short_description = "선택한 결과 엑셀 다운로드"

    def mark_email_sent(self, request, queryset):
        """선택한 결과를 이메일 발송 완료로 표시"""
        count = queryset.update(email_sent=True, email_sent_at=timezone.now())
        self.message_user(request, f"{count}건이 이메일 발송 완료로 표시되었습니다.")

    mark_email_sent.short_description = "이메일 발송 완료로 표시"


@admin.register(EmailCampaign)
class EmailCampaignAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'subject', 'status', 'total_count', 'success_count', 'fail_count', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'subject']
    readonly_fields = ['total_count', 'success_count', 'fail_count', 'started_at', 'completed_at', 'created_at']
    ordering = ['-created_at']


# ============== 백그라운드 크롤링 함수 ==============

def run_crawling_task(session_id, crawler_type, params):
    """백그라운드에서 크롤링 실행"""
    import django
    django.setup()

    from django.db import connection
    connection.close()

    from .models_crawler import CrawlSession, CrawlResult
    from .services.crawler_service import (
        crawl_local_business_emails, run_crawler, run_all_crawlers, export_to_excel
    )

    global _crawling_progress

    try:
        session = CrawlSession.objects.get(pk=session_id)

        def progress_callback(msg):
            _crawling_progress[session_id] = {
                'status': 'running',
                'message': msg,
                'updated_at': datetime.now().isoformat()
            }

        _crawling_progress[session_id] = {
            'status': 'running',
            'message': '크롤링 시작...',
            'updated_at': datetime.now().isoformat()
        }

        if crawler_type == 'local_business':
            result = crawl_local_business_emails(
                category_id=params.get('category_id'),
                region_name=params.get('region_name'),
                limit=params.get('limit', 100),
                progress_callback=progress_callback
            )
            all_data = result['data']
            session.total_count = result.get('businesses_crawled', 0)
            session.email_count = result['email_count']
        else:
            regions = params.get('regions', ['서울', '경기', '부산', '대구', '인천'])
            max_pages = params.get('max_pages', 5)

            if crawler_type == 'all':
                result = run_all_crawlers(regions=regions, max_pages=max_pages, progress_callback=progress_callback)
                all_data = result['all_data']
                session.total_count = result['total_count']
                session.email_count = result['total_emails']
            else:
                result = run_crawler(crawler_type, regions=regions, max_pages=max_pages, progress_callback=progress_callback)
                all_data = result['data']
                session.total_count = result['count']
                session.email_count = result['email_count']

        # 결과 저장
        _crawling_progress[session_id]['message'] = '결과 저장 중...'

        for item in all_data:
            if crawler_type == 'local_business':
                CrawlResult.objects.create(
                    session=session,
                    category='local_business',
                    name=item.get('업체명', ''),
                    office_name=item.get('업체명', ''),
                    affiliation='',
                    address=item.get('주소', ''),
                    region=item.get('지역', ''),
                    phone=item.get('전화번호', ''),
                    email=item.get('이메일', ''),
                    specialty=item.get('웹사이트', ''),
                )
            else:
                category = None
                category_name = item.get('업종', '')
                for key, (name, _) in CRAWLER_MAP.items():
                    if name == category_name:
                        category = key
                        break
                if category:
                    CrawlResult.objects.create(
                        session=session,
                        category=category,
                        name=item.get('성명', '') or item.get('대표자', ''),
                        office_name=item.get('사무소명', ''),
                        affiliation=item.get('소속', ''),
                        address=item.get('주소', ''),
                        region=item.get('지역', ''),
                        phone=item.get('전화번호', ''),
                        email=item.get('이메일', ''),
                        specialty=item.get('전문분야', ''),
                    )

        # 엑셀 파일 생성
        _crawling_progress[session_id]['message'] = '엑셀 파일 생성 중...'
        excel_file = export_to_excel(all_data)
        if excel_file:
            filename = f"crawl_{crawler_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            session.result_file.save(filename, ContentFile(excel_file.read()))

        session.status = 'completed'
        session.completed_at = timezone.now()
        session.save()

        _crawling_progress[session_id] = {
            'status': 'completed',
            'message': f'완료! {session.total_count}건 수집, {session.email_count}개 이메일',
            'total_count': session.total_count,
            'email_count': session.email_count,
            'updated_at': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"백그라운드 크롤링 오류: {e}")
        import traceback
        traceback.print_exc()

        try:
            session = CrawlSession.objects.get(pk=session_id)
            session.status = 'failed'
            session.error_message = str(e)
            session.save()
        except:
            pass

        _crawling_progress[session_id] = {
            'status': 'failed',
            'message': f'오류: {str(e)}',
            'updated_at': datetime.now().isoformat()
        }


# ============== 크롤러 관리 뷰 ==============

@staff_member_required
def crawler_dashboard(request):
    """크롤러 대시보드"""
    recent_sessions = CrawlSession.objects.all()[:10]
    total_results = CrawlResult.objects.count()
    total_emails = CrawlResult.objects.exclude(email='').count()

    # 업종별 통계
    category_stats = {}
    for key, (name, _) in CRAWLER_MAP.items():
        count = CrawlResult.objects.filter(category=key).count()
        email_count = CrawlResult.objects.filter(category=key).exclude(email='').count()
        category_stats[name] = {'count': count, 'email_count': email_count}

    # 진행 중인 세션 확인
    running_sessions = CrawlSession.objects.filter(status='running')

    context = {
        'title': '크롤러 관리',
        'recent_sessions': recent_sessions,
        'total_results': total_results,
        'total_emails': total_emails,
        'category_stats': category_stats,
        'crawler_types': CRAWLER_MAP,
        'running_sessions': running_sessions,
    }
    return render(request, 'admin/crawler/dashboard.html', context)


@staff_member_required
@csrf_protect
def run_crawler_view(request):
    """크롤러 실행 (백그라운드)"""
    if request.method == 'POST':
        crawler_type = request.POST.get('crawler_type', 'all')
        regions = request.POST.getlist('regions')
        max_pages = int(request.POST.get('max_pages', 5))

        # LocalBusiness 크롤러인 경우
        if crawler_type == 'local_business':
            category_id = request.POST.get('lb_category_id')
            region_name = request.POST.get('lb_region_name', '').strip()
            limit = int(request.POST.get('lb_limit', 100))

            # 세션 생성
            session = CrawlSession.objects.create(
                crawler_type='local_business',
                regions=[region_name] if region_name else [],
                max_pages=limit,
                status='running',
                created_by=request.user
            )

            # 백그라운드 실행
            params = {
                'category_id': int(category_id) if category_id else None,
                'region_name': region_name if region_name else None,
                'limit': limit
            }
            thread = threading.Thread(
                target=run_crawling_task,
                args=(session.id, 'local_business', params),
                daemon=True
            )
            thread.start()

            # 진행 상태 페이지로 리다이렉트
            return redirect('admin_crawler_progress', session_id=session.id)

        # 기존 협회 크롤러
        if not regions:
            regions = ['서울', '경기', '부산', '대구', '인천']

        # 세션 생성
        session = CrawlSession.objects.create(
            crawler_type=crawler_type,
            regions=regions,
            max_pages=max_pages,
            status='running',
            created_by=request.user
        )

        # 백그라운드 실행
        params = {
            'regions': regions,
            'max_pages': max_pages
        }
        thread = threading.Thread(
            target=run_crawling_task,
            args=(session.id, crawler_type, params),
            daemon=True
        )
        thread.start()

        # 진행 상태 페이지로 리다이렉트
        return redirect('admin_crawler_progress', session_id=session.id)

    # GET 요청
    # LocalBusiness 카테고리 및 지역 목록 가져오기
    lb_categories = get_local_business_categories()
    lb_regions = get_local_business_regions()

    context = {
        'title': '크롤러 실행',
        'crawler_types': [('all', '전체 (협회)')] + [(k, v[0]) for k, v in CRAWLER_MAP.items()] + [('local_business', 'DB 업체 웹사이트')],
        'regions': ['서울', '경기', '부산', '대구', '인천', '광주', '대전', '울산', '세종',
                    '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주'],
        'lb_categories': lb_categories,
        'lb_regions': lb_regions,
    }
    return render(request, 'admin/crawler/run_crawler.html', context)


@staff_member_required
def crawler_progress_view(request, session_id):
    """크롤링 진행 상태 페이지"""
    try:
        session = CrawlSession.objects.get(pk=session_id)
    except CrawlSession.DoesNotExist:
        messages.error(request, "세션을 찾을 수 없습니다.")
        return redirect('admin_crawler_dashboard')

    context = {
        'title': '크롤링 진행 상태',
        'session': session,
    }
    return render(request, 'admin/crawler/progress.html', context)


@csrf_exempt
def crawler_status_api(request, session_id):
    """크롤링 진행 상태 API (AJAX)"""
    global _crawling_progress

    try:
        session = CrawlSession.objects.get(pk=session_id)

        # 메모리에 진행 상태가 있으면 사용
        if session_id in _crawling_progress:
            progress = _crawling_progress[session_id]
            return JsonResponse({
                'session_id': session_id,
                'status': progress.get('status', session.status),
                'message': progress.get('message', ''),
                'total_count': progress.get('total_count', session.total_count),
                'email_count': progress.get('email_count', session.email_count),
            })

        # DB에서 상태 가져오기
        return JsonResponse({
            'session_id': session_id,
            'status': session.status,
            'message': '완료' if session.status == 'completed' else (session.error_message if session.status == 'failed' else '진행 중...'),
            'total_count': session.total_count,
            'email_count': session.email_count,
        })

    except CrawlSession.DoesNotExist:
        return JsonResponse({'error': '세션을 찾을 수 없습니다.'}, status=404)


@staff_member_required
def download_session_excel(request, session_id):
    """세션 결과 엑셀 다운로드"""
    try:
        session = CrawlSession.objects.get(pk=session_id)

        # 저장된 파일이 있으면 반환
        if session.result_file:
            response = HttpResponse(
                session.result_file.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{session.result_file.name}"'
            return response

        # 없으면 생성
        data = []
        for result in session.results.all():
            data.append({
                '업종': result.get_category_display(),
                '성명': result.name,
                '사무소명': result.office_name,
                '소속': result.affiliation,
                '주소': result.address,
                '지역': result.region,
                '전화번호': result.phone,
                '이메일': result.email,
                '전문분야': result.specialty,
            })

        excel_file = export_to_excel(data)
        if excel_file:
            response = HttpResponse(
                excel_file.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="session_{session_id}_{datetime.now().strftime("%Y%m%d")}.xlsx"'
            return response

        messages.warning(request, "다운로드할 데이터가 없습니다.")
        return redirect('admin_crawler_dashboard')

    except CrawlSession.DoesNotExist:
        messages.error(request, "세션을 찾을 수 없습니다.")
        return redirect('admin_crawler_dashboard')


@staff_member_required
def email_campaign_create(request):
    """이메일 캠페인 생성"""
    if request.method == 'POST':
        name = request.POST.get('name')
        subject = request.POST.get('subject')
        content = request.POST.get('content')
        categories = request.POST.getlist('categories')
        regions = request.POST.getlist('regions')

        # 캠페인 생성
        campaign = EmailCampaign.objects.create(
            name=name,
            subject=subject,
            content=content,
            target_categories=categories,
            target_regions=regions,
            created_by=request.user,
        )

        # 대상 설정
        queryset = CrawlResult.objects.exclude(email='')
        if categories:
            queryset = queryset.filter(category__in=categories)
        if regions:
            queryset = queryset.filter(region__in=regions)

        campaign.target_results.set(queryset)
        campaign.total_count = queryset.count()
        campaign.save()

        messages.success(request, f"캠페인이 생성되었습니다. 대상: {campaign.total_count}건")
        return redirect('admin:api_emailcampaign_change', campaign.pk)

    # GET
    categories = [(k, v[0]) for k, v in CRAWLER_MAP.items()]
    regions = CrawlResult.objects.values_list('region', flat=True).distinct()

    context = {
        'title': '이메일 캠페인 생성',
        'categories': categories,
        'regions': list(regions),
    }
    return render(request, 'admin/crawler/email_campaign.html', context)


@staff_member_required
def send_email_campaign(request, campaign_id):
    """이메일 캠페인 발송"""
    try:
        from .utils.email_sender import EmailSender

        campaign = EmailCampaign.objects.get(pk=campaign_id)

        if campaign.status not in ['draft', 'failed']:
            messages.warning(request, "이미 발송 중이거나 완료된 캠페인입니다.")
            return redirect('admin:api_emailcampaign_change', campaign.pk)

        campaign.status = 'sending'
        campaign.started_at = timezone.now()
        campaign.save()

        email_sender = EmailSender()
        success = 0
        fail = 0

        for result in campaign.target_results.all():
            if not result.email:
                continue

            try:
                # 이메일 발송
                email_sender.send_email(
                    to_email=result.email,
                    subject=campaign.subject,
                    body=campaign.content,
                )
                success += 1
                result.email_sent = True
                result.email_sent_at = timezone.now()
                result.save()
            except Exception as e:
                logger.error(f"이메일 발송 실패 ({result.email}): {e}")
                fail += 1

        campaign.success_count = success
        campaign.fail_count = fail
        campaign.status = 'completed'
        campaign.completed_at = timezone.now()
        campaign.save()

        messages.success(request, f"이메일 발송 완료! 성공: {success}건, 실패: {fail}건")

    except EmailCampaign.DoesNotExist:
        messages.error(request, "캠페인을 찾을 수 없습니다.")
    except Exception as e:
        logger.error(f"캠페인 발송 오류: {e}")
        messages.error(request, f"발송 오류: {e}")

    return redirect('admin:api_emailcampaign_changelist')


# ============== URL 패턴 ==============
def get_crawler_urls():
    """크롤러 관련 URL 패턴 반환"""
    return [
        path('admin/crawler/', crawler_dashboard, name='admin_crawler_dashboard'),
        path('admin/crawler/run/', run_crawler_view, name='admin_crawler_run'),
        path('admin/crawler/progress/<int:session_id>/', crawler_progress_view, name='admin_crawler_progress'),
        path('admin/crawler/status/<int:session_id>/', crawler_status_api, name='admin_crawler_status'),
        path('admin/crawler/download/<int:session_id>/', download_session_excel, name='admin_crawler_download'),
        path('admin/crawler/email/create/', email_campaign_create, name='admin_crawler_email_create'),
        path('admin/crawler/email/send/<int:campaign_id>/', send_email_campaign, name='admin_crawler_email_send'),
    ]
