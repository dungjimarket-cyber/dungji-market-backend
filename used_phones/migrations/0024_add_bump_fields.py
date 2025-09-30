# Generated manually for adding bump fields to UsedPhone model
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('used_phones', '0023_drop_used_phone_review_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='usedphone',
            name='last_bumped_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='마지막 끌올'),
        ),
        migrations.AddField(
            model_name='usedphone',
            name='bump_count',
            field=models.PositiveIntegerField(default=0, verbose_name='끌올 횟수'),
        ),
    ]