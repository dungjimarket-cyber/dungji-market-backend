# Generated manually
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('used_phones', '0014_add_report_penalty_system'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usedphonedeletepenalty',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='used_phone_delete_penalties', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='usedphonepenalty',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='used_phone_report_penalties', to=settings.AUTH_USER_MODEL, verbose_name='패널티대상'),
        ),
    ]