from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from .models_inquiry import Inquiry
from .serializers_inquiry import InquirySerializer, InquiryDetailSerializer


class InquiryViewSet(viewsets.ModelViewSet):
    """문의사항 ViewSet"""
    serializer_class = InquirySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """사용자 자신의 문의사항만 조회"""
        if self.request.user.is_staff:
            # 관리자는 모든 문의사항 조회 가능
            return Inquiry.objects.all()
        else:
            # 일반 사용자는 자신의 문의사항만 조회
            return Inquiry.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """권한에 따라 시리얼라이저 선택"""
        if self.request.user.is_staff:
            return InquiryDetailSerializer
        return InquirySerializer
    
    def create(self, request, *args, **kwargs):
        """문의사항 생성"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # 사용자 정보 자동 설정
        inquiry = serializer.save(user=request.user)
        
        return Response(
            InquirySerializer(inquiry).data,
            status=status.HTTP_201_CREATED
        )
    
    def list(self, request, *args, **kwargs):
        """문의사항 목록 조회"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """문의사항 상세 조회"""
        instance = self.get_object()
        
        # 작성자 본인이거나 관리자만 조회 가능
        if not (instance.user == request.user or request.user.is_staff):
            return Response(
                {'detail': '권한이 없습니다.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """문의사항 수정 (관리자만 가능 - 답변 작성용)"""
        if not request.user.is_staff:
            return Response(
                {'detail': '권한이 없습니다.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        instance = self.get_object()
        
        # 답변이 추가되면 상태를 답변완료로 변경
        if 'answer' in request.data and request.data['answer']:
            request.data['status'] = 'answered'
            request.data['answered_at'] = timezone.now()
        
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """문의사항 삭제 (작성자 본인만 가능, 답변 전에만)"""
        instance = self.get_object()
        
        # 작성자 본인만 삭제 가능
        if instance.user != request.user:
            return Response(
                {'detail': '권한이 없습니다.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 답변이 완료된 문의는 삭제 불가
        if instance.status == 'answered':
            return Response(
                {'detail': '답변이 완료된 문의는 삭제할 수 없습니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def admin_list(self, request):
        """관리자용 전체 문의사항 목록"""
        queryset = Inquiry.objects.all()
        
        # 상태별 필터링
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # 검색 기능
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                title__icontains=search
            ) | queryset.filter(
                content__icontains=search
            ) | queryset.filter(
                user__username__icontains=search
            )
        
        serializer = InquiryDetailSerializer(queryset, many=True)
        return Response(serializer.data)