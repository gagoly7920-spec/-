import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def init_db():
    """DB 테이블 초기 생성"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            상품코드        VARCHAR(10) PRIMARY KEY,
            상품판매명      TEXT,
            상품인가명      TEXT,
            상품단축명      TEXT,
            보험종목코드    VARCHAR(2),
            상품형태구분코드 VARCHAR(2),
            자동갱신가능여부 VARCHAR(1),
            상품최대가입연령 NUMERIC,
            보험기간기본값  TEXT,
            진단상품여부    VARCHAR(1),
            적용시작일자    VARCHAR(8),
            적용종료일자    VARCHAR(8),
            판매시작일자    VARCHAR(8),
            판매종료일자    VARCHAR(8),
            파일명          TEXT,
            업로드일시      TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS coverages (
            id              SERIAL PRIMARY KEY,
            상품코드        VARCHAR(10) REFERENCES products(상품코드) ON DELETE CASCADE,
            담보코드        VARCHAR(8),
            담보대표명      TEXT,
            담보한글명      TEXT,
            담보한글단축명  TEXT,
            담보기본특약구분코드 VARCHAR(2),
            가입대상여부    VARCHAR(1),
            가입금액필요여부 VARCHAR(1),
            적용시작일자    VARCHAR(8),
            적용종료일자    VARCHAR(8),
            독립특약여부    VARCHAR(1),
            독립특약상품코드 VARCHAR(10)
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_coverages_상품코드
            ON coverages(상품코드)
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS file_upload_log (
            id          SERIAL PRIMARY KEY,
            파일명      TEXT,
            상품코드    VARCHAR(10),
            상품판매명  TEXT,
            담보수      INTEGER,
            업로드일시  TIMESTAMP DEFAULT NOW(),
            성공여부    BOOLEAN,
            오류메시지  TEXT
        )
    """)
    # 기존 DB에 컬럼이 없을 경우 추가 (마이그레이션)
    for col in ['판매시작일자 VARCHAR(8)', '판매종료일자 VARCHAR(8)']:
        try:
            cur.execute(f"ALTER TABLE products ADD COLUMN IF NOT EXISTS {col}")
        except Exception:
            pass
    for col in ['독립특약여부 VARCHAR(1)', '독립특약상품코드 VARCHAR(10)']:
        try:
            cur.execute(f"ALTER TABLE coverages ADD COLUMN IF NOT EXISTS {col}")
        except Exception:
            pass
    conn.commit()
    cur.close()
    conn.close()


# ── 상품 조회 ──────────────────────────────────────────────

def search_products(keyword):
    """상품코드 또는 상품판매명으로 검색"""
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT 상품코드, 상품판매명, 상품인가명, 보험종목코드,
               자동갱신가능여부, 상품최대가입연령, 적용시작일자, 적용종료일자
          FROM products
         WHERE 상품코드 ILIKE %s OR 상품판매명 ILIKE %s
         ORDER BY 상품코드
         LIMIT 50
    """, (f"%{keyword}%", f"%{keyword}%"))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_product(product_code):
    """상품 기본 정보 단건 조회"""
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM products WHERE 상품코드 = %s", (product_code,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def get_coverages(product_code):
    """상품의 담보 목록 조회"""
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT 담보코드, 담보대표명, 담보한글명, 담보한글단축명,
               담보기본특약구분코드, 가입대상여부, 가입금액필요여부,
               적용시작일자, 적용종료일자
          FROM coverages
         WHERE 상품코드 = %s
         ORDER BY 담보기본특약구분코드, 담보코드
    """, (product_code,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_all_products():
    """전체 상품 목록 (목록 화면용)"""
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT p.상품코드, p.상품판매명,
               p.판매시작일자, p.판매종료일자,
               COUNT(c.id) AS 담보수
          FROM products p
          LEFT JOIN coverages c ON p.상품코드 = c.상품코드
         GROUP BY p.상품코드, p.상품판매명,
                  p.판매시작일자, p.판매종료일자
         ORDER BY p.상품코드
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_upload_log():
    """업로드 이력 조회"""
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT * FROM file_upload_log
         ORDER BY 업로드일시 DESC
         LIMIT 100
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


# ── 챗봇용 검색 ───────────────────────────────────────────

def search_for_chat(keyword):
    """챗봇 질의에서 관련 상품·담보 검색 (토큰 절약용)"""
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 상품 매칭
    cur.execute("""
        SELECT 상품코드, 상품판매명, 상품인가명, 보험종목코드,
               자동갱신가능여부, 상품최대가입연령, 보험기간기본값
          FROM products
         WHERE 상품코드 ILIKE %s OR 상품판매명 ILIKE %s OR 상품인가명 ILIKE %s
         LIMIT 5
    """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"))
    products = cur.fetchall()

    # 담보 매칭
    cur.execute("""
        SELECT c.상품코드, p.상품판매명,
               c.담보코드, c.담보대표명, c.담보한글명, c.담보기본특약구분코드
          FROM coverages c
          JOIN products p ON p.상품코드 = c.상품코드
         WHERE c.담보대표명 ILIKE %s OR c.담보한글명 ILIKE %s
         LIMIT 20
    """, (f"%{keyword}%", f"%{keyword}%"))
    coverages = cur.fetchall()

    cur.close()
    conn.close()
    return {"products": products, "coverages": coverages}


# ── 정합성 체크 ───────────────────────────────────────────

def compare_coverages(code_a, code_b):
    """두 상품의 담보 비교 (A에만 있는 담보 / B에만 있는 담보 / 공통)"""
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT 담보코드, 담보대표명, 담보기본특약구분코드
          FROM coverages WHERE 상품코드 = %s
    """, (code_a,))
    set_a = {r["담보코드"]: r for r in cur.fetchall()}

    cur.execute("""
        SELECT 담보코드, 담보대표명, 담보기본특약구분코드
          FROM coverages WHERE 상품코드 = %s
    """, (code_b,))
    set_b = {r["담보코드"]: r for r in cur.fetchall()}

    cur.close()
    conn.close()

    only_a = [set_a[k] for k in set_a if k not in set_b]
    only_b = [set_b[k] for k in set_b if k not in set_a]
    common = [set_a[k] for k in set_a if k in set_b]
    return {"only_a": only_a, "only_b": only_b, "common": common}
