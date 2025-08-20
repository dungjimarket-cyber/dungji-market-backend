from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from api.models import Region
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Create test seller accounts (seller1-seller10) with business verification bypassed'

    def handle(self, *args, **options):
        # 서울특별시 강남구를 기본 지역으로 설정
        default_region = Region.objects.filter(
            name='강남구',
            full_name__contains='서울특별시'
        ).first()
        
        created_count = 0
        
        for i in range(1, 11):
            username = f'seller{i}'
            
            # 이미 존재하는 계정은 건너뛰기
            if User.objects.filter(username=username).exists():
                self.stdout.write(f'계정 {username}은 이미 존재합니다.')
                continue
            
            try:
                user = User.objects.create(
                    username=username,
                    email=f'{username}@test.com',
                    phone_number=f'010{1000 + i:04d}{i:04d}',  # 010-1001-0001 형태
                    nickname=f'테스트판매자{i}',
                    first_name=f'테스트판매자{i}',
                    role='seller',
                    sns_type='email',
                    business_number=f'12345678{i:02d}',  # 사업자등록번호 (10자리)
                    representative_name=f'테스트대표자{i}',
                    is_business_verified=True,  # 사업자 인증 완료 처리
                    address_region=default_region,
                    address_detail=f'테스트 사업장 주소 {i}',
                    is_remote_sales_enabled=False
                )
                
                # 기본 비밀번호 설정 (test123!)
                user.set_password('test123!')
                user.save()
                
                # 입찰권 10매 지급
                from api.models import BidToken
                for j in range(10):
                    BidToken.objects.create(
                        seller=user,
                        token_type='single',
                        status='active'
                    )
                
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'테스트 계정 생성 완료: {username} (비밀번호: test123!)')
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'계정 {username} 생성 실패: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'총 {created_count}개의 테스트 계정이 생성되었습니다.')
        )
        
        # 생성된 계정 목록 출력
        if created_count > 0:
            self.stdout.write('\n=== 생성된 테스트 계정 목록 ===')
            for i in range(1, 11):
                username = f'seller{i}'
                if User.objects.filter(username=username).exists():
                    self.stdout.write(f'ID: {username}, 비밀번호: test123!')