# FOTOSTREAM 개발 이력 및 요구사항 요약 (history.md)

이 문서는 프로젝트 진행에 따른 모든 사용자 요구사항, 설계 변경 및 개발 요약 내역을 시간순으로 누적 관리하는 이력 문서입니다.

---

## [2026-10-14 22:22] .gitignore 및 .dockerignore 최신화: 개인정보, 캐시, 민감 데이터 보호 강화

### 1. 개발 내용 요약
- **`.gitignore` 8대 보안 카테고리 최신화**:
  - 환경변수 및 시크릿: `.env`, `*.env`, `.env.*`, 비밀키(`*.key`, `*.pem`), 인증서(`*.crt`), SSH 키(`id_rsa*`, `id_ed25519*`), 토큰(`*token*`), 서비스 계정 파일(`credentials*.json`, `client_secret*.json`) 차단.
  - 안전한 공개용 템플릿 `.env.example` 생성 및 예외 보존(`!.env.example`).
  - 영구 스토리지 및 미디어: `storage/`, `storage/*`, `*.db`, `*.sqlite*`, 저널/WAL 파일, 업로드/인코딩 미디어(`*.mp4`, `*.mp3` 등) 차단.
  - 로컬 바이너리: `bin/`, `*.exe`, `*.dll`, `*.so` 차단.
  - 바이트코드 및 캐시: `__pycache__/`, `.pytest_cache/`, `.coverage`, `htmlcov/`, `.mypy_cache/`, `.venv/` 차단.
  - 로그, 임시 파일 및 쉘 히스토리: `*.log`, `scratch/`, `tmp/`, `.bash_history`, `.python_history` 차단.
- **`.dockerignore` 전면 개편**:
  - Git 형상관리 메타데이터(`.git`), Docker 설정, 환경변수 파일 배제.
  - Windows 호스트 바이너리(`bin/`), 가상환경(`.venv/`), 단위 테스트(`tests/`), 설계 문서(`notes/`, `GOAL.md`)를 도커 빌드 컨텍스트에서 원천 제외하여 빌드 속도 및 보안 극대화.
- **검증 결과**:
  - Pytest 11개 테스트 스위트 전원 통과 (`11 passed in 26.77s`).

### 2. 작성 산출물
- `.gitignore`: 소스코드 저장소 보안 무시 규칙 최신화
- `.dockerignore`: 컨테이너 빌드 컨텍스트 제외 규칙 전면 개편
- `.env.example`: 안전한 환경변수 설정 템플릿
- `notes/req_202610142222.md`: 사용자 원본 요구사항 및 분석 기록
- `notes/plan_202610142222.md`: 파일 제외 및 보안 강화 계획서
- `notes/result_202610142222.md`: 개발 결과 및 검증 상세 보고서
- `notes/requirement.md`: [FR-11] 누적 요구사항 및 RTM [REQ-09] 반영

---

## [2026-10-14 22:08] 등록된 무료 BGM 라이브러리 항목 삭제 버튼 추가 및 상태 관리 연동

### 1. 개발 내용 요약
- **BGM 카드 UI 삭제 버튼 구현**:
  - `app/static/js/bgm_selector.js`의 `renderBgmCards()`에서 각 BGM 항목 우측에 휴지통 아이콘 삭제 버튼 추가.
  - 마우스 호버 효과(`hover:text-rose-400`, `hover:bg-rose-500/10`) 및 이벤트 전파 방지(`event.stopPropagation()`) 적용.
- **비동기 삭제 및 상태 동기화 파이프라인**:
  - `deleteBgmTrack(prefix, trackId, trackTitle)` 함수 구현.
  - 삭제 전 확인 팝업(`confirm`)을 띄워 오동작 방지.
  - 재생 중인 오디오가 삭제될 경우 즉시 정지(`currentAudio.pause()`) 및 아이콘 리셋.
  - 선택되어 있던 트랙이 삭제될 경우 `selectedBgmId` 초기화.
  - `DELETE /api/v1/bgm/{id}` 호출 후 `loadBgmTracks()` 비동기 호출로 목록 즉시 갱신.
- **프리셋 재시작 보존 관리**:
  - `bgm_manager.py`에 `.presets_seeded` 마커 파일 로직을 적용하여 사용자가 삭제한 프리셋이 서버 재시작 시 강제로 복원되지 않도록 보장.
- **검증 결과**:
  - 신규 `test_delete_bgm_track`를 포함하여 pytest 11개 테스트 스위트 전원 통과 (`11 passed in 22.83s`).

