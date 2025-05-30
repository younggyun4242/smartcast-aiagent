#!/bin/bash
# AI Agent 통합 모니터링 스크립트 - CentOS Stream 9 최적화
# 서버 스펙: 32코어, 62GB RAM

# 사용법 출력 함수
show_usage() {
    echo "사용법: $0 [옵션]"
    echo "옵션:"
    echo "  -s, --system     시스템 전체 모니터링 (로그 저장, 60초 간격)"
    echo "  -d, --docker     Docker 전용 모니터링 (실시간 화면, 10초 간격)"
    echo "  -a, --all        통합 모니터링 (모든 정보, 30초 간격)"
    echo "  -h, --help       도움말 표시"
    echo ""
    echo "예시:"
    echo "  $0 --system      # 시스템 모니터링"
    echo "  $0 --docker      # Docker 모니터링"
    echo "  $0 --all         # 통합 모니터링"
    exit 1
}

# 기본 설정
MODE="all"
LOG_FILE="/var/log/aiagent_monitor.log"
REFRESH_INTERVAL=30

# 명령행 인수 처리
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--system)
            MODE="system"
            REFRESH_INTERVAL=60
            shift
            ;;
        -d|--docker)
            MODE="docker"
            REFRESH_INTERVAL=10
            shift
            ;;
        -a|--all)
            MODE="all"
            REFRESH_INTERVAL=30
            shift
            ;;
        -h|--help)
            show_usage
            ;;
        *)
            echo "알 수 없는 옵션: $1"
            show_usage
            ;;
    esac
done

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 로그 디렉토리 생성
mkdir -p /var/log

echo -e "${CYAN}🚀 AI Agent 모니터링 시작 (모드: $MODE)${NC}"
echo -e "${YELLOW}Ctrl+C로 종료하세요.${NC}"
echo ""

# 시스템 정보 수집 함수
get_system_info() {
    local log_output=$1
    
    # CPU 사용률
    CPU_USAGE=$(mpstat 1 1 | grep "Average" | awk '{print int(100-$12)}')
    
    # 메모리 사용률
    MEM_USAGE=$(free | grep Mem | awk '{print int($3/$2*100)}')
    
    # 디스크 사용률
    DISK_USAGE=$(df / | tail -1 | awk '{print int($5)}')
    
    if [ "$log_output" = "true" ]; then
        echo -e "${BLUE}=== System Overview ===${NC}" | tee -a "$LOG_FILE"
        echo "CPU: $CPU_USAGE%, 메모리: $MEM_USAGE%, 디스크: $DISK_USAGE%" | tee -a "$LOG_FILE"
        uptime | tee -a "$LOG_FILE"
        echo "" | tee -a "$LOG_FILE"
        
        echo -e "${BLUE}=== Memory Usage (62GB Total) ===${NC}" | tee -a "$LOG_FILE"
        free -h | tee -a "$LOG_FILE"
        echo "" | tee -a "$LOG_FILE"
    else
        echo -e "${BLUE}💻 시스템 상태: ${GREEN}CPU $CPU_USAGE%${NC} | ${BLUE}메모리 $MEM_USAGE%${NC} | ${BLUE}디스크 $DISK_USAGE%${NC}"
        uptime
        echo ""
    fi
}

# Docker 정보 수집 함수
get_docker_info() {
    local log_output=$1
    
    if [ "$log_output" = "true" ]; then
        echo -e "${BLUE}=== Docker Container Status ===${NC}" | tee -a "$LOG_FILE"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | tee -a "$LOG_FILE"
        echo "" | tee -a "$LOG_FILE"
        
        echo -e "${BLUE}=== Docker Container Resources ===${NC}" | tee -a "$LOG_FILE"
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}" | tee -a "$LOG_FILE"
        echo "" | tee -a "$LOG_FILE"
    else
        echo -e "${BLUE}🐳 Docker 컨테이너:${NC}"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        echo ""
        
        echo -e "${BLUE}📊 리소스 사용량:${NC}"
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
        echo ""
    fi
}

