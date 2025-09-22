# Generated manually to drop UsedPhoneReview model and table

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('used_phones', '0022_remove_usedphonefavorite'),
    ]

    operations = [
        # Drop the used_phone_reviews table
        migrations.RunSQL(
            "DROP TABLE IF EXISTS used_phone_reviews;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]