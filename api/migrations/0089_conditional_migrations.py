# Conditional migrations for existing tables
from django.conf import settings
from django.db import migrations, models, connection
import django.db.models.deletion


def check_table_exists(table_name):
    """테이블 존재 여부 확인"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = %s
            );
        """, [table_name])
        return cursor.fetchone()[0]


def conditional_create_unified_bump(apps, schema_editor):
    """unified_bumps 테이블이 없을 때만 생성"""
    if not check_table_exists('unified_bumps'):
        schema_editor.execute("""
            CREATE TABLE unified_bumps (
                id BIGSERIAL PRIMARY KEY,
                item_type VARCHAR(20) NOT NULL CHECK (item_type IN ('phone', 'electronics')),
                item_id INTEGER NOT NULL,
                bumped_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                is_free BOOLEAN NOT NULL DEFAULT TRUE,
                user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
                CONSTRAINT unified_bum_user_id_3b6f17_idx_unique UNIQUE (user_id, bumped_at)
            );
            CREATE INDEX unified_bum_user_id_3b6f17_idx ON unified_bumps (user_id, bumped_at DESC);
            CREATE INDEX unified_bum_item_ty_a7e2c9_idx ON unified_bumps (item_type, item_id, bumped_at DESC);
            CREATE INDEX unified_bum_user_id_9c3d82_idx ON unified_bumps (user_id, bumped_at);
        """)


def conditional_create_noshow_objection(apps, schema_editor):
    """api_noshowobjection 테이블이 없을 때만 생성"""
    if not check_table_exists('api_noshowobjection'):
        schema_editor.execute("""
            CREATE TABLE api_noshowobjection (
                id BIGSERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                evidence_image_1 VARCHAR(100),
                evidence_image_2 VARCHAR(100),
                evidence_image_3 VARCHAR(100),
                status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'resolved', 'rejected')),
                admin_comment TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                processed_at TIMESTAMPTZ,
                noshow_report_id INTEGER NOT NULL REFERENCES api_noshowreport(id) ON DELETE CASCADE,
                objector_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
                processed_by_id INTEGER REFERENCES auth_user(id) ON DELETE SET NULL,
                edit_count INTEGER NOT NULL DEFAULT 0,
                is_cancelled BOOLEAN NOT NULL DEFAULT FALSE,
                cancelled_at TIMESTAMPTZ,
                cancellation_reason TEXT NOT NULL DEFAULT '',
                CONSTRAINT unique_objection_per_report UNIQUE (noshow_report_id, objector_id)
            );
            CREATE INDEX api_noshowobjection_noshow_report_idx ON api_noshowobjection (noshow_report_id);
            CREATE INDEX api_noshowobjection_objector_idx ON api_noshowobjection (objector_id);
            CREATE INDEX api_noshowobjection_processed_by_idx ON api_noshowobjection (processed_by_id);
        """)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0088_notification_system_expansion'),
    ]

    operations = [
        migrations.RunPython(
            conditional_create_unified_bump,
            reverse_code=migrations.RunPython.noop
        ),
        migrations.RunPython(
            conditional_create_noshow_objection,
            reverse_code=migrations.RunPython.noop
        ),
    ]
