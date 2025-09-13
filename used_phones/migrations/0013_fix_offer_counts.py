# Generated manually
from django.db import migrations


def fix_offer_counts(apps, schema_editor):
    """기존 offer_count를 재계산하여 cancelled 제안 제외"""
    UsedPhone = apps.get_model('used_phones', 'UsedPhone')
    UsedPhoneOffer = apps.get_model('used_phones', 'UsedPhoneOffer')

    updated_count = 0

    for phone in UsedPhone.objects.all():
        # pending 상태의 유니크한 구매자 수만 계산
        correct_count = UsedPhoneOffer.objects.filter(
            phone=phone,
            status='pending'
        ).values('buyer').distinct().count()

        # 현재 값과 다르면 업데이트
        if phone.offer_count != correct_count:
            print(f'Updating Phone {phone.id}: {phone.offer_count} -> {correct_count}')
            phone.offer_count = correct_count
            phone.save(update_fields=['offer_count'])
            updated_count += 1

    print(f'Updated {updated_count} phones')


def reverse_fix_offer_counts(apps, schema_editor):
    """역방향 마이그레이션 - 모든 제안 카운트로 되돌리기"""
    UsedPhone = apps.get_model('used_phones', 'UsedPhone')
    UsedPhoneOffer = apps.get_model('used_phones', 'UsedPhoneOffer')

    for phone in UsedPhone.objects.all():
        # 모든 상태의 유니크한 구매자 수 계산
        total_count = UsedPhoneOffer.objects.filter(
            phone=phone
        ).values('buyer').distinct().count()

        if phone.offer_count != total_count:
            phone.offer_count = total_count
            phone.save(update_fields=['offer_count'])


class Migration(migrations.Migration):

    dependencies = [
        ('used_phones', '0012_update_battery_status_add_defective'),
    ]

    operations = [
        migrations.RunPython(fix_offer_counts, reverse_fix_offer_counts),
    ]