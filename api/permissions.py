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
