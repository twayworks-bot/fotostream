# FOTOSTREAM 시스템 세부 기술 규격서 (SPECIFICATION.md)

> **문서 버전**: v1.3.0  
> **갱신일**: 2026-10-14 21:36  
> **상태**: 구현 표준 명세 (Design Specification)

---

## 1. 해상도 프로필 및 비디오 합성 규격

### 1.1 지원 해상도 매핑 테이블
| 프로필 코드 | 화면 해상도 (가로x세로) | 종횡비 | 표준 구분 | FFmpeg 비트레이트 설정 | 권장 활용 용도 |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **`720p`** | $1280 \times 720$ | 16:9 | 최소 화질 | `-maxrate 2500k -bufsize 5000k` | 저용량 / 초고속 렌더링 |
| **`1080p`** | $1920 \times 1080$ | 16:9 | **표준 기본값 (Default)** | `-maxrate 4500k -bufsize 9000k` | **웹 표준 / 고화질 디스플레이** |
| **`1440p`** | $2560 \times 1440$ | 16:9 | 2K QHD 고화질 | `-maxrate 7000k -bufsize 14000k` | 고해상도 모니터 / TV 감상 |
| **`1920p`** | $3414 \times 1920$ | 16:9 | **최대 초고화질 (Max)** | `-maxrate 10000k -bufsize 20000k`| 프리미엄 초고화질 아카이빙 |

### 1.2 하이브리드 해상도 줌인/줌아웃 트랜지션 (Hybrid Resolution Zoom with Seamless Crossfade)
기존 저해상도 썸네일 크롭 디지털 줌의 픽셀 깨짐 현상을 원천 방지하기 위한 듀얼 레이어 하이브리드 합성 파이프라인:

1. **듀얼 레이어 프리렌더링**:
   - **Layer A (Base Grid Canvas)**: 전체 캔버스($W \times H$) 상에 각 이미지를 셀 크기($W_{\text{cell}} \times H_{\text{cell}}$)로 배치한 매트릭스 캔버스.
   - **Layer B (High-Res Normalized Images)**: 각 원본 이미지를 캔버스 해상도($W \times H$)에 맞게 고품질(LANCZOS)로 피팅한 최고 해상도 이미지.
2. **동적 크로스페이드 줌인 (Zoom In with Alpha Blending)**:
   - 프레임 $f \in [0, 15]$ ($t = f / 15$):
     - 카메라 이동 배율: $S(t) = 1.0 + (S_{\text{max}} - 1.0) \times \frac{1 - \cos(\pi \cdot t)}{2}$
     - $t < 0.35$: Layer A의 크롭 뷰 ($Frame_A$) 100% 렌더링.
     - $0.35 \le t \le 0.70$: 전환 구간. Layer A와 Layer B 간의 코사인 알파 블렌딩:
       $$W_B(t) = \frac{1 - \cos\left(\pi \cdot \frac{t - 0.35}{0.35}\right)}{2}$$
       $$Frame(t) = (1 - W_B(t)) \cdot Frame_A(t) + W_B(t) \cdot Frame_B(t)$$
     - $t > 0.70$: **Layer B (원본 고해상도 이미지) 100% 렌더링**.
3. **고해상도 원본 집중 감상 (Hold Inspection, 45 프레임)**:
   - **Layer B (100% 최고 해상도 원본)** 프레임을 송출하여 저해상도 뭉개짐 없이 선명한 화질 제공.
4. **동적 크로스페이드 줌아웃 (Zoom Out to Matrix)**:
   - 고해상도 뷰에서 줌아웃을 시작하고 중간 지점($0.30 \le t \le 0.65$)에서 Layer A 매트릭스 뷰로 부드럽게 크로스페이드 복귀.

> **용량 방어 메커니즘**: 모든 해상도에서 H.264 CRF 23 및 상한 비트레이트(-maxrate)를 강제하여 49장(약 2분) 기준 100MB를 초과하지 않도록 보장합니다.

---

## 2. 밝고 경쾌한 BGM 프리셋 5곡 스펙 정의

기존의 단순 단일 주파수 음원을 전면 폐기하고, 메이저 장조 화음 및 경쾌한 템포의 5곡을 기본 시딩합니다.

