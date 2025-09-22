"""
통합 후기 모델 필드 수정 - 실제 모델과 일치시키기
"""
from django.db import migrations, models
import django.db.models.deletion
from django.core.validators import MinValueValidator, MaxValueValidator


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0081_unified_favorites_reviews'),
    ]

    operations = [
        # 1. 먼저 unique_together 제거 (item_id 참조 때문에)
        migrations.AlterUniqueTogether(
            name='unifiedreview',
            unique_together=set(),
        ),

        # 2. reviewed_user를 reviewee로 이름 변경
        migrations.RenameField(
            model_name='unifiedreview',
            old_name='reviewed_user',
            new_name='reviewee',
        ),

        # 3. transaction_type을 is_from_buyer로 변경
        migrations.RemoveField(
            model_name='unifiedreview',
            name='transaction_type',
        ),
        migrations.AddField(
            model_name='unifiedreview',
            name='is_from_buyer',
            field=models.BooleanField(default=True, verbose_name='구매자가 작성'),
        ),

        # 4. transaction_id 필드 추가 (item_id 대신 사용)
        migrations.RemoveField(
            model_name='unifiedreview',
            name='item_id',
        ),
        migrations.AddField(
            model_name='unifiedreview',
            name='transaction_id',
            field=models.PositiveIntegerField(default=1, verbose_name='거래 ID'),
            preserve_default=False,
        ),

        # 4. 추가 평가 항목들 추가
        migrations.AddField(
            model_name='unifiedreview',
            name='is_punctual',
            field=models.BooleanField(default=False, verbose_name='시간 약속을 잘 지켜요'),
        ),
        migrations.AddField(
            model_name='unifiedreview',
            name='is_friendly',
            field=models.BooleanField(default=False, verbose_name='친절해요'),
        ),
        migrations.AddField(
            model_name='unifiedreview',
            name='is_honest',
            field=models.BooleanField(default=False, verbose_name='정직해요'),
        ),
        migrations.AddField(
            model_name='unifiedreview',
            name='is_fast_response',
            field=models.BooleanField(default=False, verbose_name='응답이 빨라요'),
        ),

        # 5. updated_at 필드 추가
        migrations.AddField(
            model_name='unifiedreview',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='후기 수정일'),
        ),

        # 6. unique_together 새로 설정
        migrations.AlterUniqueTogether(
            name='unifiedreview',
            unique_together={('item_type', 'transaction_id', 'reviewer')},
        ),

        # 7. 인덱스 추가
        migrations.AddIndex(
            model_name='unifiedreview',
            index=models.Index(fields=['reviewee', '-created_at'], name='unified_rev_reviewe_idx'),
        ),
        migrations.AddIndex(
            model_name='unifiedreview',
            index=models.Index(fields=['reviewer', '-created_at'], name='unified_rev_reviewer_idx'),
        ),
        migrations.AddIndex(
            model_name='unifiedreview',
            index=models.Index(fields=['rating'], name='unified_rev_rating_idx'),
        ),
    ]