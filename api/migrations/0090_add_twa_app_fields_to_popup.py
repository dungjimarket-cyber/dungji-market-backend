# Generated migration for TWA app popup fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0089_conditional_migrations'),  # 이전 마이그레이션 번호 (실제로는 최신 번호로 변경)
    ]

    operations = [
        migrations.AddField(
            model_name='popup',
            name='hide_on_twa_app',
            field=models.BooleanField(default=False, help_text='Play Store 앱(TWA)에서 팝업을 표시하지 않음 (웹에서만 표시)', verbose_name='웹에서만 표시'),
        ),
        migrations.AddField(
            model_name='popup',
            name='show_only_on_twa_app',
            field=models.BooleanField(default=False, help_text='Play Store 앱(TWA)에서만 팝업을 표시 (웹에서는 숨김)', verbose_name='앱에서만 표시'),
        ),
    ]