| 번호 | BGM ID | 곡명 (Title) | 분위기/장르 (Mood) | 음악적 특성 및 악기 구성 | 출처 및 라이선스 |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **1** | `preset-sunny-morning` | Sunny Morning Walk | Acoustic / Bright | C Major 화음, 밝은 통기타 스트럼 & 글로켄슈필 벨 멜로디 | Pixabay Music (CC0) |
| **2** | `preset-joyful-ukulele` | Upbeat Joyful Ukulele | Ukulele & Pop | G-D-Em-C 장조 진행, 경쾌한 우쿨렐레 리듬 & 휘파람 | Pixabay Music (CC0) |
| **3** | `preset-energy-dance` | Bright Energy Dance | Synth Pop / Upbeat | 밝고 경쾌한 124BPM 댄스 비트 & 신나는 아르페지오 | Pixabay Music (CC0) |
| **4** | `preset-happy-breeze` | Happy Acoustic Breeze | Folk & Acoustic | 기분 좋은 산들바람 느낌의 따뜻한 핑거스타일 기타 | Pixabay Music (CC0) |
| **5** | `preset-summer-smile` | Playful Summer Smile | Marimba & Upbeat | 발랄한 마림바 타악기 & 활기찬 라틴 퍼커션 리듬 | Pixabay Music (CC0) |

---

## 3. 데이터베이스 스키마 및 도메인 모델

### 3.1 Table: `jobs` (해상도 컬럼 반영)
| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | VARCHAR(36) | PRIMARY KEY | UUID v4 고유 식별자 |
| `title` | VARCHAR(255) | NOT NULL | 작업 제목 / 앨범명 |
| `status` | VARCHAR(30) | NOT NULL | `QUEUED`, `PROCESSING`, `COMPLETED`, `FAILED`, `CANCELED` |
| `progress` | INTEGER | DEFAULT 0 | 진행률 (0 ~ 100%) |
| `resolution` | VARCHAR(20) | DEFAULT "1080p" | **선택된 해상도 (`720p`, `1080p`, `1440p`, `1920p`)** |
| `image_count` | INTEGER | NOT NULL | 업로드된 사진 개수 (1 ~ 49) |
| `grid_rows` | INTEGER | NULL | 계산된 그리드 행 $N$ |
| `grid_cols` | INTEGER | NULL | 계산된 그리드 열 $M$ |
| `bgm_id` | VARCHAR(36) | NULL | 선택된 `bgm_tracks.id` |
| `bgm_filename` | VARCHAR(255) | NULL | 직접 업로드된 BGM 파일명 |
| `error_message`| TEXT | NULL | 작업 실패 시 상세 에러 로그 |
| `created_at` | DATETIME | NOT NULL | 작업 등록 일시 |

### 3.2 Table: `videos`
| 컬럼명 | 데이터 타입 | 제약 조건 | 설명 |
| :--- | :--- | :--- | :--- |
| `id` | VARCHAR(36) | PRIMARY KEY | UUID v4 고유 식별자 |
| `job_id` | VARCHAR(36) | FOREIGN KEY | 생성에 사용된 `jobs.id` |
| `title` | VARCHAR(255) | NOT NULL | 비디오 제목 |
| `filename` | VARCHAR(255) | NOT NULL | 저장된 mp4 파일명 |
| `file_path` | VARCHAR(500) | NOT NULL | 로컬 파일 경로 |
| `file_size` | BIGINT | NOT NULL | 파일 크기 (Bytes, $\le 100\text{MB}$) |
| `duration` | FLOAT | NOT NULL | 재생 시간 (초 단위, $\le 600\text{초}$) |
| `resolution` | VARCHAR(20) | NOT NULL | 실제 합성된 해상도 (예: `1920x1080`) |
| `thumbnail_path`| VARCHAR(500) | NULL | 대표 썸네일 경로 |
| `stream_url` | VARCHAR(500) | NOT NULL | 스트리밍 엔드포인트 URL |
| `view_count` | INTEGER | DEFAULT 0 | 누적 재생 횟수 |
| `created_at` | DATETIME | NOT NULL | 생성 일시 |

---

## 4. RESTful API 명세 갱신

### `POST /fotostream/api/v1/jobs`
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `images`: 다중 이미지 파일 (1~49장) [필수]
  - `title`: 비디오 제목 [선택, 기본: "My Photo Slideshow"]
  - `resolution`: **해상도 옵션 [선택, 기본값: `"1080p"`]** (`"720p"`, `"1080p"`, `"1440p"`, `"1920p"`)
  - `bgm_id`: 선택된 BGM ID [선택]
  - `bgm_file`: 직접 업로드 음원 파일 [선택]
- **Response**: `202 Accepted` (`job_id`, `resolution`, `status: "QUEUED"`)

---

## 5. UI/UX 확장 설계

- **해상도 선택 라디오/버튼 그룹**:
  - `[720p]`, `[1080p (표준 추천)]` (기본 선택), `[1440p (2K)]`, `[1920p (최대)]`
  - 각 옵션별 추천 라벨 및 해상도 픽셀 표기
