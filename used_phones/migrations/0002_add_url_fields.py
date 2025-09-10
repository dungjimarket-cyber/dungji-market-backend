# Generated migration to add missing URL fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('used_phones', '0001_initial'),
    ]

    operations = [
        # Try to add image_url field if it doesn't exist
        migrations.RunSQL(
            "ALTER TABLE used_phone_images ADD COLUMN IF NOT EXISTS image_url VARCHAR(500);",
            reverse_sql="ALTER TABLE used_phone_images DROP COLUMN IF EXISTS image_url;"
        ),
        
        # Try to add thumbnail_url field if it doesn't exist
        migrations.RunSQL(
            "ALTER TABLE used_phone_images ADD COLUMN IF NOT EXISTS thumbnail_url VARCHAR(500);",
            reverse_sql="ALTER TABLE used_phone_images DROP COLUMN IF EXISTS thumbnail_url;"
        ),
    ]