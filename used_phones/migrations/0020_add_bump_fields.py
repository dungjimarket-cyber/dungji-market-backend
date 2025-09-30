# Generated manually for adding bump fields to UsedPhone model
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('used_phones', '0019_auto_20250123_0000'),  # Adjust to your last migration
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