# Generated manually for custom groupbuy notice

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0095_add_bump_fields_to_custom_groupbuy'),
    ]

    operations = [
        migrations.AddField(
            model_name='notice',
            name='show_in_custom',
            field=models.BooleanField(default=False, help_text='커스텀 공구 목록 페이지에 노출', verbose_name='커스텀 공구 목록'),
        ),
    ]
