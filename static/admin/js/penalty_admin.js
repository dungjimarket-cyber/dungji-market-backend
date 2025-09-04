document.addEventListener('DOMContentLoaded', function() {
    // 패널티 기간 설정 fieldset 찾기
    const durationField = document.querySelector('#id_duration_hours');
    const penaltyTypeField = document.querySelector('#id_penalty_type');
    
    if (durationField) {
        // 프리셋 버튼 컨테이너 생성
        const presetContainer = document.createElement('div');
        presetContainer.style.marginTop = '10px';
        presetContainer.style.marginBottom = '10px';
        presetContainer.innerHTML = `
            <label style="display: block; font-weight: bold; margin-bottom: 8px;">⚡ 빠른 설정:</label>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                <button type="button" class="preset-btn" data-hours="24" data-type="노쇼" style="padding: 6px 12px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    노쇼 1일 (24시간)
                </button>
                <button type="button" class="preset-btn" data-hours="48" data-type="노쇼" style="padding: 6px 12px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    노쇼 2일 (48시간)
                </button>
                <button type="button" class="preset-btn" data-hours="72" data-type="노쇼" style="padding: 6px 12px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    노쇼 3일 (72시간)
                </button>
                <button type="button" class="preset-btn" data-hours="168" data-type="노쇼" style="padding: 6px 12px; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    노쇼 1주 (168시간)
                </button>
                <button type="button" class="preset-btn" data-hours="48" data-type="판매포기" style="padding: 6px 12px; background: #fd7e14; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    판매포기 2일 (48시간)
                </button>
                <button type="button" class="preset-btn" data-hours="72" data-type="판매포기" style="padding: 6px 12px; background: #fd7e14; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    판매포기 3일 (72시간)
                </button>
            </div>
        `;
        
        // duration_hours 필드 앞에 프리셋 버튼 추가
        durationField.parentElement.insertBefore(presetContainer, durationField);
        
        // 프리셋 버튼 클릭 이벤트
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                
                // 중복 클릭 방지
                if (this.disabled) return;
                
                const hours = this.dataset.hours;
                const type = this.dataset.type;
                
                // 패널티 기간 설정
                durationField.value = hours;
                
                // 패널티 유형 설정
                if (penaltyTypeField) {
                    penaltyTypeField.value = type;
                }
                
                // 시작일을 현재 시간으로 설정
                const startDateField = document.querySelector('#id_start_date');
                if (startDateField) {
                    const now = new Date();
                    const localDateTime = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
                        .toISOString()
                        .slice(0, 16);
                    startDateField.value = localDateTime;
                }
                
                // 종료일 필드 초기화 (자동 계산되도록)
                const endDateField = document.querySelector('#id_end_date');
                if (endDateField) {
                    endDateField.value = '';
                }
                
                // 선택된 버튼 강조
                document.querySelectorAll('.preset-btn').forEach(b => {
                    b.style.opacity = '0.7';
                });
                this.style.opacity = '1';
                
                // 알림 표시
                const alertDiv = document.createElement('div');
                alertDiv.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #28a745; color: white; padding: 12px 20px; border-radius: 4px; z-index: 9999;';
                alertDiv.textContent = `✅ ${type} ${hours}시간 패널티가 설정되었습니다.`;
                document.body.appendChild(alertDiv);
                
                setTimeout(() => {
                    alertDiv.remove();
                }, 3000);
            });
        });
        
        // 호버 효과
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('mouseenter', function() {
                this.style.transform = 'scale(1.05)';
                this.style.transition = 'transform 0.2s';
            });
            btn.addEventListener('mouseleave', function() {
                this.style.transform = 'scale(1)';
            });
        });
    }
    
    // 사용자 필드 자동완성 개선
    const userField = document.querySelector('#id_user');
    if (userField) {
        // 사용자 검색 도움말 추가
        const helpText = document.createElement('div');
        helpText.style.cssText = 'margin-top: 8px; padding: 8px; background: #e7f3ff; border-left: 3px solid #0066cc; font-size: 13px;';
        helpText.innerHTML = `
            <strong>💡 사용자 검색 팁:</strong><br>
            • 닉네임(username) 입력: 예) user123<br>
            • 이메일 입력: 예) user@example.com<br>
            • 실명 입력: 예) 홍길동<br>
            • 입력 후 드롭다운에서 선택하세요.
        `;
        userField.parentElement.appendChild(helpText);
    }
});