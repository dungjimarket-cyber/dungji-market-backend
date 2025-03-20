from django.db import migrations, models
from django.db.models import F

def set_default_titles(apps, schema_editor):
    GroupBuy = apps.get_model('api', 'GroupBuy')
    for groupbuy in GroupBuy.objects.filter(title__isnull=True):
        if groupbuy.product:
            groupbuy.title = groupbuy.product.name
        else:
            groupbuy.title = f'공동구매 #{groupbuy.id}'
        groupbuy.save()

class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_groupbuy_description_groupbuy_title'),
    ]

    operations = [
        migrations.RunPython(set_default_titles),
        migrations.AlterField(
            model_name='groupbuy',
            name='title',
            field=models.CharField(max_length=255),
        ),
    ]
