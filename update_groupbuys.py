import os
import django
import sys

# Django 설정 로드
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
django.setup()

from django.db import connection
from api.models import GroupBuy

def update_groupbuys_directly():
    """
    직접 SQL을 사용하여 GroupBuy 모델의 product_name 필드를 업데이트합니다.
    이렇게 하면 save() 메서드가 호출되지 않아 알림 생성 로직을 우회할 수 있습니다.
    """
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE api_groupbuy
            SET product_name = (
                SELECT name 
                FROM api_product 
                WHERE api_product.id = api_groupbuy.product_id
            )
            WHERE product_name IS NULL OR product_name = '';
        """)
        rows_updated = cursor.rowcount
        print(f"총 {rows_updated}개의 공동구매 데이터를 업데이트했습니다.")

if __name__ == "__main__":
    print("공동구매 데이터 업데이트를 시작합니다...")
    update_groupbuys_directly()
    print("공동구매 데이터 업데이트가 완료되었습니다.")
