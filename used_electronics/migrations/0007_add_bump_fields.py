# Generated manually for adding bump fields to UsedElectronics model
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('used_electronics', '0006_auto_20250123_0000'),  # Adjust to your last migration
    ]

    operations = [
        migrations.AddField(
            model_name='usedelectronics',
            name='last_bumped_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='마지막 끌올'),
        ),
        migrations.AddField(
            model_name='usedelectronics',
            name='bump_count',
            field=models.PositiveIntegerField(default=0, verbose_name='끌올 횟수'),
        ),
    ]