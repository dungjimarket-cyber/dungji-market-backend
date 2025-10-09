# Generated manually for changing OneToOneField to ForeignKey

from django.conf import settings
from django.db import migrations, models, connection
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('used_electronics', '0007_electronicsdeletepenalty'),
    ]

    operations = [
        # Step 1: Change OneToOneField to ForeignKey (preserves data)
        migrations.AlterField(
            model_name='electronicstransaction',
            name='electronics',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='transactions',
                to='used_electronics.usedelectronics'
            ),
        ),

        # Step 2: Add offer field
        migrations.AddField(
            model_name='electronicstransaction',
            name='offer',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='transaction',
                to='used_electronics.electronicsoffer'
            ),
        ),
    ]

    def apply(self, project_state, schema_editor, collect_sql=False):
        """인덱스가 이미 존재하면 스킵 (이미 ForeignKey로 변경된 상태)"""
        with connection.cursor() as cursor:
            # ForeignKey 인덱스가 이미 존재하는지 확인
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM pg_indexes
                    WHERE indexname = 'used_electronics_transactions_electronics_id_f317f1ae'
                );
            """)
            index_exists = cursor.fetchone()[0]

            # offer 필드가 이미 존재하는지 확인
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns
                    WHERE table_name = 'used_electronics_transactions'
                    AND column_name = 'offer_id'
                );
            """)
            offer_field_exists = cursor.fetchone()[0]

        if index_exists and offer_field_exists:
            # 이미 마이그레이션이 적용된 상태면 기록만 추가하고 스킵
            return project_state
        else:
            # 정상 실행
            return super().apply(project_state, schema_editor, collect_sql)