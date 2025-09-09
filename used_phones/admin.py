from django.contrib import admin
from .models import UsedPhone, UsedPhoneImage, UsedPhoneFavorite, UsedPhoneOffer


class UsedPhoneImageInline(admin.TabularInline):
    model = UsedPhoneImage
    extra = 0


@admin.register(UsedPhone)
class UsedPhoneAdmin(admin.ModelAdmin):
    list_display = ['id', 'model', 'brand', 'price', 'seller', 'status', 'created_at']
    list_filter = ['status', 'brand', 'condition_grade', 'accept_offers']
    search_fields = ['model', 'seller__username', 'description']
    inlines = [UsedPhoneImageInline]
    readonly_fields = ['view_count', 'favorite_count', 'offer_count', 'created_at', 'updated_at']


@admin.register(UsedPhoneOffer)
class UsedPhoneOfferAdmin(admin.ModelAdmin):
    list_display = ['id', 'phone', 'buyer', 'amount', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['phone__model', 'buyer__username']


@admin.register(UsedPhoneFavorite)
class UsedPhoneFavoriteAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'phone', 'created_at']
    search_fields = ['user__username', 'phone__model']