- **밝고 경쾌한 BGM 선택 카드**:
  - 밝은 무드 태그(`Acoustic`, `Upbeat`, `Pop`, `Dance`, `Marimba`)와 함께 5곡의 프리셋을 시각적으로 돋보이게 렌더링.
  - **각 항목별 삭제 버튼**: 각 BGM 카드 우측에 휴지통 아이콘 삭제 버튼 배치 (`hover:text-rose-400`, `event.stopPropagation()`).
  - **삭제 인터랙션**: 브라우저 `confirm` 팝업을 통한 삭제 확인 $\rightarrow$ 비동기 `DELETE /api/v1/bgm/{id}` 호출 $\rightarrow$ 재생 중 오디오 정지 및 선택 상태 초기화 $\rightarrow$ 목록 실시간 갱신.

---

## 6. Docker 컨테이너 및 배포 아키텍처 (Deployment Specification)

### 6.1 Dockerfile 구성 사양
- **베이스 이미지**: `python:3.11-slim` (안정적이고 경량화된 Debian 기반 런타임)
- **시스템 패키지**: `ffmpeg`, `curl`
- **포트 노출**: `EXPOSE 5000`
- **영구 보존 볼륨 (Persistent Volume)**: `VOLUME ["/app/storage"]`
- **환경변수 기본값**:
  - `PORT=5000`, `HOST=0.0.0.0`
  - `DEFAULT_PREFIX=/fotostream`
  - `DB_PATH=/app/storage/fotostream.db`
  - `STORAGE_DIR=/app/storage`, `UPLOAD_DIR=/app/storage/uploads`, `BGM_DIR=/app/storage/bgm`, `TRANSCODE_DIR=/app/storage/transcoded`
  - `FFMPEG_PATH=/usr/bin/ffmpeg`, `FFPROBE_PATH=/usr/bin/ffprobe`
- **컨테이너 헬스체크**:
  ```dockerfile
  HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=5s \
      CMD python -c "import os, requests; prefix = os.getenv('DEFAULT_PREFIX', ''); requests.get(f'http://localhost:5000{prefix}/api/status')"
  ```
- **실행 CMD**:
  - Option 1 (Gunicorn 운영 서버):
    `CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--log-level", "debug", "--access-logfile", "-", "--error-logfile", "-", "--capture-output", "main:app"]`
    (`gunicorn.conf.py`를 통해 `worker_class = "uvicorn.workers.UvicornWorker"` 자동 연동)
  - Option 2 (Uvicorn 개발/경량 구동):
    `CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]`

### 6.2 URL Prefix 및 라우팅 정규화
- `Settings.clean_prefix`: 선행/후행 슬래시를 제거한 문자열(예: `fotostream`).
- `Settings.url_prefix`: 선행 슬래시 1개를 보장하고 후행 슬래시를 제거한 URL 마운트 경로(예: `/fotostream`).
- 전용 헬스체크 엔드포인트: `/{DEFAULT_PREFIX}/api/status` 및 `/api/status` 모두 200 OK 응답 보장.

---

## 7. 보안 및 빌드 배제 규칙 (Security & Ignore Rules)

### 7.1 `.gitignore` (소스코드 저장소 보호)
- **비밀키 및 인증 자격증명 차단**: `.env`, `*.env`, `.env.*`, `*.key`, `*.pem`, `*.crt`, `credentials*.json`, `client_secret*.json`, `*token*`
- **안전한 공개 템플릿 보존**: `.env.example`
- **영구 스토리지 및 미디어 격리**: `storage/`, `downloads/`, `*.db`, `*.sqlite*`, 비디오/오디오 파일
- **로컬 호스트 바이너리 배제**: `bin/`, `*.exe`, `*.dll`, `*.so`
- **캐시 및 임시 파일 차단**: `__pycache__/`, `.pytest_cache/`, `.coverage`, `.mypy_cache/`, `*.log`, `tmp/`, `scratch/`
- **쉘 히스토리 차단**: `.bash_history`, `.python_history`

### 7.2 `.dockerignore` (컨테이너 빌드 컨텍스트 최적화)
- **빌드 컨텍스트 누출 차단**: `.env`, 시크릿/키 파일, `.git/`, `notes/`, `GOAL.md`, `tests/`
- **호스트 종속성 배제**: `bin/` (Windows FFmpeg 대신 컨테이너 내부 apt 패키지 사용), `.venv/`
- **런타임 볼륨 배제**: `storage/`, `downloads/` (호스트 마운트로 런타임에 주입)