# 경고 체크 함수
check_alerts() {
    local cpu=$1
    local mem=$2
    local disk=$3
    
    if [ "$cpu" -gt 80 ] || [ "$mem" -gt 85 ] || [ "$disk" -gt 90 ]; then
        echo -e "${RED}⚠️  시스템 경고:${NC}"
        [ "$cpu" -gt 80 ] && echo -e "${RED}   - CPU 사용률 높음: $cpu%${NC}"
        [ "$mem" -gt 85 ] && echo -e "${RED}   - 메모리 사용률 높음: $mem%${NC}"
        [ "$disk" -gt 90 ] && echo -e "${RED}   - 디스크 사용률 높음: $disk%${NC}"
        echo ""
    fi
}

# 메인 모니터링 루프
while true; do
    TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
    
    case $MODE in
        "system")
            echo "==================== $TIMESTAMP ====================" | tee -a "$LOG_FILE"
            get_system_info true
            
            # 네트워크 연결
            echo -e "${BLUE}=== Network Connections ===${NC}" | tee -a "$LOG_FILE"
            ss -tulpn | grep -E "(8000|5555|25555)" | tee -a "$LOG_FILE"
            echo "" | tee -a "$LOG_FILE"
            
            # 프로세스 상위 5개
            echo -e "${BLUE}=== Top Processes ===${NC}" | tee -a "$LOG_FILE"
            ps aux --sort=-%cpu | head -6 | tee -a "$LOG_FILE"
            echo "" | tee -a "$LOG_FILE"
            ;;
            
        "docker")
            clear
            echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
            echo -e "${CYAN}║              🐳 DOCKER 모니터링 - $TIMESTAMP              ║${NC}"
            echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
            echo ""
            
            get_docker_info false
            
            # 컨테이너 로그
            echo -e "${BLUE}📝 최근 로그:${NC}"
            CONTAINER_NAME="smartcast-aiagent-ai-agent-1"
            if docker ps | grep -q "$CONTAINER_NAME"; then
                docker logs --tail=5 "$CONTAINER_NAME" 2>/dev/null | tail -5
            fi
            echo ""
            
            echo -e "${CYAN}빠른 명령어:${NC}"
            echo "로그 보기: docker logs -f $CONTAINER_NAME"
            echo "재시작: docker restart $CONTAINER_NAME"
            ;;
            
        "all")
            if [ $(($(date +%s) % 2)) -eq 0 ]; then
                clear
            fi
            
            echo -e "${CYAN}╔════════════════════════════════════════════════════════════════════════╗${NC}"
            echo -e "${CYAN}║                   🚀 AI AGENT 통합 모니터링                              ║${NC}"
            echo -e "${CYAN}║                        $TIMESTAMP                         ║${NC}"
            echo -e "${CYAN}╚════════════════════════════════════════════════════════════════════════╝${NC}"
            echo ""
            
            get_system_info false
            get_docker_info false
            
            # 경고 체크
            CPU_USAGE=$(mpstat 1 1 | grep "Average" | awk '{print int(100-$12)}')
            MEM_USAGE=$(free | grep Mem | awk '{print int($3/$2*100)}')
            DISK_USAGE=$(df / | tail -1 | awk '{print int($5)}')
            check_alerts $CPU_USAGE $MEM_USAGE $DISK_USAGE
            
            echo -e "${BLUE}🌐 네트워크:${NC}"
            ss -tulpn | grep -E "(8000|5555|25555)" | head -3
            echo ""
            ;;
    esac
    
    echo -e "${YELLOW}새로고침: ${REFRESH_INTERVAL}초 후... | 종료: Ctrl+C${NC}"
    
    if [ "$MODE" != "docker" ]; then
        echo "============================================================" | tee -a "$LOG_FILE"
        echo "" | tee -a "$LOG_FILE"
    fi
    
    sleep $REFRESH_INTERVAL
done 