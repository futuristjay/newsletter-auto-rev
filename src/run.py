import json, os, sys, re, time
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import HTTPError

KST = timezone(timedelta(hours=9))
NOW = datetime.now(KST)
DATE_STR = NOW.strftime("%Y-%m-%d")
DATE_KR = NOW.strftime("%Y년 %m월 %d일")

# ─────────────────────────────────────────
# FETCH HELPERS
# ─────────────────────────────────────────

def fetch(url, headers=None):
    try:
        h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        if headers:
            h.update(headers)
        r = urlopen(Request(url, headers=h), timeout=15)
        return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  fetch error {url[:60]}: {e}")
        return ""

def fetch_yf(ticker):
    """Yahoo Finance v8 chart API"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
    try:
        data = json.loads(fetch(url))
        result = data["chart"]["result"][0]
        meta = result["meta"]
        price = meta.get("regularMarketPrice") or meta.get("previousClose")
        prev  = meta.get("chartPreviousClose") or meta.get("previousClose")
        currency = meta.get("currency", "USD")
        chg   = round(price - prev, 4) if (price and prev) else None
        chg_p = round((price - prev) / prev * 100, 2) if (price and prev and prev != 0) else None
        return {
            "price": price, "prev": prev,
            "change": chg, "change_pct": chg_p,
            "currency": currency,
            "name": meta.get("shortName", ticker)
        }
    except Exception as e:
        print(f"  YF error {ticker}: {e}")
        return {"price": None, "prev": None, "change": None, "change_pct": None, "currency": "USD", "name": ticker}

def xnum(text, pats):
    for p in pats:
        m = re.search(p, text)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except:
                pass
    return None

# ─────────────────────────────────────────
# CLAUDE API
# ─────────────────────────────────────────

def ask(api_key, q, max_tokens=2000):
    msg = [{"role": "user", "content": q}]
    body = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": max_tokens,
        "messages": msg
    }).encode()
    for i in range(3):
        try:
            req = Request(
                "https://api.anthropic.com/v1/messages",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01"
                },
                method="POST",
            )
            with urlopen(req, timeout=90) as r:
                res = json.loads(r.read().decode())
            return "".join(b.get("text","") for b in res.get("content",[]) if b.get("type")=="text").strip()
        except HTTPError as e:
            if e.code == 429:
                time.sleep(60 * (i + 1))
                continue
            print(f"HTTP {e.code}")
            sys.exit(1)
    sys.exit(1)

def plines(t):
    """번호 붙은 줄 파싱"""
    r = {}
    for line in t.split("\n"):
        line = line.strip()
        for i in range(1, 20):
            for pfx in [f"{i}.", f"{i})", f"{i}:"]:
                if line.startswith(pfx):
                    r[i] = line[len(pfx):].strip()
    return r

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def main():
    # ── 1. COAL SCRAPE ──────────────────
    print("=== COAL SCRAPING ===")
    coal_prices = {}
    for name, url, pats, unit in [
        ("Newcastle 6000",
         "https://www.oilpriceapi.com/live/coal-price",
         [r"Coal NOW:\s*\$?([\d,.]+)", r"Newcastle.*?([\d,.]+)"],
         "$/t"),
        ("HBA Indonesia",
         "https://coaltradeindo.com/hba-coal-index-price/",
         [r"HBA.*?GAR 6322.*?\$([\d,.]+)", r"HBA1.*?\$([\d,.]+)", r"\$\s*([\d,.]+)"],
         "$/t"),
        ("Coking Coal",
         "https://tradingeconomics.com/commodity/coking-coal",
         [r"Coking Coal.*?rose to ([\d,.]+)", r"([\d]{3,}\.[\d]+) USD per Metric Ton"],
         "$/t"),
    ]:
        v = xnum(fetch(url), pats)
        coal_prices[name] = {"value": v, "unit": unit}
        print(f"  {name}: {v}")

    # ── 2. YAHOO FINANCE ──────────────────
    print("\n=== YAHOO FINANCE ===")
    YF_TICKERS = {
        "copper":      "HG=F",
        "bhp":         "BHP",
        "lme_copper":  "COPX",
        "cameco":      "CCJ",
        "ura_etf":     "URA",
        "samsung":     "005930.KS",
        "lselectric":  "010120.KS",
        "hyundai":     "005380.KS",
        "amorepacific":"090430.KS",
        "lghh":        "051900.KS",
        "tesla":       "TSLA",
        "nvidia":      "NVDA",
        "tsmc":        "TSM",
        "microsoft":   "MSFT",
        "dxy":         "DX-Y.NYB",
        "wti":         "CL=F",
        "gold":        "GC=F",
        "us10y":       "^TNX",
        "vix":         "^VIX",
        "kospi":       "^KS11",
        "sp500":       "^GSPC",
        "hscei":       "^HSCE",
        "nikkei":      "^N225",
    }

    mkt = {}
    for key, ticker in YF_TICKERS.items():
        mkt[key] = fetch_yf(ticker)
        p = mkt[key].get("price")
        c = mkt[key].get("change_pct")
        chg_str = f" ({'+' if c and c>=0 else ''}{c:.2f}%)" if c is not None else ""
        print(f"  {key:15} [{ticker}]: {p}{chg_str}")
        time.sleep(0.3)

    # ── 3. CLAUDE ANALYSIS ──────────────────
    print("\n=== ANALYZING ===")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("NO ANTHROPIC_API_KEY")
        sys.exit(1)

    def p(key):
        v = mkt.get(key, {}).get("price")
        return f"{v:,.2f}" if v else "N/A"

    def pchg(key):
        v = mkt.get(key, {}).get("change_pct")
        return f"{'+' if v and v>=0 else ''}{v:.2f}%" if v else ""

    print("Analyzing coal...")
    coal_text = ask(api_key, f"""오늘은 {DATE_KR}. 아래는 실제 석탄 시장 데이터다.

