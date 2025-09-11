from rest_framework import permissions

class IsAdminRole(permissions.BasePermission):
    """
    사용자의 role 필드가 'admin'인 경우에만 접근을 허용하는 권한 클래스
    Django의 기본 IsAdminUser는 is_staff 필드를 확인하지만,
    이 클래스는 JWT 토큰에 포함된 role 필드와 User 모델의 role 필드를 확인합니다.
    """
    
    def has_permission(self, request, view):
        # 인증되지 않은 사용자는 접근 불가
        if not request.user or not request.user.is_authenticated:
            return False
            
        # 슈퍼유저는 항상 접근 가능
        if request.user.is_superuser:
            return True
            
        # role 필드가 'admin'인 경우 접근 허용
        return getattr(request.user, 'role', '') == 'admin'


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    객체의 소유자만 수정/삭제할 수 있고, 다른 사용자는 읽기만 가능
    """
    
    def has_object_permission(self, request, view, obj):
        # 읽기 권한은 모든 사용자에게 허용
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 쓰기 권한은 소유자에게만 허용
        # 객체에 따라 owner, seller, buyer, user 등 다양한 필드명 체크
        owner_fields = ['owner', 'seller', 'buyer', 'user', 'creator']
        for field in owner_fields:
            if hasattr(obj, field):
                return getattr(obj, field) == request.user
        
        return False


class IsSeller(permissions.BasePermission):
    """
    판매자 권한 확인
    """
    
    def has_permission(self, request, view):
        # 인증되지 않은 사용자는 접근 불가
        if not request.user or not request.user.is_authenticated:
            return False
        
        # role이 seller인 경우만 접근 허용
        return getattr(request.user, 'role', '') == 'seller'


class IsBuyer(permissions.BasePermission):
    """
    구매자 권한 확인
    """
    
    def has_permission(self, request, view):
        # 인증되지 않은 사용자는 접근 불가
        if not request.user or not request.user.is_authenticated:
            return False
        
        # role이 buyer인 경우만 접근 허용
        return getattr(request.user, 'role', '') == 'buyer'
