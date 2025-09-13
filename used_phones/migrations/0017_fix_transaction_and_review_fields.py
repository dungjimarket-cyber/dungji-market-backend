# Generated manually to fix missing fields in UsedPhoneTransaction and UsedPhoneReview
from django.conf import settings
from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('used_phones', '0016_create_review_model'),
    ]

    operations = [
        # Rename price to final_price and update its properties in UsedPhoneTransaction
        migrations.RemoveField(
            model_name='usedphonetransaction',
            name='price',
        ),
        migrations.AddField(
            model_name='usedphonetransaction',
            name='final_price',
            field=models.IntegerField(
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(9900000)
                ],
                verbose_name='최종거래가격',
                default=0
            ),
            preserve_default=False,
        ),

        # Add missing fields to UsedPhoneTransaction
        migrations.AddField(
            model_name='usedphonetransaction',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='수정일'),
        ),
        migrations.AddField(
            model_name='usedphonetransaction',
            name='meeting_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='거래일시'),
        ),
        migrations.AddField(
            model_name='usedphonetransaction',
            name='meeting_location',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='거래장소'),
        ),

        # Update status choices for UsedPhoneTransaction
        migrations.AlterField(
            model_name='usedphonetransaction',
            name='status',
            field=models.CharField(
                choices=[
                    ('reserved', '예약중'),
                    ('completed', '거래완료'),
                    ('cancelled', '거래취소')
                ],
                default='reserved',
                max_length=20,
                verbose_name='거래 상태'
            ),
        ),

        # Remove unnecessary fields from UsedPhoneTransaction
        migrations.RemoveField(
            model_name='usedphonetransaction',
            name='cancelled_at',
        ),

        # Update related names to match the model
        migrations.AlterField(
            model_name='usedphonetransaction',
            name='buyer',
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name='bought_transactions',
                to=settings.AUTH_USER_MODEL,
                verbose_name='구매자'
            ),
        ),
        migrations.AlterField(
            model_name='usedphonetransaction',
            name='seller',
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name='sold_transactions',
                to=settings.AUTH_USER_MODEL,
                verbose_name='판매자'
            ),
        ),

        # Add updated_at field to UsedPhoneReview
        migrations.AddField(
            model_name='usedphonereview',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='수정일'),
        ),

        # Update boolean fields in UsedPhoneReview to allow null
        migrations.AlterField(
            model_name='usedphonereview',
            name='is_punctual',
            field=models.BooleanField(blank=True, null=True, verbose_name='시간약속준수'),
        ),
        migrations.AlterField(
            model_name='usedphonereview',
            name='is_friendly',
            field=models.BooleanField(blank=True, null=True, verbose_name='친절함'),
        ),
        migrations.AlterField(
            model_name='usedphonereview',
            name='is_honest',
            field=models.BooleanField(blank=True, null=True, verbose_name='정직한거래'),
        ),
        migrations.AlterField(
            model_name='usedphonereview',
            name='is_fast_response',
            field=models.BooleanField(blank=True, null=True, verbose_name='빠른응답'),
        ),

        # Update rating choices for UsedPhoneReview
        migrations.AlterField(
            model_name='usedphonereview',
            name='rating',
            field=models.IntegerField(
                choices=[
                    (5, '매우 만족'),
                    (4, '만족'),
                    (3, '보통'),
                    (2, '불만족'),
                    (1, '매우 불만족')
                ],
                verbose_name='평점'
            ),
        ),

        # Update related names for UsedPhoneReview
        migrations.AlterField(
            model_name='usedphonereview',
            name='reviewer',
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name='written_used_phone_reviews',
                to=settings.AUTH_USER_MODEL,
                verbose_name='평가자'
            ),
        ),
    ]