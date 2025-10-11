"""
Django Admin 메뉴 카테고리 설정

메뉴를 3개 영역으로 분류:
1. 공구견적 (Group Purchase)
2. 커스텀공구 (Custom Deal)
3. 중고거래 (Used Market)
"""

from django.contrib import admin


class CategoryAdminSite(admin.AdminSite):
    """카테고리별로 정리된 Admin Site"""

    site_header = '둥지마켓 관리자'
    site_title = '둥지마켓 Admin'
    index_title = '관리 대시보드'

    def get_app_list(self, request, app_label=None):
        """앱 리스트를 카테고리별로 재구성"""
        app_list = super().get_app_list(request, app_label)

        # 카테고리별로 모델 분류
        categories = {
            '1. 공구견적': [],
            '2. 커스텀공구': [],
            '3. 중고거래': [],
            '4. 시스템 관리': [],
        }

        # 키워드 기반 분류
        groupbuy_keywords = ['groupbuy', 'bid', 'participation', 'consent', 'settlement', 'product', 'category']
        custom_keywords = ['custom', 'customgroupbuy', 'customparticipant', 'customfavorite', 'custompenalty', 'customnoshow']
        used_keywords = ['usedphone', 'usedelectronics', 'electronics', 'offer', 'transaction', 'cancellation']

        for app in app_list:
            app_label_lower = app['app_label'].lower()

            for model in app['models']:
                model_name_lower = model['object_name'].lower()
                url_name = model.get('admin_url', '')

                # 분류 로직
                if any(keyword in model_name_lower or keyword in url_name for keyword in custom_keywords):
                    categories['2. 커스텀공구'].append(model)
                elif any(keyword in model_name_lower or keyword in url_name for keyword in used_keywords):
                    categories['3. 중고거래'].append(model)
                elif any(keyword in model_name_lower or keyword in url_name for keyword in groupbuy_keywords):
                    categories['1. 공구견적'].append(model)
                else:
                    categories['4. 시스템 관리'].append(model)

        # 카테고리별로 앱 리스트 재구성
        new_app_list = []
        for category_name, models in categories.items():
            if models:  # 모델이 있는 카테고리만 표시
                new_app_list.append({
                    'name': category_name,
                    'app_label': category_name.lower().replace('. ', '_').replace(' ', '_'),
                    'models': sorted(models, key=lambda x: x['name']),
                    'has_module_perms': True,
                })

        return new_app_list


# 기본 admin site를 커스텀 site로 교체
admin_site = CategoryAdminSite(name='admin')
