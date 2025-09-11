# Generated migration file

from django.db import migrations


def update_offer_counts(apps, schema_editor):
    """기존 offer_count를 유니크한 구매자 수로 업데이트"""
    UsedPhone = apps.get_model('used_phones', 'UsedPhone')
    UsedPhoneOffer = apps.get_model('used_phones', 'UsedPhoneOffer')
    
    for phone in UsedPhone.objects.all():
        # 각 상품별로 유니크한 구매자 수 계산
        unique_buyers_count = UsedPhoneOffer.objects.filter(
            phone=phone,
            status='pending'
        ).values('buyer').distinct().count()
        
        # offer_count 업데이트
        phone.offer_count = unique_buyers_count
        phone.save(update_fields=['offer_count'])


def reverse_update_offer_counts(apps, schema_editor):
    """역 마이그레이션 - 전체 제안 수로 되돌리기"""
    UsedPhone = apps.get_model('used_phones', 'UsedPhone')
    UsedPhoneOffer = apps.get_model('used_phones', 'UsedPhoneOffer')
    
    for phone in UsedPhone.objects.all():
        # 전체 pending 제안 수로 되돌리기
        total_offers = UsedPhoneOffer.objects.filter(
            phone=phone,
            status='pending'
        ).count()
        
        phone.offer_count = total_offers
        phone.save(update_fields=['offer_count'])


class Migration(migrations.Migration):

    dependencies = [
        ('used_phones', '0007_add_modified_and_penalty'),
    ]

    operations = [
        migrations.RunPython(update_offer_counts, reverse_update_offer_counts),
    ]