# Generated manually to fix database column name mismatch
from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('used_phones', '0017_fix_transaction_and_review_fields'),
    ]

    operations = [
        migrations.RenameField(
            model_name='usedphoneoffer',
            old_name='amount',
            new_name='offered_price',
        ),
    ]