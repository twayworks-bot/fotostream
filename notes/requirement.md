# FOTOSTREAM 시스템 개발 요구사항 정의서 (requirement.md)

> **문서 버전**: v1.3.0  
> **최초 작성일**: 2026-10-14 20:28  
> **최종 갱신일**: 2026-10-14 21:36  
> **상태**: 승인 및 고해상도 원본 줌 전환(Hybrid Resolution Transition) 확장 반영 (Approved)  
> **누적 관리**: 본 문서는 시스템 개발 진행에 따른 모든 요구사항 변경 및 추가 사항을 누적하여 기록합니다.

---

## 1. 개요 및 배경
FOTOSTREAM 프로젝트는 대량의 사진(최대 49장)을 매트릭스 레이아웃과 줌인/줌아웃 트랜지션 효과를 통해 한 편의 다이내믹한 슬라이드쇼 비디오로 자동 제작하고, 이를 웹 기반으로 안전하고 신속하게 관리 및 스트리밍하는 것을 목표로 합니다.
추가 요구사항에 따라, 영상의 화질을 대폭 개선하여 **표준 해상도 1080p(1920x1080)를 기본**으로 하고 최소 720p부터 최대 1920p(3414x1920)까지 사용자가 자유롭게 해상도를 선택할 수 있도록 옵션을 제공합니다. 또한, 배경음악의 분위기를 획기적으로 개선하여 **밝고 경쾌한 분위기의 5곡**을 엄선하여 기본 BGM으로 자동 적재합니다.

---

## 2. 사용자 요구사항의 기능적 요구사항(FR) 누적 명세

### [FR-01] 포토 이미지 및 멀티미디어 업로드 처리
- **FR-01.1 이미지 다중 업로드**: 사용자는 1회 요청 시 최소 1장부터 최대 49장까지의 사진 이미지를 다중 업로드할 수 있어야 한다.
- **FR-01.2 포맷 및 무결성 검증**: 지원 포맷은 `JPG`, `JPEG`, `PNG`, `WEBP` 등 웹 표준 이미지여야 하며, 파일 헤더 및 PIL(Pillow)을 통한 이미지 무결성을 검증한다.
- **FR-01.3 업로드 자원 관리**: 업로드된 이미지는 유니크한 Job ID 폴더(`storage/uploads/{job_id}/`)에 안전하게 격리 저장된다.
- **FR-01.4 이미지 순서 지정**: 업로드 시 파일명 또는 사용자가 지정한 순서 메타데이터를 보존하여 비디오 합성 시 순차 슬라이딩 순서로 활용한다.

### [FR-02] 배경음악(BGM) 오디오 연동 및 합성
- **FR-02.1 BGM 적용 방식의 다양화**:
  1. **BGM 라이브러리 선택**: 관리자가 사전 등록한 BGM 리스트 중 하나를 선택.
  2. **사용자 직접 업로드**: 개별 음원 파일(`MP3`, `WAV`, `AAC`, `OGG`, `M4A`) 직접 업로드.
  3. **무음(No BGM)**: 배경음악 없이 영상만 합성.
- **FR-02.2 오디오 동기화 및 길이 조절**: 합성된 비디오 전체 길이에 맞추어 오디오를 자동 루프(Loop)시키거나, 영상 종료 시점에 맞춰 부드럽게 페이드아웃(Fade-out) 처리한다.

### [FR-03] NxM 최적 매트릭스 자동 계산 알고리즘
- **FR-03.1 매트릭스 조건식**: 이미지 개수 $K$ ($1 \le K \le 49$)에 대하여 그리드 행(Row) $N$과 열(Column) $M$은 다음 조건을 만족해야 한다.
  $$\text{Grid}(N, M) \quad \text{where} \quad M = N \quad \text{or} \quad N = M \pm 1$$
  $$\text{Capacity} = N \times M \ge K$$
  $$\text{Minimize } (N \times M - K) \text{ and Aspect Ratio close to } 16:9$$