석탄 가격:
- Newcastle 6000: {coal_prices.get('Newcastle 6000',{}).get('value')} $/t
- HBA Indonesia: {coal_prices.get('HBA Indonesia',{}).get('value')} $/t
- Coking Coal: {coal_prices.get('Coking Coal',{}).get('value')} $/t

관련 지표:
- 구리 선물: ${p('copper')} {pchg('copper')}
- BHP: ${p('bhp')} {pchg('bhp')}
- WTI: ${p('wti')}
- 중국 H주(HSCEI): {p('hscei')}

한국어로 답해. 아래 번호 형식 정확히 지켜:
1. 헤드라인 (핵심 한 문장, 구체적 수치 포함)
2. 인도네시아 (HBA 동향, 공급 측면, 2-3문장)
3. 중국 (수요/재고/정책 동향, 2-3문장)
4. 인도 (수입 트렌드/발전 수요, 2-3문장)
5. 전망 (단기 1-2주 전망, 1-2문장)
6. 선행지표 (왜 구리/BHP가 석탄의 선행지표인지 구체적으로 설명, 1-2문장)""")
    time.sleep(4)

    print("Analyzing sectors...")
    sector_text = ask(api_key, f"""오늘은 {DATE_KR}. 아래 실제 시장 데이터 기반으로 분석해.

