# 🚀 SmartCast AI Agent 서버 배포 가이드

## 📋 개요

이 문서는 SmartCast AI Agent를 실제 서버에 배포하는 방법을 설명합니다.

## 🛠️ 사전 준비

### 1. 개발 환경 (빌드용)
- Docker & Docker Compose
- Git
- 인터넷 연결

### 2. 서버 환경 (운영용)
- **OS**: Ubuntu 20.04+ / CentOS 8+ / Amazon Linux 2
- **CPU**: 최소 16코어 (권장 32코어+)
- **메모리**: 최소 32GB (권장 64GB+)
- **디스크**: 최소 100GB SSD
- **Docker**: 20.10+ 버전
- **Docker Compose**: 2.0+ 버전

### 3. 필수 정보
- **OpenAI API Key**: GPT-4 사용 권한 필요
- **외부 브로커 서버**: ZeroMQ 브로커 주소 및 포트
- **Docker Registry**: Docker Hub 또는 Private Registry 계정

---

## 🔧 1단계: 이미지 빌드 및 푸시

### 1.1 Registry 설정

**Docker Hub 사용 시:**
```bash
# build.sh, push.sh, deploy.sh에서 REGISTRY 변수 수정
REGISTRY="younggyun"
```

**Private Registry 사용 시:**
```bash
# build.sh, push.sh, deploy.sh에서 REGISTRY 변수 수정
REGISTRY="registry.company.com"
```

### 1.2 Docker Hub 로그인 (Docker Hub 사용 시)
```bash
docker login
```

### 1.3 이미지 빌드
```bash
# 버전 지정 빌드
./build.sh v1.0.0

# 또는 latest 태그
./build.sh
```

### 1.4 이미지 푸시
```bash
# 빌드한 버전과 동일하게
./push.sh v1.0.0

# 또는 latest
./push.sh
```

---

## 🚀 2단계: 서버 배포

### 2.1 서버 준비

**Docker 설치 (Ubuntu 기준):**
```bash
# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER
```

### 2.2 배포 디렉토리 생성 (기존 구조와 일치)
```bash
# 배포용 디렉토리 생성 (이미 aiagent 폴더가 있다면 생략)
sudo mkdir -p /opt/aiagent
sudo chown -R $USER:$USER /opt/aiagent
cd /opt/aiagent

# 배포 스크립트 다운로드
curl -O https://raw.githubusercontent.com/younggyun4242/smartcast-aiagent/main/deploy.sh
chmod +x deploy.sh
```

### 2.3 환경변수 설정
```bash
# .env 파일 생성
cat > .env << EOF
# SmartCast AI Agent 환경변수
OPENAI_API_KEY=sk-your-openai-api-key-here
BROKER_HOST=broker.company.com
BROKER_PORT=5555
LOG_LEVEL=INFO

# PostgreSQL 설정
POSTGRES_DB=aiagent
POSTGRES_USER=aiagent
POSTGRES_PASSWORD=your-secure-password-here
POSTGRES_PORT=5432
EOF

# 보안을 위해 권한 제한
chmod 600 .env
```

### 2.4 배포 실행
```bash
# 특정 버전 배포
./deploy.sh v1.0.0

# 또는 최신 버전 배포
./deploy.sh
```

---

## 📊 3단계: 배포 확인

### 3.1 서비스 상태 확인
```bash
# 컨테이너 상태 확인
docker-compose -f docker-compose.prod.yml -p smartcast-aiagent-prod ps

# 예상 출력:
# NAME                               COMMAND               SERVICE    STATUS    PORTS
# smartcast-aiagent-ai-agent-prod    "python main.py"      ai-agent   running   
# smartcast-aiagent-postgres-prod    "docker-entrypoint.s…"postgres   running   0.0.0.0:5432->5432/tcp
```

### 3.2 로그 확인
```bash
# AI Agent 로그 확인
docker-compose -f docker-compose.prod.yml -p smartcast-aiagent-prod logs -f ai-agent

# 모든 서비스 로그 확인
docker-compose -f docker-compose.prod.yml -p smartcast-aiagent-prod logs -f
```

### 3.3 시스템 리소스 확인
```bash
# Docker 리소스 사용량 확인
docker stats

# 시스템 리소스 확인
htop  # 또는 top
```

