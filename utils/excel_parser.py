import pandas as pd

# 엑셀 구조:
#   행 23(0-indexed) = 컬럼 헤더
#   행 24~27         = 메타데이터(정의·타입·길이·Not_Null) → 건너뜀
#   행 28+           = 실제 데이터 ('DATA' 레이블로 시작, 이후 NaN)

HEADER_ROW = 23


def _read_sheet(xl, sheet_name):
    """
    시트를 읽어 실제 데이터 행만 반환.
    첫 번째 'DATA' 레이블 행부터 시작하고, 상품코드(또는 첫 PK 컬럼)가 있는 행만 남긴다.
    """
    try:
        df = xl.parse(sheet_name, header=HEADER_ROW)
    except Exception:
        return pd.DataFrame()

    # 'DATA' 레이블이 있는 행 위치 찾기
    data_mask = df["Unnamed: 0"] == "DATA"
    if not data_mask.any():
        return pd.DataFrame()

    start_idx = data_mask.idxmax()
    data = df.loc[start_idx:].drop(columns=["Unnamed: 0"], errors="ignore").copy()

    # 첫 번째 컬럼(상품코드)이 있는 행만 유지
    first_col = data.columns[0]
    data = data[data[first_col].notna()].reset_index(drop=True)
    return data


def _safe_str(val):
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except Exception:
        pass
    return str(val).strip() or None


def _safe_num(val):
    try:
        if pd.isna(val):
            return None
        return float(val)
    except Exception:
        return None


def parse_product(xl):
    """상품 시트 → dict"""
    df = _read_sheet(xl, "상품")
    if df.empty:
        return None

    row = df.iloc[0]
    return {
        "상품코드":         _safe_str(row.get("상품코드")),
        "상품판매명":       _safe_str(row.get("상품판매명")),
        "상품인가명":       _safe_str(row.get("상품인가명")),
        "상품단축명":       _safe_str(row.get("상품단축명")),
        "보험종목코드":     _safe_str(row.get("보종군코드")),    # LA/CA/FA 등
        "상품형태구분코드": _safe_str(row.get("상품형태구분코드")),
        "자동갱신가능여부": _safe_str(row.get("자동갱신가능여부")),  # '0'/'1'
        "상품최대가입연령": _safe_num(row.get("상품최대가입연령")),
        "보험기간기본값":   _safe_str(row.get("보험기간기본값")),
        "진단상품여부":     _safe_str(row.get("진단상품여부")),
        "적용시작일자":     _safe_str(row.get("적용시작일자")),
        "적용종료일자":     _safe_str(row.get("적용종료일자")),
    }


def parse_coverages(xl):
    """상품담보 시트 → list of dict"""
    df = _read_sheet(xl, "상품담보")
    if df.empty:
        return []

    results = []
    for _, row in df.iterrows():
        results.append({
            "상품코드":             _safe_str(row.get("상품코드")),
            "담보코드":             _safe_str(row.get("담보코드")),
            "담보대표명":           _safe_str(row.get("담보대표명")),
            "담보한글명":           _safe_str(row.get("담보한글명")),
            "담보한글단축명":       _safe_str(row.get("담보한글단축명")),
            "담보기본특약구분코드": _safe_str(row.get("담보기본특약구분코드")),
            "가입대상여부":         _safe_str(row.get("가입대상여부")),
            "가입금액필요여부":     _safe_str(row.get("가입금액필요여부")),
            "적용시작일자":         _safe_str(row.get("적용시작일자")),
            "적용종료일자":         _safe_str(row.get("적용종료일자")),
        })
    return results


def parse_excel_file(filepath):
    """
    엑셀 파일 하나를 파싱해 상품 정보와 담보 목록을 반환.
    반환: {"product": dict, "coverages": list, "error": str|None}
    """
    try:
        xl = pd.ExcelFile(filepath, engine="xlrd")
    except Exception as e:
        return {"product": None, "coverages": [], "error": f"파일 열기 실패: {e}"}

    product = parse_product(xl)
    if product is None or not product.get("상품코드"):
        return {"product": None, "coverages": [], "error": "상품코드를 찾을 수 없습니다"}

    coverages = parse_coverages(xl)
    return {"product": product, "coverages": coverages, "error": None}
