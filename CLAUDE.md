# 보험 상품 관리 챗봇 웹앱

## 프로젝트 개요
보험회사 상품 관리팀이 사용하는 내부 웹 애플리케이션.
엑셀로 관리하던 보험 상품 데이터를 DB에 적재하고,
팀원 누구나 챗봇으로 상품 정보를 쉽게 조회할 수 있게 한다.

## 개발 배경
- 바이브코딩 경진대회 제출용 (초보자 부문)
- 개발자가 아닌 상품 관리직 팀장이 Claude Code로 제작
- 목표: 업무 효율성 + 기본에 충실한 결과물

## 기술 스택
- **백엔드**: Python 3.11 + Flask
- **데이터베이스**: PostgreSQL (Render.com 제공 무료 DB)
- **AI 챗봇**: Google Gemini API (gemini-1.5-flash, 무료 티어)
- **프론트엔드**: HTML + CSS + JavaScript (순수 바닐라, 프레임워크 없음)
- **배포**: Render.com (무료 플랜)
- **엑셀 파싱**: pandas + openpyxl

## 핵심 기능

### 1. 엑셀 업로드
- 수십 개의 엑셀 파일을 업로드
- 자동으로 DB 테이블에 적재
- 상품코드를 기준으로 파일 간 데이터 연결

### 2. 상품 조회 화면
- 상품코드 / 상품명으로 검색
- 상품 기본속성 표시
- 해당 상품의 담보 목록 및 보장내용 표시

### 3. AI 챗봇
- 팀원이 자연어로 질문 입력
- DB에서 관련 데이터 검색 후 Gemini에 전달
- Gemini가 자연어로 답변 생성
- 전체 데이터를 AI에 보내지 않고 관련 데이터만 검색해서 전달 (토큰 절약)

## 데이터 구조

### 엑셀 파일 구조 (분석 완료)
- 파일당 상품코드 1개, 23개 파일 = 23개 상품 (단, 동일 상품 다른 종 포함)
- 모든 파일은 **55개 시트** 동일 구조
- **파싱 핵심**: `header=23`, DATA 레이블 행부터 시작, 이후 NaN 행도 유효 데이터
- 주요 시트:
  - `상품` : 113개 컬럼, 상품 기본속성
  - `상품담보` : 77개 컬럼, 담보 목록 (상품당 30~2,284개)
- 상품코드 형태: `LA02944001` (보종군코드 2자리 + 상품번호 5자리 + 종코드 3자리)
- `자동갱신가능여부` 값: '1'(갱신) / '0'(비갱신)
- `담보기본특약구분코드` 값: '01'(기본) / '02'(특약) / '03'(특별약관)

### DB 테이블 구조 (확정)
- `products` : 상품 기본 정보 (상품코드 PK, 13개 주요 컬럼)
- `coverages` : 담보 정보 (상품코드 FK, 10개 컬럼, 인덱스 있음)
- `file_upload_log` : 업로드 이력 관리

## 개발 원칙
- 코드는 단순하고 읽기 쉽게 (복잡한 추상화 금지)
- 에러 발생 시 사용자에게 친절한 한국어 메시지 표시
- 모바일보다 PC 브라우저 최적화
- 보안: API 키는 환경변수로 관리, 코드에 직접 입력 금지

## 배포 환경
- **플랫폼**: Render.com
- **무료 플랜 제약**: 15분 미사용 시 슬립 모드 진입 (첫 접속 시 30초 대기 가능)
- **환경변수 설정 필요**:
  - `DATABASE_URL` : Render PostgreSQL 연결 문자열
  - `GEMINI_API_KEY` : Google Gemini API 키

## 프로젝트 구조
```
바이브코딩_도전/
├── CLAUDE.md
├── app.py                  # Flask 메인 앱 (라우팅 전체)
├── requirements.txt
├── render.yaml             # Render 배포 설정
├── .env                    # 환경변수 (로컬용, Git 제외)
├── .gitignore
├── templates/
│   ├── base.html           # 공통 레이아웃 (navbar)
│   ├── index.html          # 홈 (카드 4개)
│   ├── upload.html         # 엑셀 업로드 + 이력 테이블
│   ├── upload_result.html  # 업로드 결과
│   ├── products.html       # 상품 목록/검색
│   ├── product_detail.html # 상품 상세 + 담보 필터
│   ├── compare.html        # 정합성 비교 (두 상품 담보 비교)
│   └── chat.html           # AI 챗봇
├── static/
│   └── style.css
└── utils/
    ├── __init__.py
    ├── db.py               # DB 연결·쿼리·정합성 비교
    ├── excel_parser.py     # 엑셀 파싱 (header=23 기준)
    └── gemini_chat.py      # Gemini API 연동
```

## 작업 진행 상황
- [x] 프로젝트 기획 확정
- [x] CLAUDE.md 작성
- [x] 엑셀 파일 구조 분석 및 DB 스키마 확정
- [x] 개발 환경 세팅 (requirements.txt, .gitignore, render.yaml)
- [x] 백엔드 개발 (app.py, utils/)
- [x] 프론트엔드 개발 (templates, style.css)
- [x] Gemini 챗봇 연동 (gemini_chat.py)
- [x] 정합성 비교 기능 개발 (compare.html, /api/compare)
- [ ] Render DB 연결 및 환경변수 설정
- [ ] Render 배포
- [ ] 테스트 및 최종 점검
