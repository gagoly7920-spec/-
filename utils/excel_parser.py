import xlrd

# 엑셀 구조:
#   행 23(0-indexed) = 컬럼 헤더
#   행 24~27         = 메타데이터 → 건너뜀
#   행 28+           = 실제 데이터 ('DATA' 레이블로 시작, 이후 빈 값)

HEADER_ROW = 23


def _cell(value):
    """xlrd 셀 값을 문자열로 변환, 빈 값은 None"""
    if value is None:
        return None
    s = str(value).strip()
    # xlrd가 숫자를 float으로 읽는 경우 처리 (예: '1.0' → '1')
    if s.endswith('.0') and s[:-2].lstrip('-').isdigit():
        s = s[:-2]
    return s or None


def _num(value):
    """숫자 변환, 실패하면 None"""
    try:
        v = float(value)
        return v if v == v else None  # NaN 체크
    except Exception:
        return None


def _read_sheet(wb, sheet_name):
    """
    시트를 읽어 컬럼명 dict와 데이터 행 목록 반환.
    반환: (col_map, rows)
      col_map: {컬럼명: 인덱스}
      rows: list of list (실제 데이터 행들)
    """
    try:
        ws = wb.sheet_by_name(sheet_name)
    except Exception:
        return {}, []

    if ws.nrows <= HEADER_ROW:
        return {}, []

    # 컬럼명 맵 (행 23)
    header = ws.row_values(HEADER_ROW)
    col_map = {}
    for i, name in enumerate(header):
        name = str(name).strip()
        if name and name not in col_map:
            col_map[name] = i

    # DATA 레이블 행 찾기 (첫 번째 컬럼 기준)
    first_col = 0  # Unnamed: 0 위치
    data_start = None
    for row_idx in range(HEADER_ROW + 1, ws.nrows):
        val = str(ws.cell_value(row_idx, first_col)).strip()
        if val == 'DATA':
            data_start = row_idx
            break

    if data_start is None:
        return col_map, []

    # DATA 행부터 끝까지, 두 번째 컬럼(상품코드)이 있는 행만 수집
    rows = []
    pk_col = 1  # 상품코드는 항상 두 번째 컬럼
    for row_idx in range(data_start, ws.nrows):
        pk_val = str(ws.cell_value(row_idx, pk_col)).strip()
        if pk_val and pk_val != 'nan':
            rows.append(ws.row_values(row_idx))

    return col_map, rows


def _get(row, col_map, name):
    """col_map에서 컬럼 인덱스 찾아 값 반환"""
    idx = col_map.get(name)
    if idx is None or idx >= len(row):
        return None
    return _cell(row[idx])


def parse_product(wb):
    """상품 시트 → dict"""
    col_map, rows = _read_sheet(wb, '상품')
    if not rows:
        return None

    row = rows[0]
    return {
        '상품코드':         _get(row, col_map, '상품코드'),
        '상품판매명':       _get(row, col_map, '상품판매명'),
        '상품인가명':       _get(row, col_map, '상품인가명'),
        '상품단축명':       _get(row, col_map, '상품단축명'),
        '보험종목코드':     _get(row, col_map, '보종군코드'),
        '상품형태구분코드': _get(row, col_map, '상품형태구분코드'),
        '자동갱신가능여부': _get(row, col_map, '자동갱신가능여부'),
        '상품최대가입연령': _num(row[col_map['상품최대가입연령']] if '상품최대가입연령' in col_map else None),
        '보험기간기본값':   _get(row, col_map, '보험기간기본값'),
        '진단상품여부':     _get(row, col_map, '진단상품여부'),
        '적용시작일자':     _get(row, col_map, '적용시작일자'),
        '적용종료일자':     _get(row, col_map, '적용종료일자'),
    }


def parse_coverages(wb):
    """상품담보 시트 → list of dict"""
    col_map, rows = _read_sheet(wb, '상품담보')
    if not rows:
        return []

    results = []
    for row in rows:
        results.append({
            '상품코드':             _get(row, col_map, '상품코드'),
            '담보코드':             _get(row, col_map, '담보코드'),
            '담보대표명':           _get(row, col_map, '담보대표명'),
            '담보한글명':           _get(row, col_map, '담보한글명'),
            '담보한글단축명':       _get(row, col_map, '담보한글단축명'),
            '담보기본특약구분코드': _get(row, col_map, '담보기본특약구분코드'),
            '가입대상여부':         _get(row, col_map, '가입대상여부'),
            '가입금액필요여부':     _get(row, col_map, '가입금액필요여부'),
            '적용시작일자':         _get(row, col_map, '적용시작일자'),
            '적용종료일자':         _get(row, col_map, '적용종료일자'),
        })
    return results


def parse_excel_file(filepath):
    """
    엑셀 파일 하나를 파싱해 상품 정보와 담보 목록을 반환.
    반환: {"product": dict, "coverages": list, "error": str|None}
    """
    try:
        wb = xlrd.open_workbook(filepath)
    except Exception as e:
        return {"product": None, "coverages": [], "error": f"파일 열기 실패: {e}"}

    product = parse_product(wb)
    if product is None or not product.get('상품코드'):
        return {"product": None, "coverages": [], "error": "상품코드를 찾을 수 없습니다"}

    coverages = parse_coverages(wb)
    return {"product": product, "coverages": coverages, "error": None}
