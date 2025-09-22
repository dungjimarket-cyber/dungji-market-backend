"""
통합 찜/후기 모델 마이그레이션
기존 데이터를 새로운 통합 테이블로 이전
"""
from django.db import migrations, models
import django.db.models.deletion
from django.core.validators import MinValueValidator, MaxValueValidator


def migrate_favorites(apps, schema_editor):
    """기존 찜 데이터를 통합 테이블로 이전"""
    UnifiedFavorite = apps.get_model('api', 'UnifiedFavorite')

    phone_count = 0
    electronics_count = 0
    errors = []

    # 휴대폰 찜 마이그레이션
    try:
        PhoneFavorite = apps.get_model('used_phones', 'PhoneFavorite')
        phone_favorites = PhoneFavorite.objects.all()

        for favorite in phone_favorites:
            try:
                # 중복 체크
                if not UnifiedFavorite.objects.filter(
                    user=favorite.user,
                    item_type='phone',
                    item_id=favorite.phone_id
                ).exists():
                    UnifiedFavorite.objects.create(
                        user=favorite.user,
                        item_type='phone',
                        item_id=favorite.phone_id,
                        created_at=favorite.created_at
                    )
                    phone_count += 1
            except Exception as e:
                errors.append(f"Phone favorite {favorite.id}: {str(e)}")

        print(f"Successfully migrated {phone_count} phone favorites")
    except Exception as e:
        print(f"Phone favorites table not found or error: {e}")

    # 전자제품 찜 마이그레이션
    try:
        ElectronicsFavorite = apps.get_model('used_electronics', 'ElectronicsFavorite')
        electronics_favorites = ElectronicsFavorite.objects.all()

        for favorite in electronics_favorites:
            try:
                # 중복 체크
                if not UnifiedFavorite.objects.filter(
                    user=favorite.user,
                    item_type='electronics',
                    item_id=favorite.electronics_id
                ).exists():
                    UnifiedFavorite.objects.create(
                        user=favorite.user,
                        item_type='electronics',
                        item_id=favorite.electronics_id,
                        created_at=favorite.created_at
                    )
                    electronics_count += 1
            except Exception as e:
                errors.append(f"Electronics favorite {favorite.id}: {str(e)}")

        print(f"Successfully migrated {electronics_count} electronics favorites")
    except Exception as e:
        print(f"Electronics favorites table not found or error: {e}")

    if errors:
        print(f"Errors during migration: {errors}")

    print(f"Migration complete: {phone_count} phone favorites, {electronics_count} electronics favorites")


def migrate_reviews(apps, schema_editor):
    """기존 후기 데이터를 통합 테이블로 이전"""
    UnifiedReview = apps.get_model('api', 'UnifiedReview')

    phone_review_count = 0
    electronics_review_count = 0
    errors = []

    # 휴대폰 후기 마이그레이션 (있을 경우)
    try:
        PhoneReview = apps.get_model('used_phones', 'TransactionReview')
        phone_reviews = PhoneReview.objects.all()

        for review in phone_reviews:
            try:
                # 중복 체크
                if not UnifiedReview.objects.filter(
                    item_type='phone',
                    transaction_id=review.transaction_id,
                    reviewer=review.reviewer
                ).exists():
                    UnifiedReview.objects.create(
                        item_type='phone',
                        transaction_id=review.transaction_id,
                        reviewer=review.reviewer,
                        reviewee=review.reviewee,
                        rating=review.rating,
                        comment=review.comment,
                        is_punctual=getattr(review, 'is_punctual', False),
                        is_friendly=getattr(review, 'is_friendly', False),
                        is_honest=getattr(review, 'is_honest', False),
                        is_fast_response=getattr(review, 'is_fast_response', False),
                        is_from_buyer=getattr(review, 'is_from_buyer', True),
                        created_at=review.created_at,
                        updated_at=review.updated_at
                    )
                    phone_review_count += 1
            except Exception as e:
                errors.append(f"Phone review {review.id}: {str(e)}")

        print(f"Successfully migrated {phone_review_count} phone reviews")
    except Exception as e:
        print(f"Phone reviews table not found or error: {e}")

    # 전자제품 후기 마이그레이션 (있을 경우)
    try:
        ElectronicsReview = apps.get_model('used_electronics', 'TransactionReview')
        electronics_reviews = ElectronicsReview.objects.all()

        for review in electronics_reviews:
            try:
                # 중복 체크
                if not UnifiedReview.objects.filter(
                    item_type='electronics',
                    transaction_id=review.transaction_id,
                    reviewer=review.reviewer
                ).exists():
                    UnifiedReview.objects.create(
                        item_type='electronics',
                        transaction_id=review.transaction_id,
                        reviewer=review.reviewer,
                        reviewee=review.reviewee,
                        rating=review.rating,
                        comment=review.comment,
                        is_punctual=getattr(review, 'is_punctual', False),
                        is_friendly=getattr(review, 'is_friendly', False),
                        is_honest=getattr(review, 'is_honest', False),
                        is_fast_response=getattr(review, 'is_fast_response', False),
                        is_from_buyer=getattr(review, 'is_from_buyer', True),
                        created_at=review.created_at,
                        updated_at=review.updated_at
                    )
                    electronics_review_count += 1
            except Exception as e:
                errors.append(f"Electronics review {review.id}: {str(e)}")

        print(f"Successfully migrated {electronics_review_count} electronics reviews")
    except Exception as e:
        print(f"Electronics reviews table not found or error: {e}")

    if errors:
        print(f"Errors during migration: {errors}")

    print(f"Migration complete: {phone_review_count} phone reviews, {electronics_review_count} electronics reviews")


