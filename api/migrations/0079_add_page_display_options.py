# Generated manually for page display options

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0078_nicknamechangehistory'),
    ]

    operations = [
        # Notice model - Add page display options
        migrations.AddField(
            model_name='notice',
            name='show_in_groupbuy',
            field=models.BooleanField(default=False, help_text='공구(견적) 목록 페이지에 노출', verbose_name='공구(견적) 목록'),
        ),
        migrations.AddField(
            model_name='notice',
            name='show_in_used',
            field=models.BooleanField(default=False, help_text='중고거래 목록 페이지에 노출', verbose_name='중고거래 목록'),
        ),
        migrations.AlterField(
            model_name='notice',
            name='show_in_main',
            field=models.BooleanField(default=False, help_text='메인 페이지에 노출', verbose_name='메인 페이지'),
        ),

        # Popup model - Add page display checkboxes
        migrations.AddField(
            model_name='popup',
            name='show_on_groupbuy_list',
            field=models.BooleanField(default=False, help_text='공구(견적) 목록 페이지에서 표시', verbose_name='공구 목록'),
        ),
        migrations.AddField(
            model_name='popup',
            name='show_on_groupbuy_detail',
            field=models.BooleanField(default=False, help_text='공구(견적) 상세 페이지에서 표시', verbose_name='공구 상세'),
        ),
        migrations.AddField(
            model_name='popup',
            name='show_on_used_list',
            field=models.BooleanField(default=False, help_text='중고거래 목록 페이지에서 표시', verbose_name='중고거래 목록'),
        ),
        migrations.AddField(
            model_name='popup',
            name='show_on_used_detail',
            field=models.BooleanField(default=False, help_text='중고거래 상세 페이지에서 표시', verbose_name='중고거래 상세'),
        ),
        migrations.AddField(
            model_name='popup',
            name='show_on_mypage',
            field=models.BooleanField(default=False, help_text='마이페이지에서 표시', verbose_name='마이페이지'),
        ),
        migrations.AlterField(
            model_name='popup',
            name='show_on_main',
            field=models.BooleanField(default=True, help_text='메인 페이지에서 팝업 표시', verbose_name='메인 페이지'),
        ),

        # Update deprecated fields
        migrations.AlterField(
            model_name='popup',
            name='show_pages',
            field=models.JSONField(blank=True, default=list, help_text='(사용하지 마세요) 위의 체크박스를 사용하세요', verbose_name='[구버전] 표시할 페이지'),
        ),
        migrations.AlterField(
            model_name='popup',
            name='exclude_pages',
            field=models.JSONField(blank=True, default=list, help_text='(사용하지 마세요) 위의 체크박스를 사용하세요', verbose_name='[구버전] 제외할 페이지'),
        ),
    ]