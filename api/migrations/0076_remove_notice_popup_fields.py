# Generated manually to remove popup fields from Notice model

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0075_rename_payment_tables'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='notice',
            name='popup_width',
        ),
        migrations.RemoveField(
            model_name='notice',
            name='popup_height',
        ),
        migrations.RemoveField(
            model_name='notice',
            name='popup_image',
        ),
        migrations.RemoveField(
            model_name='notice',
            name='popup_link',
        ),
        migrations.RemoveField(
            model_name='notice',
            name='popup_expires_at',
        ),
        migrations.RemoveField(
            model_name='notice',
            name='popup_type',
        ),
        migrations.RemoveField(
            model_name='notice',
            name='popup_link_target',
        ),
        migrations.RemoveField(
            model_name='notice',
            name='popup_show_today_close',
        ),
    ]