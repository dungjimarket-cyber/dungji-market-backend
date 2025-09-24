# used_electronics/views.py 수정 사항

# buyer_info 메서드를 다음과 같이 수정해야 합니다:

@action(detail=True, methods=['get'], url_path='buyer-info', permission_classes=[IsAuthenticated])
def buyer_info(self, request, pk=None):
    """구매자 정보 조회 (거래중인 판매자용)"""
    # get_object() 대신 직접 조회 (거래중 상태도 포함)
    try:
        electronics = UsedElectronics.objects.get(pk=pk)
    except UsedElectronics.DoesNotExist:
        return Response(
            {'error': '전자제품을 찾을 수 없습니다.'},
            status=status.HTTP_404_NOT_FOUND
        )

    if electronics.seller != request.user:
        return Response(
            {'error': '판매자만 조회할 수 있습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        transaction = ElectronicsTransaction.objects.get(
            electronics=electronics,
            status='in_progress'
        )
    except ElectronicsTransaction.DoesNotExist:
        return Response(
            {'error': '거래 정보를 찾을 수 없습니다.'},
            status=status.HTTP_404_NOT_FOUND
        )

    buyer_data = {
        'id': transaction.buyer.id,
        'nickname': getattr(transaction.buyer, 'nickname', transaction.buyer.username),
        'phone': getattr(transaction.buyer, 'phone', None),
        'email': transaction.buyer.email,
        'region': getattr(transaction.buyer, 'region_name', None),
        'accepted_price': transaction.final_price
    }

    return Response(buyer_data)

# 또는 get_queryset을 오버라이드하는 방법:
def get_object(self):
    """buyer-info, seller-info 등의 액션에서는 거래중 상태도 조회 가능하도록"""
    if self.action in ['buyer_info', 'seller_info', 'complete_transaction', 'buyer_complete', 'cancel_trade']:
        queryset = UsedElectronics.objects.all()
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)
        self.check_object_permissions(self.request, obj)
        return obj
    return super().get_object()