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
        # Step 1: Change OneToOneField to ForeignKey (preserves data)
        migrations.AlterField(
            model_name='electronicstransaction',
            name='electronics',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='transactions',
                to='used_electronics.usedelectronics'
            ),
        ),

        # Step 2: Add offer field
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