def reverse_migrate_favorites(apps, schema_editor):
    """롤백: 통합 테이블에서 기존 테이블로 복원"""
    UnifiedFavorite = apps.get_model('api', 'UnifiedFavorite')

    try:
        PhoneFavorite = apps.get_model('used_phones', 'PhoneFavorite')
        for favorite in UnifiedFavorite.objects.filter(item_type='phone'):
            PhoneFavorite.objects.create(
                user=favorite.user,
                phone_id=favorite.item_id,
                created_at=favorite.created_at
            )
    except:
        pass

    try:
        ElectronicsFavorite = apps.get_model('used_electronics', 'ElectronicsFavorite')
        for favorite in UnifiedFavorite.objects.filter(item_type='electronics'):
            ElectronicsFavorite.objects.create(
                user=favorite.user,
                electronics_id=favorite.item_id,
                created_at=favorite.created_at
            )
    except:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0080_add_unified_report_penalty_models'),
        ('used_phones', '0001_initial'),
        ('used_electronics', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UnifiedFavorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_type', models.CharField(choices=[('phone', '휴대폰'), ('electronics', '전자제품')], max_length=20, verbose_name='상품타입')),
                ('item_id', models.IntegerField(verbose_name='상품ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='찜한날짜')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='unified_favorites', to='auth.user')),
            ],
            options={
                'db_table': 'unified_favorites',
                'verbose_name': '통합 찜',
                'verbose_name_plural': '통합 찜 관리',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['user', '-created_at'], name='unified_fav_user_id_b8f5d7_idx'),
                    models.Index(fields=['item_type', 'item_id'], name='unified_fav_item_ty_5e8c9a_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='UnifiedReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_type', models.CharField(choices=[('phone', '휴대폰'), ('electronics', '전자제품')], max_length=20, verbose_name='상품타입')),
                ('transaction_id', models.IntegerField(verbose_name='거래ID')),
                ('rating', models.IntegerField(choices=[(5, '매우 만족'), (4, '만족'), (3, '보통'), (2, '불만족'), (1, '매우 불만족')], validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name='평점')),
                ('comment', models.TextField(max_length=500, verbose_name='후기내용')),
                ('is_punctual', models.BooleanField(default=False, verbose_name='시간약속잘지킴')),
                ('is_friendly', models.BooleanField(default=False, verbose_name='친절함')),
                ('is_honest', models.BooleanField(default=False, verbose_name='정직함')),
                ('is_fast_response', models.BooleanField(default=False, verbose_name='응답빠름')),
                ('is_from_buyer', models.BooleanField(default=True, verbose_name='구매자후기')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='작성일')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일')),
                ('reviewer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='unified_reviews_written', to='auth.user')),
                ('reviewee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='unified_reviews_received', to='auth.user')),
            ],
            options={
                'db_table': 'unified_reviews',
                'verbose_name': '통합 후기',
                'verbose_name_plural': '통합 후기 관리',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['reviewee', '-created_at'], name='unified_rev_reviewe_5f9c8a_idx'),
                    models.Index(fields=['reviewer', '-created_at'], name='unified_rev_reviewe_6a7d9b_idx'),
                    models.Index(fields=['rating'], name='unified_rev_rating_7b8e0c_idx'),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name='unifiedfavorite',
            constraint=models.UniqueConstraint(fields=('user', 'item_type', 'item_id'), name='unique_user_item_favorite'),
        ),
        migrations.AddConstraint(
            model_name='unifiedreview',
            constraint=models.UniqueConstraint(fields=('item_type', 'transaction_id', 'reviewer'), name='unique_transaction_reviewer'),
        ),
        migrations.RunPython(migrate_favorites, reverse_migrate_favorites),
        migrations.RunPython(migrate_reviews, reverse_code=migrations.RunPython.noop),
    ]