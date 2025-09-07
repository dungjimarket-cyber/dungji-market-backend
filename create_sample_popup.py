#!/usr/bin/env python
"""
샘플 팝업 생성 스크립트
"""
import os
import sys
import django
from datetime import datetime, timedelta

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models_popup import Popup
from django.contrib.auth import get_user_model

User = get_user_model()

def create_sample_popup():
    """샘플 팝업 생성"""
    
    # 관리자 계정 찾기
    admin_user = User.objects.filter(is_staff=True).first()
    if not admin_user:
        print("관리자 계정이 없습니다. 먼저 관리자 계정을 생성해주세요.")
        return
    
    # 기존 팝업 확인
    existing = Popup.objects.filter(title="🎉 둥지마켓 오픈 이벤트").first()
    if existing:
        print(f"기존 팝업을 업데이트합니다: {existing.title}")
        popup = existing
    else:
        popup = Popup()
        print("새 팝업을 생성합니다.")
    
    # 팝업 데이터 설정
    popup.title = "🎉 둥지마켓 오픈 이벤트"
    popup.is_active = True
    popup.priority = 10
    popup.popup_type = 'text'
    popup.content = """
    <div style="text-align: center; padding: 20px;">
        <h2 style="color: #6B46C1; margin-bottom: 20px;">🎊 둥지마켓 그랜드 오픈! 🎊</h2>
        
        <p style="font-size: 18px; margin-bottom: 15px;">
            <strong>지금 가입하면 특별 혜택!</strong>
        </p>
        
        <ul style="text-align: left; max-width: 400px; margin: 0 auto 20px;">
            <li>✅ 첫 공구 참여시 5% 추가 할인</li>
            <li>✅ 판매자 입찰권 3개 무료 제공</li>
            <li>✅ 친구 초대시 포인트 적립</li>
        </ul>
        
        <p style="color: #666; font-size: 14px;">
            이벤트 기간: 2025.01.01 ~ 2025.01.31
        </p>
    </div>
    """
    popup.link_url = "https://dungjimarket.com/events"
    popup.link_target = '_blank'
    popup.position = 'center'
    popup.width = 500
    popup.height = 400
    popup.start_date = datetime.now()
    popup.end_date = datetime.now() + timedelta(days=30)
    popup.show_on_main = True
    popup.show_on_mobile = True
    popup.show_today_close = True
    popup.show_week_close = True
    popup.author = admin_user
    
    popup.save()
    
    print(f"✅ 팝업 생성/업데이트 완료!")
    print(f"   - ID: {popup.id}")
    print(f"   - 제목: {popup.title}")
    print(f"   - 활성화: {popup.is_active}")
    print(f"   - 메인 표시: {popup.show_on_main}")
    print(f"   - 시작일: {popup.start_date}")
    print(f"   - 종료일: {popup.end_date}")
    
    # 현재 활성 팝업 확인
    active_count = Popup.objects.filter(
        is_active=True,
        show_on_main=True,
        start_date__lte=datetime.now()
    ).count()
    
    print(f"\n📊 현재 활성 팝업 수: {active_count}개")

if __name__ == "__main__":
    create_sample_popup()