구리/BHP: 선물 ${p('copper')} {pchg('copper')}, BHP ${p('bhp')} {pchg('bhp')}, COPX ETF ${p('lme_copper')}
우라늄: Cameco(CCJ) ${p('cameco')} {pchg('cameco')}, URA ETF ${p('ura_etf')} {pchg('ura_etf')}
삼성전자: {p('samsung')} KRW {pchg('samsung')} | NVIDIA ${p('nvidia')} {pchg('nvidia')} | TSMC ${p('tsmc')} {pchg('tsmc')}
LS Electric: {p('lselectric')} KRW {pchg('lselectric')}
현대차: {p('hyundai')} KRW {pchg('hyundai')} | Tesla ${p('tesla')} {pchg('tesla')}
K-Beauty: 아모레퍼시픽 {p('amorepacific')} KRW {pchg('amorepacific')}, LG생건 {p('lghh')} KRW {pchg('lghh')}
Tesla/Tech: Tesla ${p('tesla')} {pchg('tesla')}, NVIDIA ${p('nvidia')} {pchg('nvidia')}, MSFT ${p('microsoft')}
매크로: DXY {p('dxy')}, WTI ${p('wti')}, Gold ${p('gold')}, US10Y {p('us10y')}%, VIX {p('vix')}, KOSPI {p('kospi')}, S&P500 {p('sp500')}, HSCEI {p('hscei')}

각 섹터마다: 동향 2-3문장 + 선행지표 1문장(왜 중요한지 포함). 번호 형식 엄수:
1. 구리 (피어: BHP/COPX 언급)
2. 우라늄 (CCJ+URA 동향)
3. 삼성전자 (HBM/AI 반도체 관점, NVIDIA 연관)
4. LS Electric (AI 데이터센터 전력 수요 관점)
5. 현대차 (EV+Tesla 비교 관점)
6. K-Beauty (아모레/LG생건 피어 비교)
7. Tesla/Tech (NVIDIA+MSFT 포함 테크 섹터 종합)
8. 매크로 (DXY+VIX+금리 종합, EM 리스크 포함)""", max_tokens=2500)
    time.sleep(4)

    print("Writing mini report...")
    mini_report = ask(api_key, f"""오늘은 {DATE_KR}. 전문 상품 트레이더 관점에서 오늘의 시장을 4-5문장으로 요약해.

핵심 데이터:
- Newcastle Coal: {coal_prices.get('Newcastle 6000',{}).get('value')} $/t, Coking: {coal_prices.get('Coking Coal',{}).get('value')} $/t
- 구리: ${p('copper')}, BHP: ${p('bhp')}
- 삼성전자: {p('samsung')} KRW, NVIDIA: ${p('nvidia')}
- DXY: {p('dxy')}, VIX: {p('vix')}, US10Y: {p('us10y')}%
- KOSPI: {p('kospi')}, S&P500: {p('sp500')}

