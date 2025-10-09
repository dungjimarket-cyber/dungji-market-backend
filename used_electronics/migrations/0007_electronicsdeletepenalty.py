# Generated manually for ElectronicsDeletePenalty model

from django.conf import settings
from django.db import migrations, models, connection
import django.db.models.deletion


def check_and_create_table(apps, schema_editor):
    """테이블이 없을 때만 생성"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'electronics_delete_penalties'
            );
        """)
        table_exists = cursor.fetchone()[0]

    if not table_exists:
        # 테이블이 없으면 생성
        ElectronicsDeletePenalty = apps.get_model('used_electronics', 'ElectronicsDeletePenalty')
        schema_editor.create_model(ElectronicsDeletePenalty)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('used_electronics', '0006_electronicstradecancellation'),
    ]

    operations = [
        # 먼저 모델 정의
        migrations.CreateModel(
            name='ElectronicsDeletePenalty',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('electronics_model', models.CharField(max_length=100, verbose_name='삭제된 상품명')),
                ('had_offers', models.BooleanField(default=False, verbose_name='견적 존재 여부')),
                ('penalty_end', models.DateTimeField(verbose_name='패널티 종료 시간')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='electronics_delete_penalties', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': '전자제품 삭제 패널티',
                'verbose_name_plural': '전자제품 삭제 패널티',
                'db_table': 'electronics_delete_penalties',
                'ordering': ['-created_at'],
            },
        ),
    ]

    def apply(self, project_state, schema_editor, collect_sql=False):
        """테이블이 이미 존재하면 스킵"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'electronics_delete_penalties'
                );
            """)
            table_exists = cursor.fetchone()[0]

        if table_exists:
            # 테이블이 이미 존재하면 마이그레이션 기록만 추가하고 스킵
            return project_state
        else:
            # 테이블이 없으면 정상 실행
            return super().apply(project_state, schema_editor, collect_sql)
