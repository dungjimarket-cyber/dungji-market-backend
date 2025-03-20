from django.contrib import admin
from .models import Category, Product, GroupBuy, Bid, Penalty, User, Badge

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent']

@admin.register(Penalty)
class PenaltyAdmin(admin.ModelAdmin):
    list_display = ['user', 'reason', 'start_date']

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'role']

@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ['user', 'level', 'icon']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'base_price', 'is_available')
    search_fields = ('name', 'category__name')
    list_filter = ('category', 'product_type')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(GroupBuy)
class GroupBuyAdmin(admin.ModelAdmin):
    list_display = ('product', 'creator', 'status', 'current_participants', 'end_time')
    raw_id_fields = ('participants',)
    readonly_fields = ('current_participants',)
    actions = ['force_complete_groupbuy']

@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ('seller', 'groupbuy', 'bid_type', 'display_amount', 'is_selected')
    list_editable = ('is_selected',)

    def display_amount(self, obj):
        return f"{obj.amount // 10000}****"  # 부분 마스킹 처리