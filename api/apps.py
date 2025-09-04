from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"
    verbose_name = "둥지마켓 관리"
    
    def ready(self):
        # Admin 사이트 메뉴 순서 조정
        from django.contrib import admin
        
        # 모델 순서 정의
        model_order = [
            'User',
            'GroupBuy',
            'Bid',
            'Participation',
            'Payment',
            'NoShowReport',
            'NoShowObjection',
            'Penalty',  # 노쇼 신고 바로 다음에 패널티 관리
            'BidToken',
            'Category',
            'Product',
            'Notification',
        ]
        
        # Admin 사이트 제목 변경
        admin.site.site_header = "둥지마켓 관리 시스템"
        admin.site.site_title = "둥지마켓 Admin"
        admin.site.index_title = "둥지마켓 관리"
