# Generated manually for discount link click tracking feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0099_add_deal_type_to_custom_groupbuy'),
    ]

    operations = [
        migrations.AddField(
            model_name='customgroupbuy',
            name='discount_url_clicks',
            field=models.PositiveIntegerField(default=0, verbose_name='할인링크 클릭수'),
        ),
    ]
