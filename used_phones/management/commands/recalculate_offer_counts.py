from django.core.management.base import BaseCommand
from used_phones.models import UsedPhone, UsedPhoneOffer


class Command(BaseCommand):
    help = 'Recalculate offer_count for all phones (pending status only)'

    def handle(self, *args, **options):
        updated_count = 0

        for phone in UsedPhone.objects.all():
            # pending 상태의 유니크한 구매자 수 계산
            correct_count = UsedPhoneOffer.objects.filter(
                phone=phone,
                status='pending'
            ).values('buyer').distinct().count()

            # 현재 값과 다르면 업데이트
            if phone.offer_count != correct_count:
                old_count = phone.offer_count
                phone.offer_count = correct_count
                phone.save(update_fields=['offer_count'])
                updated_count += 1

                self.stdout.write(
                    f'Phone {phone.id} ({phone.brand} {phone.model}): '
                    f'{old_count} → {correct_count}'
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully updated {updated_count} phones'
            )
        )