# Generated migration for fixing GroupBuy creator on_delete
# 회원 탈퇴 시 GroupBuy.creator를 NULL로 설정하도록 변경

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0124_add_crawler_models'),
    ]

    operations = [
        migrations.AlterField(
            model_name='groupbuy',
            name='creator',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='created_groupbuys',
                to=settings.AUTH_USER_MODEL,
                verbose_name='생성자'
            ),
        ),
    ]
