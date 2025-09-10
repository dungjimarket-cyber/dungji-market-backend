# Generated migration for used_phones app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0001_initial'),  # Depends on Region model from api app
    ]

    operations = [
        migrations.CreateModel(
            name='UsedPhone',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('brand', models.CharField(choices=[('samsung', 'Samsung'), ('apple', 'Apple'), ('lg', 'LG'), ('xiaomi', 'Xiaomi'), ('other', 'Other')], max_length=20)),
                ('series', models.CharField(blank=True, max_length=50, null=True)),
                ('model', models.CharField(max_length=100)),
                ('storage', models.IntegerField(blank=True, choices=[(64, '64GB'), (128, '128GB'), (256, '256GB'), (512, '512GB'), (1024, '1TB')], null=True)),
                ('color', models.CharField(blank=True, max_length=30, null=True)),
                ('condition_grade', models.CharField(choices=[('A', 'A Grade (Excellent)'), ('B', 'B Grade (Good)'), ('C', 'C Grade (Fair)')], max_length=1)),
                ('condition_description', models.TextField(blank=True, null=True)),
                ('battery_status', models.CharField(blank=True, choices=[('85+', '85%+'), ('80-85', '80-85%'), ('under', 'Under 80%'), ('unknown', 'Unknown')], max_length=10, null=True)),
                ('purchase_period', models.CharField(blank=True, choices=[('1', 'Within 1 month'), ('3', 'Within 3 months'), ('6', 'Within 6 months'), ('12', 'Within 1 year'), ('over', 'Over 1 year')], max_length=10, null=True)),
                ('manufacture_date', models.CharField(blank=True, max_length=7, null=True)),
                ('price', models.DecimalField(decimal_places=0, max_digits=10)),
                ('accept_offers', models.BooleanField(default=False)),
                ('min_offer_price', models.DecimalField(blank=True, decimal_places=0, max_digits=10, null=True)),
                ('accessories', models.JSONField(blank=True, default=list)),
                ('has_box', models.BooleanField(default=False)),
                ('has_charger', models.BooleanField(default=False)),
                ('has_earphones', models.BooleanField(default=False)),
                ('trade_location', models.CharField(blank=True, max_length=200, null=True)),
                ('meeting_place', models.CharField(blank=True, max_length=200, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('status', models.CharField(choices=[('active', 'Active'), ('reserved', 'Reserved'), ('sold', 'Sold'), ('deleted', 'Deleted')], default='active', max_length=20)),
                ('view_count', models.PositiveIntegerField(default=0)),
                ('offer_count', models.PositiveIntegerField(default=0)),
                ('favorite_count', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('reserved_at', models.DateTimeField(blank=True, null=True)),
                ('sold_at', models.DateTimeField(blank=True, null=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('region', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.region')),
                ('seller', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='used_phones', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Used Phone',
                'verbose_name_plural': 'Used Phones',
                'db_table': 'used_phones',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='UsedPhoneOffer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=0, max_digits=10)),
                ('message', models.TextField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected'), ('cancelled', 'Cancelled'), ('expired', 'Expired')], default='pending', max_length=20)),
                ('seller_message', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('expired_at', models.DateTimeField(blank=True, null=True)),
                ('buyer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='used_offers', to=settings.AUTH_USER_MODEL)),
                ('phone', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='offers', to='used_phones.usedphone')),
            ],
            options={
                'verbose_name': 'Used Phone Offer',
                'verbose_name_plural': 'Used Phone Offers',
                'db_table': 'used_phone_offers',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='UsedPhoneImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='used_phones/%Y/%m/%d/')),
                ('image_url', models.URLField(max_length=500, blank=True)),
                ('thumbnail', models.ImageField(blank=True, null=True, upload_to='used_phones/thumbnails/%Y/%m/%d/')),
                ('thumbnail_url', models.URLField(max_length=500, blank=True, null=True)),
                ('is_main', models.BooleanField(default=False)),
                ('order', models.PositiveIntegerField(default=0)),
                ('file_size', models.PositiveIntegerField(blank=True, null=True)),
                ('width', models.PositiveIntegerField(blank=True, null=True)),
                ('height', models.PositiveIntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('phone', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='used_phones.usedphone')),
            ],
            options={
                'verbose_name': 'Used Phone Image',
                'verbose_name_plural': 'Used Phone Images',
                'db_table': 'used_phone_images',
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='UsedPhoneFavorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('phone', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorites', to='used_phones.usedphone')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='used_favorites', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Used Phone Favorite',
                'verbose_name_plural': 'Used Phone Favorites',
                'db_table': 'used_phone_favorites',
            },
        ),
        migrations.AddConstraint(
            model_name='usedphonefavorite',
            constraint=models.UniqueConstraint(fields=('user', 'phone'), name='unique_user_phone_favorite'),
        ),
        migrations.AddIndex(
            model_name='usedphone',
            index=models.Index(fields=['status', '-created_at'], name='used_phones_status_created_idx'),
        ),
        migrations.AddIndex(
            model_name='usedphone',
            index=models.Index(fields=['brand', 'status'], name='used_phones_brand_status_idx'),
        ),
        migrations.AddIndex(
            model_name='usedphone',
            index=models.Index(fields=['price'], name='used_phones_price_idx'),
        ),
        migrations.AddIndex(
            model_name='usedphone',
            index=models.Index(fields=['region', 'status'], name='used_phones_region_status_idx'),
        ),
    ]