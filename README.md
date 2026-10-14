# FOTOSTREAM (포토스트림)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**FOTOSTREAM**은 사용자가 업로드한 최대 49장의 사진을 최적의 $N \times M$ 매트릭스 그리드로 자동 배치하고, 각 사진을 순차적으로 줌인(Zoom-in) 및 줌아웃(Zoom-out)하는 다이내믹 슬라이딩 비디오를 합성·관리·스트리밍하는 고성능 웹 플랫폼 & RESTful API 서비스입니다.

---

## 📌 목차
1. [프로젝트 목적](#-프로젝트-목적)
2. [주요 기능 및 기술적 특징](#-주요-기능-및-기술적-특징)
3. [시스템 아키텍처](#-시스템-아키텍처)
4. [환경변수 레퍼런스](#-환경변수-레퍼런스)
5. [로컬 개발 환경 실행 방법](#-로컬-개발-환경-실행-방법)
6. [Docker 컨테이너 배포 가이드](#-docker-컨테이너-배포-가이드)
7. [API 엔드포인트 및 헬스체크](#-api-엔드포인트-및-헬스체크)
8. [테스트 실행 방법](#-테스트-실행-방법)

---

## 🎯 프로젝트 목적
- **자동 비디오 합성**: 사용자가 대량의 사진(최대 49장)을 업로드하면 하나의 유려한 스토리텔링 영상으로 자동 변환합니다.
- **고해상도 원본 디테일 보존**: 썸네일 디지털 확대로 인한 화질 저하를 방지하기 위해 **하이브리드 해상도 전환(Hybrid Resolution Zoom)** 기술을 적용하여 확대 시 원본 고화질을 온전히 유지합니다.
- **풍부한 BGM 라이브러리 연동**: 밝고 경쾌한 5곡의 번들 BGM을 기본 제공하며, [Pixabay Music](https://pixabay.com/music/) 등 외부 무료 음원을 관리자가 손쉽게 서버에 등록하여 합성 영상에 적용할 수 있습니다.
- **동시성 및 자원 제어**: 최대 3개의 동시 비디오 합성 작업 큐와 최대 10개의 동시 비디오 스트리밍 세션을 보장하여 안정적인 서버 운영 환경을 제공합니다.
- **컨테이너 기반 유연한 배포**: `DEFAULT_PREFIX` 환경변수 기반의 URL 프리픽스 라우팅, Persistent Volume을 통한 SQLite DB 및 미디어 파일 보존, 규격화된 컨테이너 헬스체크를 완벽히 지원합니다.

---

## ✨ 주요 기능 및 기술적 특징

### 1. 최적 $N \times M$ 그리드 자동 계산 엔진
- 업로드된 이미지 수(1~49장)에 맞추어 `M = N` 또는 `N = M ± 1` 조건을 만족하는 가장 균형 잡힌 최적 그리드를 자동 계산합니다.
- 여백(Margin)과 셀 간격(Gap)을 해상도 비율에 맞춰 동적으로 산출하여 정돈된 화면을 구성합니다.

### 2. 하이브리드 고해상도 줌인/줌아웃 엔진 (Hybrid Resolution Zoom)
- **전체 조망 (Intro)**: 모든 사진이 정렬된 전체 매트릭스 그리드를 조망합니다.
- **줌인 전환 ($t \in [0.35, 0.70]$)**: 줌 시작 초기에는 매트릭스 화면에서 부드럽게 줌을 시작하고, 줌 중간 지점부터 코사인 이징($\alpha$) 기반으로 **100% 원본 고해상도 이미지 레이어로 매끄럽게 크로스페이드(Blend)** 합니다.
- **확대 감상 (Hold, $t \ge 0.70$)**: 픽셀 깨짐 없이 **100% 최고 해상도 원본 프레임**을 사용자에게 선명하게 디스플레이합니다.
- **줌아웃 복귀**: 다시 자연스러운 역방향 크로스페이드로 전체 매트릭스로 복귀한 후 다음 사진으로 슬라이딩 전환합니다.

### 3. 다중 해상도 지원 (표준 1080p 기본)
| 해상도 옵션 | 규격 (가로x세로) | 비트레이트 제어 | 비고 |
| :--- | :--- | :--- | :--- |
| `720p` | 1280 x 720 | Maxrate 2.5M / Buf 5.0M | 최소 지원 화질 |
| **`1080p`** | **1920 x 1080** | **Maxrate 4.5M / Buf 9.0M** | **표준 기본 화질 (Default)** |
| `1440p` | 2560 x 1440 | Maxrate 8.0M / Buf 16.0M | 2K QHD 고화질 |
| `1920p` | 3414 x 1920 | Maxrate 14.0M / Buf 28.0M | 최대 초고화질 |

- 비디오 제약조건: 최대 파일 크기 100MB 이하, 최대 재생 시간 10분(600초) 이내 자동 제한.

### 4. 밝고 경쾌한 BGM 라이브러리 & 관리자 업로드 UI
- 기본 번들 탑재 BGM 5곡 (메이저 코드 진행, 밝고 경쾌한 멜로디):
  1. `Sunny Morning Walk` (C Major, 120 BPM, 어쿠스틱 스트럼)
  2. `Upbeat Joyful Ukulele` (F Major, 128 BPM, 경쾌한 우쿨렐레)
  3. `Energy Dance Beat` (G Major, 130 BPM, 활기찬 신스 팝)
  4. `Happy Campus Breeze` (D Major, 116 BPM, 따뜻한 포크 사운드)
  5. `Playful Summer Smile` (A Major, 124 BPM, 트로피컬 마림바)
- **외부 BGM 등록 및 항목별 삭제 관리**: 관리자가 Pixabay Music 등에서 다운로드한 오디오 파일(`mp3`, `wav`, `aac` 등)을 대시보드 모달에서 즉시 업로드 및 등록할 수 있으며, 각 BGM 카드 항목에 배치된 **삭제 버튼**을 통해 불필요한 음원을 즉각 삭제하고 디스크 공간을 안전하게 정리할 수 있습니다.
- 비디오 길이에 맞춘 오디오 무한 루프 재생 및 종료 시 2초간 자연스러운 오디오 페이드아웃(Audio Fade-out) 처리.

### 5. 비동기 작업 큐 및 HTTP 206 스트리밍
- **합성 작업 큐**: `asyncio.Semaphore(3)` 기반으로 최대 3개 작업 동시 인코딩, 초과 요청은 대기 큐(`QUEUED`)에서 순차 처리.
- **스트리밍 제어**: 최대 10개 동시 스트리밍 슬롯(`HTTP 206 Partial Content` Range 요청 지원)을 관리하여 네트워크 대역폭 보호.

---

## 🏗️ 시스템 아키텍처

```
fotostream/
├── app/
│   ├── core/                  # 앱 설정, DB 엔진 및 디렉토리 보장
│   │   ├── config.py          # Pydantic 설정 (.env, DB_PATH, DEFAULT_PREFIX 등)
│   │   └── database.py        # SQLite 연결 및 자동 스키마 마이그레이션
│   ├── models/                # SQLAlchemy ORM 모델 (Job, Video, BGMTrack)
│   ├── schemas/               # Pydantic 요청/응답 스키마
│   ├── services/              # 핵심 비즈니스 로직
│   │   ├── grid_calculator.py # 최적 NxM 매트릭스 계산기
│   │   ├── video_synthesizer.py # 하이브리드 고해상도 줌 합성 엔진
│   │   ├── audio_mixer.py     # FFprobe 분석, 루프 및 페이드아웃 오디오 믹서
│   │   ├── bgm_manager.py     # 5종 밝은 BGM 프리셋 및 업로드 관리자
│   │   ├── task_queue.py      # 비동기 인코딩 작업 큐 (N<=3)
│   │   └── stream_manager.py  # HTTP 206 부분 콘텐츠 스트리밍 제어 (M<=10)
│   ├── routers/               # API 라우터 (jobs, videos, bgm, system, ui)
│   ├── static/                # 대시보드 CSS/JS 정적 에셋
│   ├── templates/             # Jinja2 템플릿 (dashboard.html)
│   └── main.py                # FastAPI 애플리케이션 정의
├── storage/                   # 영구 보존 볼륨 (Persistent Volume)
│   ├── fotostream.db          # SQLite 데이터베이스
│   ├── uploads/               # 원본 업로드 사진 저장소
│   ├── transcoded/            # 합성 완료된 MP4 및 썸네일
│   └── bgm/                   # 등록된 BGM 오디오 파일
├── tests/                     # pytest 테스트 스위트 (10개 테스트)
├── main.py                    # Gunicorn/Uvicorn 구동을 위한 루트 엔트리포인트
├── gunicorn.conf.py           # Gunicorn UvicornWorker 설정 파일
├── Dockerfile                 # 프로덕션 도커 컨테이너 빌드 파일
├── docker-compose.yml         # 도커 컴포즈 실행 매니페스트
├── requirements.txt           # 파이썬 의존성 패키지 목록
└── README.md                  # 본 문서
```

---

## ⚙️ 환경변수 레퍼런스

`.env` 파일 또는 Docker 컨테이너 실행 시 다음 환경변수를 설정할 수 있습니다:

| 환경변수 | 기본값 | 설명 |
| :--- | :--- | :--- |
| `PORT` | `5000` | 웹 서버 노출 포트 |
| `HOST` | `0.0.0.0` | 서버 바인딩 호스트 |
| `DEFAULT_PREFIX` | `/fotostream` | 웹앱 Base URL 프리픽스 (예: `/fotostream` 또는 `fotostream`) |
| `DB_PATH` | `/app/storage/fotostream.db` | 영구 보존 SQLite DB 파일 전체 경로 |
| `DB_URL` | `sqlite:///./storage/fotostream.db` | SQLAlchemy 데이터베이스 URL (`DB_PATH` 우선 적용) |
| `STORAGE_DIR` | `/app/storage` | 영구 볼륨 루트 경로 |
| `UPLOAD_DIR` | `/app/storage/uploads` | 업로드 사진 저장소 경로 |
| `BGM_DIR` | `/app/storage/bgm` | BGM 음원 저장소 경로 |
| `TRANSCODE_DIR` | `/app/storage/transcoded` | 합성 비디오 저장소 경로 |
| `MAX_CONCURRENT_JOBS` | `3` | 동시 비디오 합성 최대 작업 수 ($N \le 3$) |
| `MAX_CONCURRENT_STREAMS` | `10` | 동시 비디오 스트리밍 최대 세션 수 ($M \le 10$) |
| `FFMPEG_PATH` | `/usr/bin/ffmpeg` | FFmpeg 바이너리 경로 (Docker: `/usr/bin/ffmpeg`, Win: `./bin/ffmpeg.exe`) |
| `FFPROBE_PATH` | `/usr/bin/ffprobe` | FFprobe 바이너리 경로 (Docker: `/usr/bin/ffprobe`, Win: `./bin/ffprobe.exe`) |

---

## 💻 로컬 개발 환경 실행 방법

### 1. 사전 요구사항
- Python 3.10 이상
- FFmpeg 및 FFprobe 설치 (Windows의 경우 `./bin/ffmpeg.exe` 배치 권장)

### 2. 가상환경 생성 및 의존성 설치
```powershell
# 가상환경 생성
python -m venv .venv

# 가상환경 활성화 (Windows PowerShell)
.venv\Scripts\Activate.ps1

# 의존성 패키지 설치
pip install -r requirements.txt
```

### 3. 서버 구동
프로젝트 루트에서 다음 명령어로 서버를 시작합니다:
```powershell
# 방법 1: main.py를 통한 실행 (포트 5000 기본)
python main.py

# 방법 2: Uvicorn 직접 실행
uvicorn main:app --host 0.0.0.0 --port 5000
```

### 4. 접속 확인
- 웹 대시보드: [http://localhost:5000/fotostream](http://localhost:5000/fotostream)
- API 문서 (Swagger): [http://localhost:5000/fotostream/docs](http://localhost:5000/fotostream/docs)
- 헬스체크: [http://localhost:5000/fotostream/api/status](http://localhost:5000/fotostream/api/status)

---

## 🐳 Docker 컨테이너 배포 가이드

FOTOSTREAM은 단일 컨테이너 배포 및 Docker Compose 배포를 모두 완벽하게 지원합니다.

### 1. Dockerfile 빌드 및 단일 컨테이너 실행

#### 이미지 빌드
```bash
docker build -t fotostream:latest .
```

#### 컨테이너 실행 (Persistent Volume & 포트 5000 바인딩)
호스트의 `./storage` 폴더를 컨테이너의 `/app/storage`로 볼륨 마운트하여 DB 및 동영상 데이터의 영구 보존을 보장합니다:
```bash
docker run -d \
  --name fotostream-app \
  -p 5000:5000 \
  -e DEFAULT_PREFIX=/fotostream \
  -e DB_PATH=/app/storage/fotostream.db \
  -v $(pwd)/storage:/app/storage \
  fotostream:latest
```

### 2. Docker Compose를 통한 원클릭 배포 (권장)
제공된 `docker-compose.yml`을 사용하여 손쉽게 서비스를 구동할 수 있습니다:
```bash
# 서비스 빌드 및 백그라운드 시작
docker compose up -d

# 서비스 로그 확인
docker compose logs -f

# 서비스 중지
docker compose down
```

### 3. 컨테이너 헬스체크 사양
Dockerfile에 정의된 헬스체크는 컨테이너 내부에서 `DEFAULT_PREFIX` 환경변수를 감지하여 동작합니다:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=5s \
    CMD python -c "import os, requests; prefix = os.getenv('DEFAULT_PREFIX', ''); requests.get(f'http://localhost:5000{prefix}/api/status')"
```
- 컨테이너 상태 점검:
  ```bash
  docker ps --filter "name=fotostream-app"
  ```
  *(정상 구동 시 `STATUS: Up ... (healthy)` 표시)*

### 4. 서버 기동 명령어 (CMD 옵션 선택)
`Dockerfile`의 마지막 줄에서 운영 환경에 맞는 기동 명령어를 선택할 수 있습니다:

1. **Option 1: Gunicorn 운영 서버 (기본 활성화)**
   ```dockerfile
   CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--log-level", "debug", "--access-logfile", "-", "--error-logfile", "-", "--capture-output", "main:app"]
   ```
   - `gunicorn.conf.py`에 선언된 `worker_class = "uvicorn.workers.UvicornWorker"`를 통해 멀티 워커 비동기 고속 처리를 지원합니다.

2. **Option 2: Uvicorn 단독 경량 서버 (대안)**
   ```dockerfile
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
   ```

---

## 📡 API 엔드포인트 및 헬스체크

모든 API는 환경변수 `DEFAULT_PREFIX`(기본값: `/fotostream`) 하위에 마운트됩니다:

### 시스템 및 헬스체크 API
| HTTP Method | 경로 | 설명 |
| :--- | :--- | :--- |
| `GET` | `/{DEFAULT_PREFIX}/api/status` | Docker 컨테이너 및 로드밸런서용 헬스체크 엔드포인트 |
| `GET` | `/api/status` | 루트 레벨 헬스체크 대체 엔드포인트 |
| `GET` | `/{DEFAULT_PREFIX}/api/v1/system/status` | 활성 인코딩 워커 및 스트리밍 세션 실시간 통계 모니터링 |

### 비디오 합성 작업 (Jobs) API
| HTTP Method | 경로 | 설명 |
| :--- | :--- | :--- |
| `POST` | `/{DEFAULT_PREFIX}/api/v1/jobs` | 1~49장 사진 및 BGM 업로드, 해상도(`720p`, `1080p`, `1440p`, `1920p`) 지정 후 합성 큐 등록 |
| `GET` | `/{DEFAULT_PREFIX}/api/v1/jobs` | 최근 합성 작업 진행 상황 목록 조회 |
| `GET` | `/{DEFAULT_PREFIX}/api/v1/jobs/{job_id}` | 특정 작업의 상태 및 진행률(`progress`) 조회 |
| `DELETE`| `/{DEFAULT_PREFIX}/api/v1/jobs/{job_id}` | 대기/진행 중인 작업 취소 |

### 완성 영상 (Videos) & 스트리밍 API
| HTTP Method | 경로 | 설명 |
| :--- | :--- | :--- |
| `GET` | `/{DEFAULT_PREFIX}/api/v1/videos` | 생성 완료된 비디오 목록 및 재생 메타데이터 조회 |
| `GET` | `/{DEFAULT_PREFIX}/api/v1/videos/{video_id}` | 특정 비디오 상세 정보 조회 |
| `GET` | `/{DEFAULT_PREFIX}/api/v1/videos/{video_id}/stream` | **HTTP 206 Partial Content 스트리밍 엔드포인트** |
| `GET` | `/{DEFAULT_PREFIX}/api/v1/videos/{video_id}/thumbnail` | 비디오 대표 썸네일 이미지 제공 |
| `GET` | `/{DEFAULT_PREFIX}/api/v1/videos/{video_id}/download` | MP4 비디오 원본 파일 다운로드 |
| `DELETE`| `/{DEFAULT_PREFIX}/api/v1/videos/{video_id}` | 생성된 비디오 및 관련 디스크 파일 영구 삭제 |

### 배경음악 (BGM) API
| HTTP Method | 경로 | 설명 |
| :--- | :--- | :--- |
| `GET` | `/{DEFAULT_PREFIX}/api/v1/bgm` | 등록된 BGM 목록 조회 (5곡의 밝은 프리셋 포함) |
| `POST` | `/{DEFAULT_PREFIX}/api/v1/bgm` | 관리자용 신규 BGM 음원 파일(MP3/WAV 등) 서버 등록 |
| `GET` | `/{DEFAULT_PREFIX}/api/v1/bgm/{bgm_id}/stream` | 오디오 미리듣기 스트리밍 |
| `DELETE`| `/{DEFAULT_PREFIX}/api/v1/bgm/{bgm_id}` | 등록된 BGM 음원 삭제 (DB 레코드 및 물리 파일 정리) |

---

## 🧪 테스트 실행 방법

전체 기능(엔드포인트 검증, NxM 수학적 그리드 계산, 줌인/줌아웃 합성 엔진, HTTP 206 바이트 레인지 스트리밍 세션 제어)을 검증하는 종합 테스트 스위트가 포함되어 있습니다:

```powershell
# 전체 테스트 실행
python -m pytest

# 상세 로그와 함께 실행
python -m pytest -v
```

**테스트 스위트 구성**:
- `tests/test_api.py`: 작업 등록, 다중 해상도 검증, BGM 라이브러리, 대시보드 렌더링, 컨테이너 헬스체크 및 리다이렉트 검증 (6개 테스트)
- `tests/test_grid_calculator.py`: 1~49개 이미지에 대한 $N \times M$ 조건 검증 및 레이아웃 산출 (2개 테스트)
- `tests/test_streaming_and_synthesis.py`: E2E 비디오 합성, FFprobe 비트레이트/FPS 검증, HTTP 206 Range 스트리밍 및 동시 세션 제한(HTTP 429) 검증 (2개 테스트)

---

## 📄 라이선스
MIT License. 자유롭게 수정 및 배포가 가능합니다.
