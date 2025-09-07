"""
팝업 생성 관리 명령어
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.models_popup import Popup
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = '샘플 팝업 생성'

    def handle(self, *args, **options):
        # 관리자 계정 찾기
        admin_user = User.objects.filter(is_staff=True).first()
        if not admin_user:
            self.stdout.write(self.style.ERROR('관리자 계정이 없습니다.'))
            return
        
        # 팝업 생성
        popup, created = Popup.objects.update_or_create(
            title="🎉 둥지마켓 오픈 이벤트",
            defaults={
                'is_active': True,
                'priority': 10,
                'popup_type': 'text',
                'content': """
                <div style="text-align: center;">
                    <h2 style="color: #6B46C1;">🎊 둥지마켓 그랜드 오픈! 🎊</h2>
                    <p><strong>지금 가입하면 특별 혜택!</strong></p>
                    <ul style="text-align: left; max-width: 300px; margin: 0 auto;">
                        <li>✅ 첫 공구 참여시 5% 추가 할인</li>
                        <li>✅ 판매자 입찰권 3개 무료 제공</li>
                        <li>✅ 친구 초대시 포인트 적립</li>
                    </ul>
                    <p style="color: #666;">이벤트 기간: 2025.01.01 ~ 2025.01.31</p>
                </div>
                """,
                'link_url': 'https://dungjimarket.com/events',
                'link_target': '_blank',
                'position': 'center',
                'width': 500,
                'height': 400,
                'start_date': timezone.now(),
                'end_date': timezone.now() + timedelta(days=30),
                'show_on_main': True,
                'show_on_mobile': True,
                'show_today_close': True,
                'show_week_close': True,
                'author': admin_user
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'팝업 생성 완료: {popup.title}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'팝업 업데이트 완료: {popup.title}'))
        
        # 활성 팝업 확인
        active_popups = Popup.objects.filter(
            is_active=True,
            show_on_main=True,
            start_date__lte=timezone.now()
        ).filter(
            end_date__isnull=True
        ) | Popup.objects.filter(
            is_active=True,
            show_on_main=True,
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        )
        
        self.stdout.write(f'현재 활성 팝업 수: {active_popups.count()}개')
        for p in active_popups:
            self.stdout.write(f'  - {p.title} (ID: {p.id})')