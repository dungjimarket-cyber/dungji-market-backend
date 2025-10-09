# Generated manually for changing OneToOneField to ForeignKey

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('used_electronics', '0007_electronicsdeletepenalty'),
    ]

    operations = [
        # Step 1: Remove the old OneToOneField
        migrations.RemoveField(
            model_name='electronicstransaction',
            name='electronics',
        ),

        # Step 2: Add new ForeignKey field
        migrations.AddField(
            model_name='electronicstransaction',
            name='electronics',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='transactions',
                to='used_electronics.usedelectronics'
            ),
            preserve_default=False,
        ),

        # Step 3: Add offer field
        migrations.AddField(
            model_name='electronicstransaction',
            name='offer',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='transaction',
                to='used_electronics.electronicsoffer'
            ),
        ),
    ]