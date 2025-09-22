# Generated migration to remove UsedPhoneFavorite model
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('used_phones', '0021_add_duration_hours_default'),
    ]

    operations = [
        migrations.DeleteModel(
            name='UsedPhoneFavorite',
        ),
    ]