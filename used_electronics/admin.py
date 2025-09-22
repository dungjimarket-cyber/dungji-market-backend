from django.contrib import admin
from .models import (
    UsedElectronics, ElectronicsRegion, ElectronicsImage,
    ElectronicsOffer, ElectronicsFavorite, ElectronicsTransaction
)

# ElectronicsRegion과 ElectronicsImage는 Inline으로만 사용 (독립 메뉴 X)


class ElectronicsRegionInline(admin.TabularInline):
    model = ElectronicsRegion
    extra = 1
    max_num = 3


class ElectronicsImageInline(admin.TabularInline):
    model = ElectronicsImage
    extra = 1
    max_num = 10


@admin.register(UsedElectronics)
class UsedElectronicsAdmin(admin.ModelAdmin):
    list_display = ['id', 'subcategory', 'brand', 'model_name', 'price', 'status', 'seller', 'created_at']
    list_filter = ['status', 'subcategory', 'condition_grade', 'purchase_period']
    search_fields = ['brand', 'model_name', 'description']
    inlines = [ElectronicsRegionInline, ElectronicsImageInline]
    readonly_fields = ['view_count', 'offer_count', 'favorite_count', 'created_at', 'updated_at']


@admin.register(ElectronicsOffer)
class ElectronicsOfferAdmin(admin.ModelAdmin):
    list_display = ['id', 'electronics', 'buyer', 'offer_price', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['electronics__model_name', 'buyer__username']


@admin.register(ElectronicsFavorite)
class ElectronicsFavoriteAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'electronics', 'created_at']
    search_fields = ['user__username', 'electronics__model_name']


@admin.register(ElectronicsTransaction)
class ElectronicsTransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'electronics', 'seller', 'buyer', 'final_price', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['electronics__model_name', 'seller__username', 'buyer__username']