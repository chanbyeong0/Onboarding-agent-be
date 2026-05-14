# Onboarding Agent Backend

사내 신입사원 온보딩을 위한 AI 에이전트 FastAPI 백엔드입니다.
문서 업로드, 체크포인트 저장, OpenAI 기반 SSE 채팅 응답을 제공합니다.

## 주요 기능

- JWT access token 및 localStorage 기반 refresh token 세션
- PDF/PPT/PPTX 문서 업로드와 텍스트 추출
- 사용자가 모르는 항목 체크포인트 저장
- OpenAI Chat Completions 스트리밍을 SSE로 중계
- MongoDB 단일 저장소와 Beanie ODM 사용
- RAG 인터페이스는 TODO 스텁으로 분리

## 실행 준비

```bash
cp .env.example .env
```

`.env`에서 최소한 다음 값을 설정합니다.

```env
MONGODB_URL=mongodb://root:example@mongo:27017
MONGODB_DB_NAME=onboarding
OPENAI_API_KEY=
JWT_SECRET_KEY=
```

## Docker Compose

DB와 Mongo Express는 별도 compose로 실행합니다.

```bash
docker compose -f docker-compose.db.yml up -d
```

백엔드 앱은 별도 compose로 실행합니다.

```bash
docker compose up -d --build
```

API 서버는 기본적으로 `http://localhost:8000`에서 접근합니다.
헬스체크는 `GET /health`입니다.

## 로컬 개발

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 폴더 아키텍처

```text
app/
├── main.py                 # FastAPI 앱 생성, CORS, lifespan, 라우터 등록
├── core/                   # 환경설정과 보안 유틸
├── api/                    # API 의존성과 버전별 라우터
│   └── v1/endpoints/       # users, document, checkpoint, chat 엔드포인트
├── models/                 # Beanie Document 모델
├── schemas/                # Pydantic 요청/응답 스키마
├── crud/                   # MongoDB 접근을 감싼 얇은 데이터 접근 계층
├── services/               # 문서 처리, OpenAI 호출 등 비즈니스 로직
├── rag/                    # RAG 인터페이스 스텁
└── db/                     # MongoDB 연결, Beanie 초기화, 벡터 컬렉션 접근
tests/                      # API와 RAG 인터페이스 테스트
```

### 계층별 책임

- `api`: HTTP 요청/응답, 인증 의존성, `HTTPException` 변환을 담당합니다.
- `schemas`: 외부 입출력 계약을 정의합니다. Mongo ObjectId는 응답에서 문자열로 노출합니다.
- `models`: MongoDB 컬렉션 구조와 인덱스를 정의합니다.
- `crud`: Beanie 쿼리 세부사항을 캡슐화합니다. 엔드포인트에서 직접 `find_one`, `insert`를 반복하지 않습니다.
- `services`: 파일 저장, PDF/PPT 파싱, OpenAI 스트리밍처럼 여러 단계가 필요한 업무 흐름을 담당합니다.
- `rag`: 현재는 TODO 인터페이스입니다. 실제 임베딩/검색 구현은 이 패키지 내부에서 확장합니다.
- `db`: 애플리케이션 시작 시 MongoDB 클라이언트와 Beanie 모델을 초기화합니다.

### 요청 흐름

```text
Client
  -> api/v1/endpoints
  -> schemas로 요청 검증
  -> deps로 인증 사용자 조회
  -> services 또는 crud 호출
  -> models/Beanie로 MongoDB 접근
  -> schemas 형태로 응답
```

채팅은 `POST /api/v1/chat`에서 `EventSourceResponse`를 반환합니다. `agent_service.stream_chat()`이 OpenAI 스트림을 읽고 `ChatStreamEvent`를 SSE data로 변환합니다.

## 협업자를 위한 구현 가이드

### 새 API를 추가할 때

1. 요청/응답 스키마를 `app/schemas/`에 먼저 정의합니다.
2. Mongo 컬렉션이 필요하면 `app/models/`에 Beanie `Document`를 추가합니다.
3. DB 접근 함수는 `app/crud/`에 작성합니다.
4. 여러 단계를 조합하는 비즈니스 로직은 `app/services/`에 둡니다.
5. 엔드포인트는 `app/api/v1/endpoints/`에 만들고 `app/api/v1/router.py`에 등록합니다.
6. 보호 API라면 `Depends(get_current_user)`를 사용합니다.
7. 테스트는 `tests/`에 추가합니다.

### 인증 구현 규칙

- Access token은 `Authorization: Bearer <token>`으로 전달됩니다.
- Refresh token은 로컬 개발 전용으로 프론트 localStorage에 저장됩니다.
- `refresh_tokens` 컬렉션에는 refresh JWT의 `jti`를 저장해 로그아웃 시 폐기할 수 있게 합니다.
- 보호 API는 `type == "access"` 토큰만 허용합니다.
- Refresh API는 `type == "refresh"` 토큰만 허용합니다.

### 문서 업로드 구현 규칙

- 업로드 파일 저장과 파싱은 `document_service.py`에서 처리합니다.
- 지원 확장자는 `pdf`, `ppt`, `pptx`입니다.
- PDF 파싱은 `pdfplumber`, PPT/PPTX 파싱은 `python-pptx`를 사용합니다.
- 청크 크기 기본값은 `500`, overlap 기본값은 `50`입니다.
- 실제 RAG 색인은 아직 TODO입니다. `rag.pipeline.index_chunks()` 호출 위치만 주석으로 남겨두었습니다.

### RAG 구현 예정 위치

- `rag/embedder.py`: 텍스트 임베딩 생성
- `rag/retriever.py`: MongoDB 벡터 검색
- `rag/pipeline.py`: 색인과 검색 흐름 조합
- `db/vector_store.py`: 벡터 컬렉션 접근과 추후 Atlas Vector Search 인덱스 관리

RAG 구현 시 엔드포인트가 직접 벡터 검색을 호출하지 않도록 하고, `agent_service` 또는 `document_service`에서 `rag.pipeline`만 호출하도록 유지합니다.

### 주석과 코드 스타일

- 모듈 최상단에는 한국어 docstring으로 역할을 적습니다.
- 공개 함수에는 Args/Returns/Raises 중심의 한국어 docstring을 작성합니다.
- 다른 서비스/CRUD/외부 API/파일 I/O를 호출하는 라인 앞에는 “왜 호출하는지”를 설명하는 한 줄 한국어 주석을 둡니다.
- 단순히 코드를 반복 설명하는 주석은 피합니다.
- TODO는 `# TODO: 추후 구현 - 설명` 형식을 사용합니다.

## API 개요

- `POST /api/v1/users/register`
- `POST /api/v1/users/login`
- `POST /api/v1/users/refresh`
- `POST /api/v1/users/logout`
- `GET /api/v1/users/me`
- `POST /api/v1/documents/upload`
- `GET /api/v1/documents`
- `GET /api/v1/documents/{document_id}`
- `POST /api/v1/checkpoints`
- `GET /api/v1/checkpoints/me`
- `POST /api/v1/chat`

## 테스트

```bash
pytest
```

현재 RAG 구현은 의도적으로 `NotImplementedError`를 발생시키는 인터페이스만 제공합니다.