- **FR-03.2 다중 해상도 캔버스 지원**: $N \times M$ 그리드 셀 배치는 720p(1280x720), 1080p(1920x1080), 1440p(2560x1440), 1920p(3414x1920) 캔버스에 비례하여 동적으로 자동 계산된다.

### [FR-04] 비디오 합성 엔진 및 다중 해상도 지원 (확장)
- **FR-04.1 베이스 매트릭스 캔버스 생성**: 선택된 해상도 캔버스 상에 각 이미지를 썸네일로 균일하게 배치. 빈 셀(K < N*M)은 세련된 블러 또는 배경 플레이스홀더로 마감.
- **FR-04.2 줌인 $\rightarrow$ 유지 $\rightarrow$ 줌아웃 $\rightarrow$ 슬라이딩 시퀀스 (고해상도 원본 보존)**:
  - Step 1: 전체 $N \times M$ 매트릭스 조망 (Intro 1.0초)
  - Step 2: $i$번째 이미지 셀 위치로 부드러운 코사인 Ease-in-out 줌인 확대 (0.5초)
    - 줌인 초기($t < 0.35$): 전체 매트릭스 뷰에서 대상 셀 중심점으로 부드럽게 줌 시작.
    - 줌인 중간($0.35 \le t \le 0.70$): 매트릭스 크롭 뷰와 원본 고해상도 이미지 간의 **코사인 알파 블렌딩(Cross-fade)**을 수행하여 고해상도 원본으로 자연스럽게 전환.
    - 줌인 완료($t > 0.70$): **100% 원본 고해상도 뷰**에 도달하여 저해상도 픽셀 깨짐을 완벽 방지.
  - Step 3: **원본 고해상도 이미지 상태로 집중 감상 (Hold 1.5초)**: 1080p/720p/1920p 원본 디테일을 최고 화질로 선명하게 유지.
  - Step 4: 다시 전체 $N \times M$ 매트릭스로 줌아웃 축소 복귀 (0.5초)
    - 고해상도 원본에서 줌아웃을 개시한 뒤 중간 지점($0.30 \le t \le 0.65$)에서 매트릭스 크롭 뷰로 부드럽게 크로스페이드 복귀.
  - Step 5: 다음 이미지 $(i+1)$로 동일 시퀀스 반복
  - Step 6: 모든 이미지 탐색 완료 후 전체 매트릭스 아웃트로(Outro 1.0초) 및 페이드아웃
- **FR-04.3 다중 해상도 선택 옵션**:
  - `720p`: $1280 \times 720$ (최소 화질, 고속 렌더링)
  - `1080p`: $1920 \times 1080$ (**표준 기본값 Standard Default**, Full HD)
  - `1440p`: $2560 \times 1440$ (2K QHD 고화질)
  - `1920p`: $3414 \times 1920$ (최대 초고화질)
- **FR-04.4 인코딩 최적화 및 제약**:
  - 코덱: H.264 (libx264), 오디오 AAC (aac)
  - 프레임레이트: 30 fps
  - 픽셀 포맷: `yuv420p`, `+faststart` 적용
  - 비트레이트: 해상도별 적응형 제어로 100MB 및 10분 상한 준수.

### [FR-05] 비동기 작업 큐 및 동시성 제어
- **FR-05.1 비동기 백그라운드 큐**: 이미지 업로드 즉시 작업 ID(Job ID)를 반환하고, 실제 합성은 내부 작업 큐(In-memory / SQLite Persistent Task Queue)를 통해 비동기로 처리한다.
- **FR-05.2 동시 합성 워커 제한 ($N \le 3$)**:
  - 동시에 진행되는 비디오 합성 작업은 **최대 3개**로 엄격히 제한한다.
  - 초과 시 `QUEUED` 대기, 순차 실행.
- **FR-05.3 상태 라이프사이클**: `QUEUED` $\rightarrow$ `PROCESSING` (0~100%) $\rightarrow$ `COMPLETED` or `FAILED`.

