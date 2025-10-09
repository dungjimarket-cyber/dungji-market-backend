#!/usr/bin/env python
"""
Migration history 정리 스크립트
이미 적용된 0010, 0011, 0012를 0007, 0008, 0009, 0010으로 fake 처리
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dungji_market_backend.settings')
django.setup()

from django.db import connection

def fix_migration_history():
    """Migration history를 정리"""
    with connection.cursor() as cursor:
        # 기존 0010, 0011, 0012 마이그레이션 기록 확인
        cursor.execute("""
            SELECT name FROM django_migrations
            WHERE app = 'used_electronics'
            AND name IN (
                '0010_electronicsdeletepenalty',
                '0010_change_transaction_to_foreignkey',
                '0011_add_bump_fields',
                '0012_update_condition_grade_choices'
            )
            ORDER BY name;
        """)
        old_migrations = [row[0] for row in cursor.fetchall()]

        print(f"기존 마이그레이션: {old_migrations}")

        # 새 번호 매핑
        migration_mapping = {
            '0010_electronicsdeletepenalty': '0007_electronicsdeletepenalty',
            '0010_change_transaction_to_foreignkey': '0008_change_transaction_to_foreignkey',
            '0011_add_bump_fields': '0009_add_bump_fields',
            '0012_update_condition_grade_choices': '0010_update_condition_grade_choices'
        }

        # 이미 존재하는 새 번호 마이그레이션 확인
        cursor.execute("""
            SELECT name FROM django_migrations
            WHERE app = 'used_electronics'
            AND name IN (
                '0007_electronicsdeletepenalty',
                '0008_change_transaction_to_foreignkey',
                '0009_add_bump_fields',
                '0010_update_condition_grade_choices'
            )
            ORDER BY name;
        """)
        new_migrations = [row[0] for row in cursor.fetchall()]

        print(f"새 마이그레이션: {new_migrations}")

        # 각 old migration에 대해 new migration이 없으면 추가
        for old_name, new_name in migration_mapping.items():
            if old_name in old_migrations and new_name not in new_migrations:
                print(f"Adding fake migration: {new_name}")
                cursor.execute("""
                    INSERT INTO django_migrations (app, name, applied)
                    VALUES ('used_electronics', %s, NOW())
                """, [new_name])

        print("✅ Migration history 정리 완료!")

if __name__ == '__main__':
    fix_migration_history()
