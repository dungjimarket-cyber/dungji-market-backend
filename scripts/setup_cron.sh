#!/bin/bash

# 둥지마켓 백엔드 크론 작업 설정 스크립트

# 백엔드 디렉토리 경로
BACKEND_DIR="/Users/crom/workspace_joshua/dungji-market/backend"
PYTHON_PATH="/usr/bin/python3"  # Python 경로 (필요시 수정)

# 크론탭 임시 파일 생성
TEMP_CRON=$(mktemp)

# 현재 크론탭 내용 가져오기 (있다면)
crontab -l 2>/dev/null > "$TEMP_CRON" || true

# 기존에 update_groupbuy_status가 있다면 제거
grep -v "update_groupbuy_status" "$TEMP_CRON" > "${TEMP_CRON}.new" && mv "${TEMP_CRON}.new" "$TEMP_CRON"

# 새로운 크론 작업 추가
# 매 10분마다 공구 상태 업데이트 실행
echo "*/10 * * * * cd $BACKEND_DIR && $PYTHON_PATH manage.py update_groupbuy_status >> $BACKEND_DIR/logs/cron_groupbuy_status.log 2>&1" >> "$TEMP_CRON"

# 로그 디렉토리 생성
mkdir -p "$BACKEND_DIR/logs"

# 크론탭 설치
crontab "$TEMP_CRON"

# 임시 파일 삭제
rm "$TEMP_CRON"

echo "크론탭이 성공적으로 설정되었습니다."
echo "다음 명령어로 확인할 수 있습니다: crontab -l"
echo ""
echo "설정된 작업:"
echo "- 매 10분마다 공구 상태 자동 업데이트"
echo "- 로그 파일: $BACKEND_DIR/logs/cron_groupbuy_status.log"