### [FR-06] 비디오 스트리밍 엔드포인트 URL 및 동시 스트리밍 제어
- **FR-06.1 스트리밍 엔드포인트 제공**: `GET /fotostream/api/v1/videos/{video_id}/stream`
- **FR-06.2 HTTP Range Request (206 Partial Content)**: 브라우저 표준 Seek 및 버퍼링 지원.
- **FR-06.3 동시 스트리밍 제한 ($M = 10$)**: 활성화된 동시 스트리밍 연결 수를 **최대 10개**로 제한 관리 (초과 시 HTTP 429 반환).

### [FR-07] 웹 대시보드 (Demo Admin UI) 확장
- **FR-07.1 통합 대시보드 제공**: 경로 `http://<host>:5000/fotostream`
- **FR-07.2 해상도 선택 UI (신규)**:
  - 동영상 생성 폼 내 **해상도 선택 옵션** 제공 (720p, 1080p[기본 선택], 1440p, 1920p).
- **FR-07.3 밝고 경쾌한 BGM 선택기 (개선)**:
  - 밝고 경쾌한 분위기의 5곡 카드 목록 표시, 트랙별 실시간 미리듣기 플레이어 연동.
- **FR-07.4 실시간 큐 & 갤러리 관리**:
  - 진행 상태 프로그레스 바, 비디오 팝업 스트리밍 플레이어, 다운로드 및 삭제 기능.

### [FR-08] RESTful API 규격 (해상도 파라미터 반영)
- `POST /fotostream/api/v1/jobs`: 사진(1~49장), 해상도(`resolution: 720p/1080p/1440p/1920p`), BGM 선택/업로드
- `GET /fotostream/api/v1/jobs/{job_id}`: 작업 상태 조회
- `GET /fotostream/api/v1/jobs`: 최근 작업 목록
- `DELETE /fotostream/api/v1/jobs/{job_id}`: 작업 취소
- `GET /fotostream/api/v1/videos`: 완성된 비디오 라이브러리 목록
- `GET /fotostream/api/v1/videos/{video_id}/stream`: 비디오 스트리밍 엔드포인트
- `GET /fotostream/api/v1/bgm`: BGM 목록 조회
- `POST /fotostream/api/v1/bgm`: 관리자 BGM 음원 파일 및 정보 등록
- `GET /fotostream/api/v1/bgm/{bgm_id}/stream`: BGM 미리듣기 스트리밍
- `GET /fotostream/api/v1/system/status`: 시스템 및 자원 현황 조회

### [FR-09] 무료 BGM 라이브러리 (밝고 경쾌한 5곡 엄선 등록)
- **FR-09.1 밝고 경쾌한 프리셋 5곡 교체 및 자동 적재**:
  - 기존의 단조롭고 음산한 sine 단일 주파수 음원을 전면 폐기.
  - 활기차고 경쾌한 장조(Major Key) 화음 및 리듬을 가진 5곡의 고품질 번들 음원을 자동 시딩:
    1. **Sunny Morning Walk** (Acoustic / 따뜻하고 상쾌한 아침 산책)
    2. **Upbeat Joyful Ukulele** (Ukulele & Pop / 밝고 명랑한 피크닉 분위기)
    3. **Bright Energy Dance** (Synth Pop / 활기차고 생동감 넘치는 팝 리듬)
    4. **Happy Acoustic Breeze** (Folk & Acoustic / 기분 좋은 산들바람)
    5. **Playful Summer Smile** (Marimba & Percussion / 경쾌하고 발랄한 여름 멜로디)
- **FR-09.2 관리자 BGM 등록 및 사용자 선택**:
  - Pixabay Music 등 외부 음원 관리자 등록 및 사용자 미리듣기/선택 기능 유지.
- **FR-09.3 BGM 항목 삭제 UI 및 상태 관리**:
  - 무료 BGM 라이브러리 카드 각 항목에 휴지통 아이콘 삭제 버튼 제공.
  - 클릭 시 확인 팝업(`confirm`), 오디오 재생 중지, 선택 상태 초기화, 비동기 `DELETE /api/v1/bgm/{id}` 호출 및 목록 갱신.
  - 물리 오디오 파일 자동 삭제 및 재시작 시 삭제된 프리셋 복구 방지.

