# Generated migration to remove ElectronicsFavorite model
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('used_electronics', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ElectronicsFavorite',
        ),
    ]