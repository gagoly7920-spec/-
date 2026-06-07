import os
import tempfile
from flask import Flask, request, render_template, redirect, url_for, jsonify, flash
from dotenv import load_dotenv

from utils.db import (
    init_db, search_products, get_product, get_coverages,
    get_all_products, get_upload_log, search_for_chat, compare_coverages
)
from utils.excel_parser import parse_excel_file
from utils.gemini_chat import ask, build_context

import psycopg2
import psycopg2.extras

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")

# ── 초기화 ────────────────────────────────────────────────

@app.before_request
def ensure_db():
    """최초 요청 시 테이블 생성"""
    if not getattr(app, "_db_initialized", False):
        try:
            init_db()
            app._db_initialized = True
        except Exception as e:
            print(f"DB 초기화 오류: {e}")


# ── 메인 ──────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── 엑셀 업로드 ───────────────────────────────────────────

@app.route("/upload", methods=["GET"])
def upload():
    logs = get_upload_log()
    return render_template("upload.html", logs=logs)


@app.route("/api/upload_single", methods=["POST"])
def upload_single():
    """파일 1개를 받아 처리 후 JSON 반환 (프론트에서 진행 바 제어용)"""
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"success": False, "message": "파일 없음"})

    fname = f.filename
    suffix = ".xls" if fname.endswith(".xls") else ".xlsx"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        f.save(tmp.name)
        tmp_path = tmp.name

    try:
        parsed = parse_excel_file(tmp_path)
    finally:
        os.unlink(tmp_path)

    if parsed["error"]:
        _log_upload(fname, False, parsed["error"])
        return jsonify({"success": False, "message": parsed["error"], "파일명": fname})

    product  = parsed["product"]
    coverages = parsed["coverages"]
    product_code = product["상품코드"]

    try:
        from utils.db import get_conn
        conn = get_conn()
        cur  = conn.cursor()

        cur.execute("""
            INSERT INTO products
                (상품코드, 상품판매명, 상품인가명, 상품단축명, 보험종목코드,
                 상품형태구분코드, 자동갱신가능여부, 상품최대가입연령,
                 보험기간기본값, 진단상품여부, 적용시작일자, 적용종료일자,
                 판매시작일자, 판매종료일자, 파일명)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (상품코드) DO UPDATE SET
                상품판매명      = EXCLUDED.상품판매명,
                상품인가명      = EXCLUDED.상품인가명,
                상품단축명      = EXCLUDED.상품단축명,
                보험종목코드    = EXCLUDED.보험종목코드,
                상품형태구분코드 = EXCLUDED.상품형태구분코드,
                자동갱신가능여부 = EXCLUDED.자동갱신가능여부,
                상품최대가입연령 = EXCLUDED.상품최대가입연령,
                보험기간기본값  = EXCLUDED.보험기간기본값,
                진단상품여부    = EXCLUDED.진단상품여부,
                적용시작일자    = EXCLUDED.적용시작일자,
                적용종료일자    = EXCLUDED.적용종료일자,
                판매시작일자    = EXCLUDED.판매시작일자,
                판매종료일자    = EXCLUDED.판매종료일자,
                파일명          = EXCLUDED.파일명,
                업로드일시      = NOW()
        """, (
            product_code,
            product["상품판매명"], product["상품인가명"], product["상품단축명"],
            product["보험종목코드"], product["상품형태구분코드"],
            product["자동갱신가능여부"], product["상품최대가입연령"],
            product["보험기간기본값"], product["진단상품여부"],
            product["적용시작일자"], product["적용종료일자"],
            product["판매시작일자"], product["판매종료일자"], fname
        ))

        cur.execute("DELETE FROM coverages WHERE 상품코드 = %s", (product_code,))
        if coverages:
            psycopg2.extras.execute_values(cur, """
                INSERT INTO coverages
                    (상품코드, 담보코드, 담보대표명, 담보한글명, 담보한글단축명,
                     담보기본특약구분코드, 가입대상여부, 가입금액필요여부,
                     적용시작일자, 적용종료일자)
                VALUES %s
            """, [(
                product_code,
                cov["담보코드"], cov["담보대표명"], cov["담보한글명"],
                cov["담보한글단축명"], cov["담보기본특약구분코드"],
                cov["가입대상여부"], cov["가입금액필요여부"],
                cov["적용시작일자"], cov["적용종료일자"]
            ) for cov in coverages], page_size=500)

        cur.execute("""
            INSERT INTO file_upload_log (파일명, 상품코드, 상품판매명, 담보수, 성공여부)
            VALUES (%s,%s,%s,%s,%s)
        """, (fname, product_code, product["상품판매명"], len(coverages), True))

        conn.commit()
        return jsonify({
            "success": True,
            "파일명": fname,
            "상품코드": product_code,
            "상품판매명": product["상품판매명"],
            "담보수": len(coverages),
            "message": f"{product['상품판매명']} — 담보 {len(coverages)}개"
        })

    except Exception as e:
        if conn: conn.rollback()
        _log_upload(fname, False, str(e))
        return jsonify({"success": False, "message": str(e), "파일명": fname})
    finally:
        if conn: conn.close()


def _log_upload(fname, success, error_msg=None):
    try:
        from utils.db import get_conn
        conn = get_conn()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO file_upload_log (파일명, 성공여부, 오류메시지)
            VALUES (%s,%s,%s)
        """, (fname, success, error_msg))
        conn.commit()
        conn.close()
    except Exception:
        pass




# ── 상품 목록/검색 ────────────────────────────────────────

@app.route("/products")
def products():
    keyword = request.args.get("q", "").strip()
    if keyword:
        items = search_products(keyword)
    else:
        items = get_all_products()
    return render_template("products.html", items=items, keyword=keyword)


@app.route("/products/<product_code>")
def product_detail(product_code):
    product = get_product(product_code)
    if not product:
        flash("해당 상품을 찾을 수 없습니다.", "error")
        return redirect(url_for("products"))
    coverages = get_coverages(product_code)
    return render_template("product_detail.html", product=product, coverages=coverages)


# ── 정합성 비교 ───────────────────────────────────────────

@app.route("/compare")
def compare():
    all_products = get_all_products()
    return render_template("compare.html", all_products=all_products)


@app.route("/api/compare")
def api_compare():
    code_a = request.args.get("a", "")
    code_b = request.args.get("b", "")
    if not code_a or not code_b:
        return jsonify({"error": "상품코드 두 개가 필요합니다"}), 400
    result = compare_coverages(code_a, code_b)
    prod_a = get_product(code_a)
    prod_b = get_product(code_b)
    return jsonify({
        "product_a": {"코드": code_a, "명": prod_a["상품판매명"] if prod_a else ""},
        "product_b": {"코드": code_b, "명": prod_b["상품판매명"] if prod_b else ""},
        "only_a": result["only_a"],
        "only_b": result["only_b"],
        "common_count": len(result["common"]),
    })


# ── 챗봇 ──────────────────────────────────────────────────

@app.route("/chat")
def chat():
    return render_template("chat.html")


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json()
    question = (data or {}).get("question", "").strip()
    if not question:
        return jsonify({"answer": "질문을 입력해주세요."}), 400

    # 키워드 추출 (간단히 질문 전체를 검색어로 사용)
    keyword = question
    search_result = search_for_chat(keyword)
    context_text = build_context(search_result)
    answer = ask(question, context_text)

    return jsonify({"answer": answer, "context": context_text})


if __name__ == "__main__":
    app.run(debug=True)