### [FR-10] Docker 컨테이너화, 영구 볼륨 및 배포 가이드
- **FR-10.1 Dockerfile 및 런타임 이미지**:
  - `python:3.11-slim` 기반 경량화 컨테이너 구성 및 시스템 레벨 FFmpeg/FFprobe 설치.
  - 포트 `5000` 노출 (`EXPOSE 5000`).
- **FR-10.2 Persistent Volume 연동 (데이터 보존)**:
  - SQLite 데이터베이스 파일 경로 `DB_PATH` 환경변수 지원 (예: `/app/storage/fotostream.db`).
  - 스토리지 디렉토리 `STORAGE_DIR=/app/storage` 및 `VOLUME ["/app/storage"]` 연동.
- **FR-10.3 `DEFAULT_PREFIX` 환경변수 기반 URL 표준화**:
  - 선행 슬래시 유무에 관계없이 `DEFAULT_PREFIX`를 정규화하여 웹앱 Base URL 및 모든 라우터 프리픽스로 바인딩.
  - 헬스체크 엔드포인트 `http://localhost:5000{prefix}/api/status` 지원.
- **FR-10.4 컨테이너 헬스체크 사양 준수**:
  - `HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=5s CMD python -c "import os, requests; prefix = os.getenv('DEFAULT_PREFIX', ''); requests.get(f'http://localhost:5000{prefix}/api/status')"`
- **FR-10.5 서버 구동 CMD 옵션 및 루트 엔트리포인트**:
  - 루트 `main.py`를 통해 `main:app` 표준 진입점 제공.
  - Gunicorn 멀티워커(`worker_class = "uvicorn.workers.UvicornWorker"`) 및 Uvicorn 단독 구동 지원.
- **FR-10.6 README.md 배포 및 통합 가이드 최신화**:
  - 프로젝트 개요, 기능 설명, 로컬 실행법, Docker 컨테이너 및 Compose 배포 가이드, API 명세 수록.

### [FR-11] 개인정보, 캐시, 민감 데이터 보호 및 무시 규칙 (.gitignore & .dockerignore)
- **FR-11.1 저장소 민감정보 유출 차단 (.gitignore)**:
  - `.env`, `.env.*`, `*.env`, 비밀키(`*.key`, `*.pem`), 인증서(`*.crt`), 토큰(`*token*`), 서비스 계정 자격증명(`credentials*.json`, `client_secret*.json`) 차단.
  - 런타임 데이터베이스(`storage/*.db`), 업로드 및 합성 미디어 파일, 호스트 종속 실행파일(`bin/`, `*.exe`) 차단.
  - Python 바이트코드(`__pycache__/`, `*.pyc`), 가상환경(`.venv/`), 테스트 캐시(`.pytest_cache/`, `.coverage`) 차단.
  - 안전한 공개 템플릿 `.env.example` 생성 및 예외 보존(`!.env.example`).
- **FR-11.2 Docker 빌드 컨텍스트 보안 및 최적화 (.dockerignore)**:
  - Git 메타데이터(`.git`), Docker 설정, 환경변수/시크릿 파일 원천 배제.
  - 테스트 스위트(`tests/`), 설계 문서(`notes/`, `GOAL.md`), Windows 바이너리(`bin/`), 런타임 스토리지(`storage/`) 배제로 빌드 컨텍스트 최소화 및 보안 강화.

### [FR-12] 종횡비 보존(Zero-Crop Contain) 및 벤토 그리드(Bento Grid) 레이아웃
- **FR-12.1 사진 종횡비 100% 보존 (무손실 맞춤)**:
  - 세로형 사진(Height > Width): 높이를 기준으로 셀 및 캔버스에 맞춤 스케일링하며, 좌우 빈 영역은 순수 검은색(`(0, 0, 0)`) 필라박스(Pillarbox)로 채움.
  - 가로형 사진(Width > Height): 폭을 기준으로 셀 및 캔버스에 맞춤 스케일링하며, 상하 빈 영역은 순수 검은색(`(0, 0, 0)`) 레터박스(Letterbox)로 채움.
  - `ImageOps.fit` 등 원본 사진 외곽을 잘라내는 크롭 모드 영구 배제.