### 2. 작성 산출물
- `app/static/js/bgm_selector.js`: BGM 카드 삭제 버튼 및 `deleteBgmTrack` 구현
- `app/services/bgm_manager.py`: `.presets_seeded` 마커 연동
- `tests/test_api.py`: `test_delete_bgm_track` 테스트 추가
- `notes/req_202610142208.md`: 사용자 원본 요구사항 및 분석 기록
- `notes/plan_202610142208.md`: BGM 항목 삭제 개발 계획서
- `notes/result_202610142208.md`: 개발 결과 및 검증 상세 보고서
- `notes/requirement.md`: [FR-09.3] 누적 요구사항 반영

---

## [2026-10-14 21:48] Dockerfile 컨테이너화, Persistent Volume 연동, DEFAULT_PREFIX 정규화 및 README.md 종합 가이드 작성

### 1. 개발 내용 요약
- **Dockerfile 및 배포 인프라 구축**:
  - `python:3.11-slim` 기반 프로덕션 `Dockerfile` 작성 (FFmpeg/FFprobe 시스템 패키지 설치).
  - 포트 `5000` 노출 (`EXPOSE 5000`).
  - Persistent Volume 연동: `/app/storage` 영구 볼륨 지정(`VOLUME ["/app/storage"]`) 및 `DB_PATH=/app/storage/fotostream.db` 환경변수 처리.
  - 컨테이너 헬스체크 정의:
    `HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=5s CMD python -c "import os, requests; prefix = os.getenv('DEFAULT_PREFIX', ''); requests.get(f'http://localhost:5000{prefix}/api/status')"`
  - 구동 CMD: Option 1(Gunicorn 운영 서버) 기본 활성화 및 `gunicorn.conf.py`(`worker_class = "uvicorn.workers.UvicornWorker"`) 자동 바인딩, Option 2(Uvicorn 경량 서버) 가이드 제공.
- **Base URL `DEFAULT_PREFIX` 표준화**:
  - `clean_prefix` (`fotostream`) 및 `url_prefix` (`/fotostream`) 정규화 프로퍼티 구현.
  - 전용 헬스체크 엔드포인트 `/{url_prefix}/api/status` 및 `/api/status` 추가.
  - 템플릿 정적 자원 및 JS API 호출 경로 안전성 강화.
- **루트 엔트리포인트 및 컴포즈 지원**:
  - `main.py` 루트 생성하여 `main:app` 표준 진입점 제공.
  - `docker-compose.yml` 및 `.dockerignore` 생성.
- **종합 프로젝트 문서 `README.md` 작성**:
  - 프로젝트 개요 및 목적, 핵심 기능 5종, 시스템 아키텍처, 환경변수 목록, 로컬 실행법, Docker 배포 가이드, API 명세서 수록.
- **검증 결과**:
  - Pytest 10개 테스트 스위트 전원 통과 (`10 passed in 24.08s`).