---

## 🔧 4단계: 운영 관리

### 4.1 자동 시작 설정
```bash
# systemd 서비스 파일 생성
sudo tee /etc/systemd/system/smartcast-aiagent.service > /dev/null << EOF
[Unit]
Description=SmartCast AI Agent
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/aiagent
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml -p smartcast-aiagent-prod up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml -p smartcast-aiagent-prod down
TimeoutStartSec=0
User=root

[Install]
WantedBy=multi-user.target
EOF

# 서비스 활성화
sudo systemctl enable smartcast-aiagent
sudo systemctl start smartcast-aiagent
```

### 4.2 로그 로테이션 설정
```bash
# logrotate 설정
sudo tee /etc/logrotate.d/smartcast-aiagent > /dev/null << EOF
/opt/aiagent/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    sharedscripts
    postrotate
        docker-compose -f /opt/aiagent/docker-compose.prod.yml -p smartcast-aiagent-prod restart ai-agent
    endscript
}
EOF
```

### 4.3 백업 스크립트
```bash
# 백업 스크립트 생성
cat > /opt/aiagent/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups/smartcast-aiagent"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# PostgreSQL 백업
docker exec smartcast-aiagent-postgres-prod pg_dump -U aiagent aiagent > $BACKUP_DIR/db_backup_$DATE.sql

# 로그 백업
tar -czf $BACKUP_DIR/logs_backup_$DATE.tar.gz logs/

# 설정 파일 백업
cp .env $BACKUP_DIR/env_backup_$DATE

# 오래된 백업 정리 (30일 이상)
find $BACKUP_DIR -name "*backup*" -mtime +30 -delete

echo "백업 완료: $BACKUP_DIR"
EOF

chmod +x /opt/aiagent/backup.sh

# 크론탭에 추가 (매일 새벽 2시)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/aiagent/backup.sh") | crontab -
```

---

## 🚦 5단계: 모니터링 및 문제 해결

### 5.1 헬스체크
```bash
# 컨테이너 상태 확인
docker-compose -f docker-compose.prod.yml -p smartcast-aiagent-prod ps

# 포트 확인
sudo netstat -tlnp | grep 5432  # PostgreSQL

# 디스크 사용량 확인
df -h
```

### 5.2 업데이트 방법
```bash
# 새 버전 배포
./deploy.sh v1.1.0

# 롤백 (이전 버전으로)
./deploy.sh v1.0.0
```

### 5.3 문제 해결

**컨테이너가 시작되지 않을 때:**
```bash
# 로그 확인
docker-compose -f docker-compose.prod.yml -p smartcast-aiagent-prod logs ai-agent

# 환경변수 확인
docker-compose -f docker-compose.prod.yml -p smartcast-aiagent-prod config
```

**데이터베이스 연결 오류:**
```bash
# PostgreSQL 상태 확인
docker exec smartcast-aiagent-postgres-prod pg_isready -U aiagent

# 데이터베이스 접속 테스트
docker exec -it smartcast-aiagent-postgres-prod psql -U aiagent -d aiagent
```

**메모리 부족:**
```bash
# 메모리 사용량 확인
free -h
docker stats

# 스왑 추가 (임시 해결)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 📋 체크리스트

### 배포 전 체크리스트
- [ ] Docker 및 Docker Compose 설치 완료
- [ ] OpenAI API Key 준비
- [ ] 외부 브로커 서버 정보 확인
- [ ] Registry 계정 및 권한 확인
- [ ] 서버 리소스 충분성 확인

### 배포 후 체크리스트
- [ ] 모든 컨테이너 정상 실행 확인
- [ ] 로그에 오류 없음 확인
- [ ] 외부 브로커 연결 확인
- [ ] 데이터베이스 연결 확인
- [ ] API 응답 테스트 완료
- [ ] 모니터링 설정 완료
- [ ] 백업 설정 완료

---

## 🆘 지원

문제가 발생하면 다음을 확인해주세요:

1. **로그 파일**: `logs/` 디렉토리
2. **시스템 리소스**: CPU, 메모리, 디스크
3. **네트워크 연결**: 브로커 서버, OpenAI API
4. **환경변수**: `.env` 파일 설정

추가 지원이 필요하면 GitHub Issues를 생성해주세요. 