한국어. 전문적이고 간결하게. 주요 리스크/기회 한 가지씩 포함.""", max_tokens=600)

    # ── 4. ASSEMBLE DATA ──────────────────
    cl = plines(coal_text)
    sl = plines(sector_text)

    ticker_list = []
    for name, pdata in coal_prices.items():
        if pdata.get("value"):
            ticker_list.append({
                "label": name, "type": "coal",
                "value": pdata["value"], "unit": pdata["unit"],
                "change_pct": None
            })
    for key, label, unit in [
        ("copper",    "Copper",   "¢/lb"),
        ("cameco",    "Cameco",   "$"),
        ("samsung",   "삼성전자",  "₩"),
        ("lselectric","LS Elec",  "₩"),
        ("tesla",     "Tesla",    "$"),
        ("nvidia",    "NVIDIA",   "$"),
        ("dxy",       "DXY",      ""),
        ("wti",       "WTI",      "$"),
        ("gold",      "Gold",     "$"),
        ("us10y",     "US10Y",    "%"),
        ("vix",       "VIX",      ""),
        ("kospi",     "KOSPI",    ""),
    ]:
        pr = mkt[key].get("price")
        cp2 = mkt[key].get("change_pct")
        if pr:
            ticker_list.append({
                "label": label, "type": "market",
                "value": pr, "unit": unit, "change_pct": cp2
            })

    newsletter = {
        "date": DATE_STR,
        "date_kr": DATE_KR,
        "ticker": ticker_list,
        "coal": {
            "prices": coal_prices,
            "headline":  cl.get(1, "석탄 시장 업데이트"),
            "indonesia": cl.get(2, ""),
            "china":     cl.get(3, ""),
            "india":     cl.get(4, ""),
            "outlook":   cl.get(5, ""),
            "leading":   cl.get(6, ""),
        },
        "copper":     {"price": mkt["copper"].get("price"),     "chg": mkt["copper"].get("change_pct"),     "bhp": mkt["bhp"].get("price"),      "bhp_chg": mkt["bhp"].get("change_pct"),      "text": sl.get(1,"")},
        "uranium":    {"price": mkt["cameco"].get("price"),     "chg": mkt["cameco"].get("change_pct"),     "ura":  mkt["ura_etf"].get("price"),  "ura_chg": mkt["ura_etf"].get("change_pct"),  "text": sl.get(2,"")},
        "samsung":    {"price": mkt["samsung"].get("price"),    "chg": mkt["samsung"].get("change_pct"),    "nvda": mkt["nvidia"].get("price"),   "nvda_chg": mkt["nvidia"].get("change_pct"),  "text": sl.get(3,"")},
        "lselectric": {"price": mkt["lselectric"].get("price"), "chg": mkt["lselectric"].get("change_pct"), "text": sl.get(4,"")},
        "hyundai":    {"price": mkt["hyundai"].get("price"),    "chg": mkt["hyundai"].get("change_pct"),    "tesla": mkt["tesla"].get("price"),   "tesla_chg": mkt["tesla"].get("change_pct"),  "text": sl.get(5,"")},
        "kbeauty":    {"amore": mkt["amorepacific"].get("price"),"amore_chg": mkt["amorepacific"].get("change_pct"),"lghh": mkt["lghh"].get("price"),"lghh_chg": mkt["lghh"].get("change_pct"), "text": sl.get(6,"")},
        "teslatech":  {"tesla": mkt["tesla"].get("price"),      "tesla_chg": mkt["tesla"].get("change_pct"), "nvda": mkt["nvidia"].get("price"),  "nvda_chg": mkt["nvidia"].get("change_pct"),  "msft": mkt["microsoft"].get("price"), "text": sl.get(7,"")},
        "macro":      {
            "dxy":   mkt["dxy"].get("price"),   "wti":   mkt["wti"].get("price"),
            "gold":  mkt["gold"].get("price"),  "us10y": mkt["us10y"].get("price"),
            "vix":   mkt["vix"].get("price"),   "kospi": mkt["kospi"].get("price"),
            "sp500": mkt["sp500"].get("price"), "hscei": mkt["hscei"].get("price"),
            "text": sl.get(8,"")
        },
        "miniReport": {"content": mini_report},
    }

    os.makedirs("data", exist_ok=True)
    with open("data/newsletter.json", "w", encoding="utf-8") as f:
        json.dump(newsletter, f, ensure_ascii=False, indent=2)
    print("=== DATA SAVED: data/newsletter.json ===")

    build_html(newsletter)
    print("=== HTML SAVED: dist/index.html ===")


# ─────────────────────────────────────────
# HTML BUILDER
# ─────────────────────────────────────────

def _color(pct):
    if pct is None: return "#57534e"
    return "#4ade80" if pct >= 0 else "#f87171"

def _arrow(pct):
    if pct is None: return ""
    sign = "+" if pct >= 0 else ""
    return f"{'▲' if pct >= 0 else '▼'} {sign}{pct:.2f}%"

def _fmt(v, unit="", decimals=2):
    if v is None: return "—"
    try:
        v = float(v)
        if unit == "₩":  return f"₩{v:,.0f}"
        elif unit == "%": return f"{v:.2f}%"
        elif unit == "":  return f"{v:,.2f}"
        else:             return f"{unit}{v:,.{decimals}f}"
    except:
        return str(v)

def build_html(n):
    c  = n["coal"]
    cp = c["prices"]
    m  = n["macro"]

    # ── TICKER BAR ──
    tick_html = ""
    for t in n["ticker"]:
        v   = t["value"]
        u   = t["unit"]
        pct = t.get("change_pct")
        color = _color(pct)
        arrow = _arrow(pct)
        if u == "₩":          vstr = f"₩{float(v):,.0f}"
        elif u == "%":         vstr = f"{float(v):.2f}%"
        elif u in ("$","¢/lb"):vstr = f"{u}{float(v):,.2f}"
        else:                  vstr = f"{float(v):,.2f}" if isinstance(v,(int,float)) else str(v)
        badge = "tick-coal" if t["type"]=="coal" else "tick-mkt"
        chg_span = f'<span class="chg" style="color:{color}">{arrow}</span>' if arrow else ""
        tick_html += f'<div class="tick {badge}"><span class="tlabel">{t["label"]}</span><span class="tval">{vstr}</span>{chg_span}</div>'

    # ── MACRO STRIP ──
    macro_items = [
        ("DXY",   m.get("dxy"),   ""),
        ("WTI",   m.get("wti"),   "$"),
        ("GOLD",  m.get("gold"),  "$"),
        ("US10Y", m.get("us10y"), "%"),
        ("VIX",   m.get("vix"),   ""),
        ("KOSPI", m.get("kospi"), ""),
        ("S&P",   m.get("sp500"), ""),
        ("HSCEI", m.get("hscei"), ""),
    ]
    macro_html = ""
    for k, v, u in macro_items:
        macro_html += f'<div class="mitem"><div class="mk">{k}</div><div class="mv">{_fmt(v,u,1)}</div></div>'

    # ── COAL BLOCK ──
    price_cards = ""
    for pname, pd in cp.items():
        v = pd.get("value")
        vstr = f"{v:,.1f}" if v else "—"
        price_cards += f'<div class="cprice"><div class="cpname">{pname}</div><div class="cpval">{vstr}</div><div class="cpunit">{pd.get("unit","")}</div></div>'

    coal_html = f"""