- **FR-12.2 전체 사진 기준 정밀 줌(Zoom) 애니메이션**:
  - 개별 사진 확대 시 사진의 전체 영역이 모두 보이도록 캔버스 크기 대비 배율(`scale_in_canvas / scale_in_cell`)을 정밀 계산하여 줌 수행.
  - 썸네일 상태와 전체화면 고해상도 상태의 종횡비 및 여백이 100% 일치하여 크로스페이드 시 가장자리 흔들림 제거.
- **FR-12.3 벤토 그리드(Bento Grid) 동적 레이아웃 및 블랙 영역 최소화**:
  - 세로형 사진과 가로형 사진이 혼합된 경우 종횡비 특성을 클러스터링하여 행(Row)별 최적 높이 및 열(Column)별 가중치 폭을 동적으로 산출하는 벤토 그리드 배치 지원.
  - 검은 빈 영역 면적을 최소화하여 시각적 조화 극대화.
  - 배치 후 원본 업로드 순서(`cell.index`)를 유지하여 슬라이드 줌 시퀀스가 왜곡되지 않도록 보장.
  - 단일 비율 또는 균일 사진의 경우 기존 정규 NxM 그리드로 안전하게 자동 폴백(Fallback).

---

## 3. 요구사항 추적 매트릭스 (RTM)

| 요구사항 ID | 분류 | 세부 명세 요약 | 구현 모듈 | 테스트 검증 항목 |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-01** | API / 업로드 | 최대 49장 이미지 업로드 | `routers/jobs.py` | 1~49장 정상 수신 확인 |
| **REQ-02** | 비디오 엔진 | NxM 그리드 계산 및 다중 해상도 지원 | `services/grid_calculator.py` | 720p/1080p/1440p/1920p 좌표 정합성 검증 |
| **REQ-03** | 비디오 엔진 | 표준 1080p(기본) 및 720p~1920p 선택 합성 | `services/video_synthesizer.py` | 1080p 및 1920p 인코딩 메타데이터 검증 |
| **REQ-04** | BGM 라이브러리 | 밝고 경쾌한 프리셋 5곡 등록 및 미리듣기 | `services/bgm_manager.py` | 5곡 적재 및 오디오 스트리밍 검증 |
| **REQ-05** | 큐 / 비동기 | 동시 합성 최대 3개 및 대기열 처리 | `services/task_queue.py` | 세마포어(3) 동작 검증 |
| **REQ-06** | 스트리밍 | 동시 스트리밍 최대 10개 및 Range 지원 | `services/stream_manager.py` | 206 Partial 및 10개 한도 제한 검증 |
| **REQ-07** | 웹 UI | 해상도 선택 및 밝은 BGM UI | `templates/dashboard.html` | 브라우저 상 해상도/BGM 변경 확인 |
| **REQ-08** | 컨테이너 배포 | Dockerfile, Volume, Base Prefix, 헬스체크, README | `Dockerfile`, `main.py`, `README.md` | 컨테이너 헬스체크 엔드포인트 및 단위 테스트 100% 통과 |
| **REQ-09** | 보안 및 빌드 위생 | .gitignore, .dockerignore 최신화 및 .env.example | `.gitignore`, `.dockerignore`, `.env.example` | 패턴 매칭 검증 및 전체 테스트 11개 100% 통과 |
| **REQ-10** | 종횡비 및 레이아웃 | 세로/가로 긴쪽 기준 Contain, 블랙여백, 벤토그리드 | `services/grid_calculator.py`, `services/video_synthesizer.py` | 벤토 그리드 비중첩/경계 검증 및 종횡비 무손실 맞춤 테스트 (13개 100% 통과) |