### 2. 작성 산출물
- `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `gunicorn.conf.py`, `main.py`
- `README.md`: 프로젝트 목적, 사용법, 배포방법, 실행방법 총괄 가이드
- `notes/req_202610142148.md`: 사용자 원본 요구사항 및 분석 기록
- `notes/plan_202610142148.md`: 도커 컨테이너화 및 배포 문서 개발 계획서
- `notes/result_202610142148.md`: 개발 결과 및 검증 상세 보고서
- `notes/requirement.md`: 누적 요구사항 [FR-10] 및 RTM [REQ-08] 반영

---

## [2026-10-14 21:36] 고해상도 원본 줌 전환(Hybrid Resolution Zoom with Seamless Crossfade) 구현 및 화질 개선

### 1. 개발 내용 요약
- **화질 저하 원인 규명 및 해결**:
  - 기존 방식: 작은 셀 썸네일(약 200~300px)을 단순 디지털 크롭 확대하여 줌인 완료 시 화질 뭉개짐 발생.
  - 개선 방식: **듀얼 레이어 프리렌더링(Layer A: 매트릭스 캔버스, Layer B: 100% 원본 고해상도 이미지) 및 동적 코사인 크로스페이드(Alpha Crossfade)** 파이프라인 구현.
- **핵심 알고리즘 적용**:
  - 줌인 구간: 전체 뷰에서 부드럽게 줌을 시작한 뒤 중간 지점($0.35 \le t \le 0.70$)에서 고해상도 원본 뷰로 자연스럽게 알파 블렌딩 스위칭.
  - 확대 감상(Hold 1.5초): **100% 원본 고해상도 이미지 프레임 직접 송출**로 원본 디테일 완벽 보존.
  - 줌아웃 구간: 고해상도 뷰에서 줌아웃을 개시한 뒤 중간 지점($0.30 \le t \le 0.65$)에서 매트릭스 뷰로 매끄럽게 크로스페이드 복귀.
- **검증 결과**:
  - Pytest 8개 테스트 스위트 전원 통과 (`8 passed in 21.41s`).
  - H.264 1080p 고화질 렌더링 무결성 및 선명도 대폭 개선 확인.

### 2. 작성 산출물
- `notes/req_202610142136.md`: 사용자 원본 요구사항 및 계획 기록
- `notes/result_202610142136.md`: 개발 결과 및 검증 상세 보고서

---

## [2026-10-14 21:09] 표준 해상도 1080p 및 720p~1920p 다중 해상도 지원, 밝고 경쾌한 BGM 5곡 전면 개편

### 1. 개발 내용 요약
- **표준 1080p 및 다중 해상도 선택 옵션 구현**:
  - 기본 표준 해상도를 **1080p Full HD (1920x1080)**로 격상.
  - 최소 `720p` (1280x720), `1080p` (표준 기본값), `1440p` (2560x1440), 최대 `1920p` (3414x1920) 4가지 해상도 선택 옵션 지원.
  - 해상도별 적응형 상한 비트레이트 제어(`-maxrate 2500k` ~ `10000k`)로 100MB 및 10분 상한 제약 준수.
  - `grid_calculator.py` 캔버스 해상도 비례 스케일링 적용.
- **밝고 경쾌한 무료 BGM 프리셋 5곡 전면 개편**:
  - 기존의 단조롭고 차가운 음원을 DB 및 디스크에서 완전 제거/대체.
  - 장조(Major Key) 기반 화음과 경쾌한 리듬을 가진 5곡의 저작권 무료 번들 음원 자동 적재:
    1. `preset-sunny-morning`: Sunny Morning Walk (Acoustic Bright)
    2. `preset-joyful-ukulele`: Upbeat Joyful Ukulele (Ukulele & Pop)
    3. `preset-energy-dance`: Bright Energy Dance (Synth Pop)
    4. `preset-happy-breeze`: Happy Acoustic Breeze (Folk Acoustic)
    5. `preset-summer-smile`: Playful Summer Smile (Marimba & Percussion)
- **UI 및 API 연동**:
  - 웹 대시보드 내 "합성 화질 (해상도 선택)" 라디오 버튼 그룹 추가 (1080p 기본 선택).
  - 작업 생성 API (`POST /jobs`)에 `resolution` 파라미터 및 유효성 검증 추가.
  - SQLite `jobs` 테이블 `resolution` 컬럼 자동 마이그레이션 적용.
- **검증 결과**:
  - Pytest 8개 테스트 스위트 전원 통과 (`8 passed in 15.62s`).
  - 실제 생성 비디오 ffprobe 검증: `1920x1080`, `30fps`, `H.264/AAC` (약 104KB, 9.5초) 확인.

### 2. 작성 산출물
- `notes/req_202610142109.md`: 사용자 원본 요구사항 및 계획 기록
- `notes/result_202610142109.md`: 개발 결과 및 검증 상세 보고서

---

## [2026-10-14 20:50] 시스템 전체 구현 및 종합 E2E 테스트 검증 완료

### 1. 개발 내용 요약
- **실행 환경 및 바이너리 구축**:
  - `./bin/ffmpeg.exe`, `./bin/ffprobe.exe` 배치 및 검증
  - Python 가상환경(`.venv`) 및 의존성 패키지 설치
  - `.env` 기반 설정 및 `storage/uploads`, `storage/bgm`, `storage/transcoded` 디렉토리 자동 초기화
- **핵심 엔진 구현**:
  - `grid_calculator.py`: 최대 49장 $N \times M$ ($M=N$ or $N=M \pm 1$) 최적 그리드 및 셀 좌표 계산기
  - `video_synthesizer.py`: 코사인 Ease-in-out 줌인/줌아웃 트랜지션 및 720p 30fps FFmpeg 파이프라인
  - `audio_mixer.py`: BGM 오디오 길이 추출, 무한 루프 및 종료 페이드아웃 필터
  - `bgm_manager.py`: 관리자 BGM 음원 등록, 오디오 스트리밍, 3곡의 프리셋 자동 시딩
  - `task_queue.py`: `asyncio.Semaphore(3)` 기반 최대 3개 동시 합성 워커 풀 및 작업 상태 관리
  - `stream_manager.py`: 최대 10개 동시 스트리밍 슬롯 제어 및 HTTP 206 Partial Content (Range) 스트리밍
- **RESTful API & 웹 대시보드 UI**:
  - Base Prefix `/fotostream`, Port `5000` 마운트
  - Tailwind CSS 기반 모던 다크 테마 대시보드 (`/fotostream`)
  - 최대 49장 사진 드래그앤드롭 업로드, BGM 미리듣기/선택/등록 모달, 실시간 작업 큐 모니터링, HTML5 비디오 스트리밍 플레이어 팝업
- **종합 검증 결과**:
  - Pytest 8개 테스트 스위트 전원 통과 (`8 passed in 10.86s`)
  - 실제 720p mp4 비디오 생성 및 HTTP 206 Range 스트리밍 및 동시 10개 초과 시 429 에러 완벽 검증

### 2. 생성 산출물
- `notes/req_202610142050.md`: 개발 착수 원본 요구사항 및 계획 기록
- `notes/result_202610142050.md`: 전체 구현 산출물 및 테스트 검증 보고서

---

## [2026-10-14 20:46] 무료 BGM 라이브러리(Pixabay Music 등) 지원 및 선택 UI 요구사항 확장

### 1. 요구사항 요약
- **배경**: 동영상 제작 시 배경음악 품질 및 편의성을 극대화하기 위해, 무료 BGM 사이트(예: Pixabay Music)에서 다운로드한 음원을 서버에 선행 등록하고 사용자가 리스트에서 선택할 수 있는 파이프라인 요구.
- **주요 기능 추가**:
  1. 관리자 BGM 선행 등록 기능 (BGM 파일 업로드, 곡명, 무드, 라이선스 정보, `storage/bgm/` 보관).
  2. 사용자 BGM 선택 UI 및 브라우저 실시간 오디오 미리듣기(Preview Play) 지원.
  3. 번들 프리셋 BGM 음원 자동 시딩 (초기 구동 시 저작권 무료 3~4곡 적재).
  4. 비디오 합성 엔진 연계: 작업 큐 요청 시 `bgm_id` 참조를 통해 동영상에 해당 음원 자동 합성(루프 및 페이드아웃).
  5. BGM 관리 RESTful API: 목록 조회, 등록, 미리듣기 스트리밍, 삭제 (`/fotostream/api/v1/bgm`).

### 2. 갱신 및 신규 작성 산출물
- `GOAL.md`: BGM 라이브러리 연동 및 사용자 선택 목표 반영 갱신
- `notes/requirement.md`: [FR-09] 무료 BGM 라이브러리 관리 및 선택 파이프라인 누적 추가
- `notes/SPECIFICATION.md`: BGM 아키텍처, DB 스키마(`bgm_tracks`), API 및 UI 명세 갱신
- `notes/plan_202610142046.md`: BGM 지원 통합 MVP 정의 및 8대 개발 마일스톤 수립
- `notes/req_202610142046.md`: BGM 추가 사용자 원본 요구사항 및 구현 계획 기록
- `notes/result_202610142046.md`: BGM 요구사항 반영 산출물 생성 결과 보고서

---

## [2026-10-14 20:28] 초기 요구사항 분석 및 프로젝트 개발 계획 수립

### 1. 요구사항 요약
- **목적**: 최대 49장의 사진을 $N \times M$ 그리드 줌인/줌아웃 트랜지션 효과를 가진 720p 동영상으로 합성하고, BGM을 믹싱하여 관리 및 스트리밍하는 시스템 개발.
- **주요 기능**:
  1. 포토 이미지 최대 49장 다중 업로드 및 BGM 선택/업로드.
  2. $N \times M$ ($M=N$ 또는 $N = M \pm 1$) 그리드 계산 및 줌인-감상-줌아웃 시퀀스 비디오 합성.
  3. 합성 비디오 규격: 최대 720p(1280x720), 최대 파일 크기 100MB 이하, 최대 재생 시간 10분(600초) 이하.
  4. 비동기 백그라운드 작업 큐 운영: 동시 합성 작업 최대 $N \le 3$개 제어.
  5. 비디오 스트리밍 엔드포인트 URL 제공: HTTP Range Request 기반, 동시 스트리밍 최대 $M = 10$개 세션 제어.
  6. 웹 대시보드 데모 UI 제공: 기본 URL Prefix `/fotostream`, 포트 `5000`, 드래그 앤 드롭 업로드, 실시간 큐 모니터링, 비디오 재생 및 목록 관리.
  7. 환경변수 기반 시스템 설정 (`.env`): `FFMPEG_PATH=./bin/ffmpeg.exe`, `FFPROBE_PATH=./bin/ffprobe.exe` 등.

### 2. 작성 산출물
- `GOAL.md`: 프로젝트 구현 목적 및 목표, 시스템 전체 요약
- `notes/requirement.md`: 기능적(FR)/비기능적(NFR) 상세 요구사항 및 RTM
- `notes/SPECIFICATION.md`: 패키지 구조, DB 스키마, 모듈 설계, API 명세, 제약사항
- `notes/plan_202610142028.md`: MVP 정의 및 단계별 7대 마일스톤 개발 계획
- `notes/req_202610142028.md`: 사용자 원본 요청문 및 세부 계획 매핑
- `notes/result_202610142028.md`: 산출물 생성 확인 및 검증 기록
