# Generated manually for UnifiedBump model
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_unified_bump_if_not_exists(apps, schema_editor):
    """unified_bumps 테이블이 없을 때만 생성"""
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'unified_bumps'
            );
        """)
        table_exists = cursor.fetchone()[0]

    if not table_exists:
        # 테이블이 없으면 생성
        UnifiedBump = apps.get_model('api', 'UnifiedBump')
        schema_editor.create_model(UnifiedBump)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0088_notification_system_expansion'),
    ]

    operations = [
        migrations.RunPython(
            create_unified_bump_if_not_exists,
            reverse_code=migrations.RunPython.noop
        ),
    ]