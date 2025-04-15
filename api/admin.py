from django.contrib import admin
from django.contrib.admin import AdminSite
from .models import Category, Product, GroupBuy, Bid, Penalty, User, Badge

# Admin 사이트 타이틀 한글화
AdminSite.site_header = '둥지마켓 관리자'
AdminSite.site_title = '둥지마켓 관리자 포털'
AdminSite.index_title = '둥지마켓 관리자 대시보드'

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent']
    
    # 한글화
    def __init__(self, model, admin_site):
        self.list_display_links = ('name',)
        super().__init__(model, admin_site)
    
    def get_model_perms(self, request):
        perms = super().get_model_perms(request)
        for action in perms:
            perms[action] = perms[action]
        return perms

@admin.register(Penalty)
class PenaltyAdmin(admin.ModelAdmin):
    list_display = ['user', 'reason', 'start_date']
    
    # 한글화
    def __init__(self, model, admin_site):
        self.list_display_links = ('user',)
        super().__init__(model, admin_site)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'role']
    
    # 한글화
    def __init__(self, model, admin_site):
        self.list_display_links = ('username',)
        super().__init__(model, admin_site)

@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ['user', 'level', 'icon']
    
    # 한글화
    def __init__(self, model, admin_site):
        self.list_display_links = ('user',)
        super().__init__(model, admin_site)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'base_price', 'is_available')
    search_fields = ('name', 'category__name')
    list_filter = ('category', 'product_type')
    prepopulated_fields = {'slug': ('name',)}
    
    # 한글화
    def __init__(self, model, admin_site):
        self.list_display_links = ('name',)
        super().__init__(model, admin_site)

@admin.register(GroupBuy)
class GroupBuyAdmin(admin.ModelAdmin):
    list_display = ('product', 'creator', 'status', 'current_participants', 'end_time')
    raw_id_fields = ('participants',)
    readonly_fields = ('current_participants',)
    actions = ['force_complete_groupbuy']
    
    # 한글화
    def __init__(self, model, admin_site):
        self.list_display_links = ('product',)
        super().__init__(model, admin_site)
        
    def force_complete_groupbuy(self, request, queryset):
        for groupbuy in queryset:
            groupbuy.status = 'completed'
            groupbuy.save()
    force_complete_groupbuy.short_description = '선택한 공구를 강제 완료 처리'

@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ('seller', 'groupbuy', 'bid_type', 'display_amount', 'is_selected')
    list_editable = ('is_selected',)
    
    # 한글화
    def __init__(self, model, admin_site):
        self.list_display_links = ('seller',)
        super().__init__(model, admin_site)

    def display_amount(self, obj):
        return f"{obj.amount // 10000}****"  # 부분 마스킹 처리
    display_amount.short_description = '입찰 금액'