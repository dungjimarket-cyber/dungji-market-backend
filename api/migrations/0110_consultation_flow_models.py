# Generated manually for consultation flow feature

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0109_populate_consultation_types'),
    ]

    operations = [
        # ConsultationFlow 모델 생성
        migrations.CreateModel(
            name='ConsultationFlow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('step_number', models.PositiveIntegerField(help_text='1부터 시작', verbose_name='단계 번호')),
                ('question', models.CharField(help_text='예: 상담 목적, 사업 형태', max_length=100, verbose_name='질문')),
                ('is_required', models.BooleanField(default=True, verbose_name='필수 여부')),
                ('depends_on_step', models.PositiveIntegerField(blank=True, help_text='특정 단계의 선택에 따라 표시', null=True, verbose_name='의존 단계')),
                ('depends_on_options', models.JSONField(blank=True, default=list, help_text='해당 선택지가 선택되었을 때만 표시 (option key 목록)', verbose_name='의존 선택지')),
                ('order_index', models.IntegerField(default=0, verbose_name='정렬 순서')),
                ('is_active', models.BooleanField(default=True, verbose_name='활성화')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='consultation_flows', to='api.localbusinesscategory', verbose_name='업종')),
            ],
            options={
                'verbose_name': '상담 질문 플로우',
                'verbose_name_plural': '상담 질문 플로우',
                'db_table': 'api_consultation_flow',
                'ordering': ['category', 'step_number', 'order_index'],
                'unique_together': {('category', 'step_number')},
            },
        ),
        # ConsultationFlowOption 모델 생성
        migrations.CreateModel(
            name='ConsultationFlowOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(help_text='프로그래밍용 키 (영문)', max_length=50, verbose_name='선택지 키')),
                ('label', models.CharField(help_text='사용자에게 표시될 텍스트', max_length=50, verbose_name='선택지 라벨')),
                ('icon', models.CharField(blank=True, default='', max_length=10, verbose_name='아이콘')),
                ('description', models.CharField(blank=True, default='', help_text='선택지에 대한 추가 설명', max_length=100, verbose_name='설명')),
                ('is_custom_input', models.BooleanField(default=False, help_text='True면 텍스트 입력창 표시', verbose_name='직접 입력 옵션')),
                ('order_index', models.IntegerField(default=0, verbose_name='정렬 순서')),
                ('is_active', models.BooleanField(default=True, verbose_name='활성화')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('flow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='options', to='api.consultationflow', verbose_name='질문 플로우')),
            ],
            options={
                'verbose_name': '상담 선택지',
                'verbose_name_plural': '상담 선택지',
                'db_table': 'api_consultation_flow_option',
                'ordering': ['flow', 'order_index'],
            },
        ),
    ]
