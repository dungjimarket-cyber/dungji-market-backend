# Generated manually - 휴대폰 통신사 로고 업데이트

from django.db import migrations


def update_carrier_logos(apps, schema_editor):
    """휴대폰 대리점 통신사 옵션에 로고 추가"""
    ConsultationFlowOption = apps.get_model('api', 'ConsultationFlowOption')
    ConsultationFlow = apps.get_model('api', 'ConsultationFlow')
    LocalBusinessCategory = apps.get_model('api', 'LocalBusinessCategory')

    try:
        category = LocalBusinessCategory.objects.get(name='휴대폰 대리점')
    except LocalBusinessCategory.DoesNotExist:
        print('휴대폰 대리점 카테고리 없음')
        return

    # 통신사 선택 질문 (step 2) 찾기
    try:
        flow = ConsultationFlow.objects.get(category=category, step_number=2)
    except ConsultationFlow.DoesNotExist:
        print('통신사 선택 플로우 없음')
        return

    # 통신사별 로고 매핑
    carrier_logos = {
        'skt': '/logos/skt.png',
        'kt': '/logos/kt.png',
        'lgu': '/logos/lgu.png',
    }

    for key, logo_path in carrier_logos.items():
        updated = ConsultationFlowOption.objects.filter(
            flow=flow,
            key=key
        ).update(logo=logo_path, icon='')  # 로고 추가, 이모지 제거

        if updated:
            print(f'{key} 로고 업데이트 완료')

    print('통신사 로고 업데이트 완료')


def reverse_update(apps, schema_editor):
    """롤백 - 이모지 복원"""
    ConsultationFlowOption = apps.get_model('api', 'ConsultationFlowOption')
    ConsultationFlow = apps.get_model('api', 'ConsultationFlow')
    LocalBusinessCategory = apps.get_model('api', 'LocalBusinessCategory')

    try:
        category = LocalBusinessCategory.objects.get(name='휴대폰 대리점')
        flow = ConsultationFlow.objects.get(category=category, step_number=2)
    except (LocalBusinessCategory.DoesNotExist, ConsultationFlow.DoesNotExist):
        return

    carrier_icons = {
        'skt': '🔴',
        'kt': '🟠',
        'lgu': '🟣',
    }

    for key, icon in carrier_icons.items():
        ConsultationFlowOption.objects.filter(
            flow=flow,
            key=key
        ).update(logo='', icon=icon)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0116_add_consultation_type_text'),
    ]

    operations = [
        migrations.RunPython(update_carrier_logos, reverse_update),
    ]
