# Generated manually for condition grade choices update

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('used_electronics', '0011_add_bump_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usedelectronics',
            name='condition_grade',
            field=models.CharField(
                choices=[
                    ('unopened', '미개봉'),
                    ('S', 'S급'),
                    ('A', 'A급'),
                    ('B', 'B급'),
                    ('C', 'C급')
                ],
                max_length=10,
                verbose_name='상태등급'
            ),
        ),
    ]