<div class="coal-block">
  <div class="coal-head">{c.get("headline","")}</div>
  <div class="coal-prices">{price_cards}</div>
  <div class="coal-grid">
    <div class="cgrid-item"><div class="cgrid-flag">🇮🇩 INDONESIA</div><div class="cgrid-text">{c.get("indonesia","")}</div></div>
    <div class="cgrid-item"><div class="cgrid-flag">🇨🇳 CHINA</div><div class="cgrid-text">{c.get("china","")}</div></div>
    <div class="cgrid-item"><div class="cgrid-flag">🇮🇳 INDIA</div><div class="cgrid-text">{c.get("india","")}</div></div>
  </div>
  <div class="insight-row">
    <div class="insight"><div class="insight-label">▸ OUTLOOK</div><div class="insight-text">{c.get("outlook","")}</div></div>
    <div class="insight"><div class="insight-label">▸ LEADING INDICATOR</div><div class="insight-text">{c.get("leading","")}</div></div>
  </div>
</div>"""

    # ── SECTOR CARDS ──
    def pp(v, chg_pct, unit="$"):
        if v is None: return "<span class='px-na'>—</span>"
        color = _color(chg_pct)
        arrow = _arrow(chg_pct)
        vstr  = _fmt(v, unit)
        chg_s = f'<span style="color:{color};margin-left:3px;font-size:10px">{arrow}</span>' if arrow else ""
        return f'<span class="px-chip">{vstr}{chg_s}</span>'

    def sector_card(sid, title, prices_html, text, leading):
        return f"""
<div class="scard">
  <div class="scard-head" onclick="tog('{sid}')">
    <span class="scard-title">{title}</span>
    <div class="scard-right">
      <div class="scard-prices">{prices_html}</div>
      <span class="scard-toggle" id="sarr-{sid}">▸</span>
    </div>
  </div>
  <div class="scard-body" id="sb-{sid}">
    <div class="scard-text">{text}</div>
    <div class="leading-bar">
      <span class="leading-label">LEADING INDICATOR</span>
      <span class="leading-text">{leading}</span>
    </div>
  </div>
