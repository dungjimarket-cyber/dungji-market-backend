# Generated migration file

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0090_noshow_objection'),
    ]

    operations = [
        migrations.AddField(
            model_name='noshowobjection',
            name='edit_count',
            field=models.IntegerField(default=0, verbose_name='수정 횟수'),
        ),
        migrations.AddField(
            model_name='noshowobjection',
            name='is_cancelled',
            field=models.BooleanField(default=False, verbose_name='취소 여부'),
        ),
        migrations.AddField(
            model_name='noshowobjection',
            name='cancelled_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='취소일시'),
        ),
        migrations.AddField(
            model_name='noshowobjection',
            name='cancellation_reason',
            field=models.TextField(blank=True, verbose_name='취소 사유'),
        ),
    ]