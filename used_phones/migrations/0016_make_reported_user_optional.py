# Generated manually by Assistant

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('used_phones', '0015_fix_related_name_conflicts'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usedphonereport',
            name='reported_user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='received_used_phone_reports', to=settings.AUTH_USER_MODEL, verbose_name='신고대상'),
        ),
        migrations.AddField(
            model_name='usedphonereport',
            name='reported_nickname',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='신고대상 닉네임'),
        ),
        migrations.AddField(
            model_name='usedphonereport',
            name='reported_phone_number',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='신고대상 연락처'),
        ),
    ]