</div>"""

    cv = n["copper"];    uv = n["uranium"];  sv = n["samsung"]
    lv = n["lselectric"];hv = n["hyundai"];  kv = n["kbeauty"]
    tv = n["teslatech"]

    sectors_html  = sector_card("copper",    "COPPER / BHP",
        pp(cv.get("price"),cv.get("chg"),"¢/lb") + pp(cv.get("bhp"),cv.get("bhp_chg"),"$"),
        cv.get("text",""),
        "글로벌 제조업 PMI와 구리 가격은 높은 상관관계 — 경기 회복 국면에서 석탄 수요를 4-6주 선행")
    sectors_html += sector_card("uranium",   "URANIUM / CAMECO",
        pp(uv.get("price"),uv.get("chg"),"$") + pp(uv.get("ura"),uv.get("ura_chg"),"$"),
        uv.get("text",""),
        "신규 원전 승인 뉴스와 CCJ 주가가 우라늄 현물가를 2-4주 선행; URA ETF 자금 유입 추이 주목")
    sectors_html += sector_card("samsung",   "삼성전자 / HBM",
        pp(sv.get("price"),sv.get("chg"),"₩") + pp(sv.get("nvda"),sv.get("nvda_chg"),"$"),
        sv.get("text",""),
        "NVIDIA 분기 실적 및 HBM 수주 공시가 삼성전자 주가 2-3주 선행; AI 서버 출하량 데이터 모니터링")
    sectors_html += sector_card("lselectric","LS ELECTRIC",
        pp(lv.get("price"),lv.get("chg"),"₩"),
        lv.get("text",""),
        "미국 IRA 전력 인프라 수주 발표 및 데이터센터 착공 통계가 LS Electric 수주 모멘텀 선행 지표")
    sectors_html += sector_card("hyundai",   "현대차 / EV",
        pp(hv.get("price"),hv.get("chg"),"₩") + pp(hv.get("tesla"),hv.get("tesla_chg"),"$"),
        hv.get("text",""),
        "미국 월간 EV 판매량 및 충전 인프라 투자 통계, Tesla 판매 동향이 현대 EV 섹터 선행 지표")
    sectors_html += sector_card("kbeauty",   "K-BEAUTY",
        pp(kv.get("amore"),kv.get("amore_chg"),"₩") + pp(kv.get("lghh"),kv.get("lghh_chg"),"₩"),
        kv.get("text",""),
        "중국 소비자 신뢰지수 및 면세점 월 매출 통계가 아모레/LG생건 중국 수출 실적 2-3주 선행")
    sectors_html += sector_card("teslatech", "TESLA / TECH",
        pp(tv.get("tesla"),tv.get("tesla_chg"),"$") + pp(tv.get("nvda"),tv.get("nvda_chg"),"$") + pp(tv.get("msft"),None,"$"),
        tv.get("text",""),
        "NVIDIA 데이터센터 수주 발표 및 TSMC 월간 매출이 광의 테크 섹터 방향성 2주 선행")
    sectors_html += sector_card("macro",     "MACRO",
        f'<span class="px-chip">DXY {_fmt(m.get("dxy"),"",1)}</span><span class="px-chip">VIX {_fmt(m.get("vix"),"",1)}</span>',
        m.get("text",""),
        "DXY 상승 = 달러 표시 원자재 하방 압력 + EM 자금 유출; VIX 20 돌파 시 리스크오프 본격화 신호")

    report_html = f"""
<div class="report-block">
  <div class="report-label">◆ INTELLIGENCE REPORT — {n["date_kr"]}</div>
  <div class="report-text">{n["miniReport"].get("content","")}</div>
</div>"""

    # ── STYLE ──
    style = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=IBM+Plex+Sans+KR:wght@300;400;500;600&display=swap');
:root{--bg:#09080A;--bg2:#0f0e10;--bg3:#141316;--border:rgba(255,255,255,.06);--coal:#FF6B35;--coal-bg:rgba(255,107,53,.08);--up:#4ade80;--dn:#f87171;--text:#E8E0DA;--muted:#8B8280;--faint:#3a3538;--mono:'IBM Plex Mono',monospace;--sans:'IBM Plex Sans KR',sans-serif}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{font-family:var(--sans);background:var(--bg);color:var(--text);min-height:100vh;padding:16px;max-width:820px;margin:0 auto;font-size:13px}
.header{display:flex;align-items:center;justify-content:space-between;padding:0 0 14px;border-bottom:1px solid var(--border);margin-bottom:16px}
.logo{font-family:var(--mono);font-size:14px;font-weight:700;letter-spacing:3px;color:var(--coal)}
.header-meta{font-family:var(--mono);font-size:10px;color:var(--faint);text-align:right}
.ticker-wrap{overflow-x:auto;margin-bottom:12px;padding-bottom:4px;scrollbar-width:none}
.ticker-wrap::-webkit-scrollbar{display:none}
.ticker{display:flex;gap:5px;width:max-content;animation:tickerScroll 50s linear infinite}.ticker-wrap:hover .ticker{animation-play-state:paused}@keyframes tickerScroll{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}
.tick{border-radius:8px;padding:7px 10px;min-width:80px;border:1px solid var(--border)}
.tick-coal{background:var(--coal-bg);border-color:rgba(255,107,53,.25)}
.tick-mkt{background:var(--bg2)}
.tlabel{display:block;font-family:var(--mono);font-size:8px;color:var(--muted);text-transform:uppercase;margin-bottom:3px;letter-spacing:.5px}
.tick-coal .tlabel{color:var(--coal)}
.tval{display:block;font-family:var(--mono);font-size:12px;font-weight:600;color:var(--text)}
.chg{display:block;font-family:var(--mono);font-size:9px;margin-top:2px}
.macro-strip{display:flex;background:var(--bg2);border:1px solid var(--border);border-radius:10px;overflow-x:auto;margin-bottom:18px;scrollbar-width:none}
.macro-strip::-webkit-scrollbar{display:none}
.mitem{flex:1;min-width:60px;padding:9px 10px;text-align:center;border-right:1px solid var(--border)}
.mitem:last-child{border-right:none}
.mk{font-family:var(--mono);font-size:8px;color:var(--faint);letter-spacing:.5px;margin-bottom:3px}
.mv{font-family:var(--mono);font-size:12px;color:var(--muted);font-weight:600}
.sec-label{font-family:var(--mono);font-size:9px;color:var(--coal);letter-spacing:3px;margin:18px 0 8px;display:flex;align-items:center;gap:8px}
.sec-label::after{content:'';flex:1;height:1px;background:var(--coal-bg)}
.coal-block{background:var(--bg2);border:1px solid rgba(255,107,53,.2);border-radius:14px;padding:16px;margin-bottom:8px}
.coal-head{font-size:14px;font-weight:600;color:var(--text);margin-bottom:14px;line-height:1.5}
.coal-prices{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap}
.cprice{flex:1;min-width:110px;background:var(--bg3);border:1px solid rgba(255,107,53,.15);border-radius:10px;padding:10px 12px}
.cpname{font-family:var(--mono);font-size:8px;color:var(--coal);letter-spacing:.5px;margin-bottom:5px}
.cpval{font-family:var(--mono);font-size:20px;font-weight:700;color:var(--coal)}
.cpunit{font-family:var(--mono);font-size:9px;color:var(--faint);margin-top:2px}
.coal-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:12px}
.cgrid-item{background:var(--bg3);border-radius:8px;padding:10px}
.cgrid-flag{font-size:10px;color:var(--coal);font-family:var(--mono);margin-bottom:5px}
.cgrid-text{font-size:11px;color:var(--muted);line-height:1.6}
.insight-row{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.insight{background:var(--bg3);border-left:2px solid var(--coal);border-radius:0 8px 8px 0;padding:10px 12px}
.insight-label{font-family:var(--mono);font-size:8px;color:var(--coal);letter-spacing:1px;margin-bottom:4px}
.insight-text{font-size:11px;color:var(--muted);line-height:1.6}
.scard{background:var(--bg2);border:1px solid var(--border);border-radius:12px;margin-bottom:6px;overflow:hidden;transition:border-color .2s}
.scard:hover{border-color:rgba(255,107,53,.2)}
.scard-head{display:flex;align-items:center;justify-content:space-between;padding:13px 16px;cursor:pointer;user-select:none}
.scard-head:hover{background:var(--bg3)}
.scard-title{font-family:var(--mono);font-size:11px;font-weight:600;color:var(--text);letter-spacing:1px}
.scard-right{display:flex;align-items:center;gap:10px}
.scard-prices{display:flex;gap:6px;align-items:center}
.px-chip{font-family:var(--mono);font-size:11px;color:var(--muted);background:var(--bg3);padding:3px 7px;border-radius:5px}
.px-na{color:var(--faint)}
.scard-toggle{font-size:11px;color:var(--faint);min-width:14px}
.scard-body{display:none;padding:0 16px 14px;animation:fadeIn .2s ease}
.scard-body.open{display:block}
@keyframes fadeIn{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:translateY(0)}}
.scard-text{font-size:12px;color:var(--muted);line-height:1.8;margin-bottom:10px}
.leading-bar{background:var(--bg3);border-left:2px solid var(--coal);border-radius:0 6px 6px 0;padding:8px 12px;display:flex;gap:8px;align-items:flex-start}
.leading-label{font-family:var(--mono);font-size:8px;color:var(--coal);letter-spacing:1px;white-space:nowrap;padding-top:2px}
.leading-text{font-size:11px;color:var(--faint);line-height:1.5}
.report-block{background:linear-gradient(135deg,var(--bg2) 0%,#120f14 100%);border:1px solid rgba(255,107,53,.15);border-radius:14px;padding:18px;margin-top:18px}
.report-label{font-family:var(--mono);font-size:9px;color:var(--coal);letter-spacing:2px;margin-bottom:12px}
.report-text{font-size:13px;color:var(--muted);line-height:1.9;font-weight:300}
.footer{text-align:center;padding:24px 0 8px;font-family:var(--mono);font-size:9px;color:var(--faint);letter-spacing:1px}
@media(max-width:560px){.coal-grid{grid-template-columns:1fr}.insight-row{grid-template-columns:1fr}.header{flex-direction:column;align-items:flex-start;gap:4px}.cpval{font-size:16px}}
"""

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Market Intelligence · {n["date_kr"]}</title>
<style>{style}</style>
</head>
<body>
<div class="header">
  <div class="logo">MARKET INTELLIGENCE</div>
  <div class="header-meta">{n["date_kr"]}<br>KST AUTO-GENERATED</div>
</div>
<div class="ticker-wrap"><div class="ticker">{tick_html}{tick_html}</div></div>
<div class="macro-strip">{macro_html}</div>
<div class="sec-label">COAL — FULL DETAIL</div>
{coal_html}
<div class="sec-label">SECTORS — TAP TO EXPAND</div>
{sectors_html}
{report_html}
<div class="footer">MARKET INTELLIGENCE · {n["date_kr"]} · AUTO-GENERATED DAILY 07:00 KST</div>
<script>
function tog(id){{
  const body=document.getElementById('sb-'+id);
  const arr=document.getElementById('sarr-'+id);
  const open=body.classList.toggle('open');
  arr.textContent=open?'▾':'▸';
  arr.style.color=open?'var(--coal)':'var(--faint)';
}}
</script>
</body>
</html>"""

    os.makedirs("dist", exist_ok=True)
    with open("dist/index.html","w",encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    main()
