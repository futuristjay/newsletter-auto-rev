import json, os, sys, urllib.request, time

def call(api_key, prompt, label=""):
    print(f"  API call: {label}...")
    body = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2048,
        "messages": [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": "{"}
        ],
    }).encode("utf-8")
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=body,
                headers={"Content-Type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=90) as r:
                res = json.loads(r.read().decode("utf-8"))
            txt = "".join(b.get("text","") for b in res.get("content",[]) if b.get("type")=="text")
            txt = "{" + txt.strip()
            last = txt.rfind("}")
            if last > 0:
                txt = txt[:last+1]
            result = json.loads(txt)
            print(f"  OK: {list(result.keys())}")
            return result
        except urllib.error.HTTPError as e:
            if e.code == 429:
                w = 60*(attempt+1)
                print(f"  429 rate limit, waiting {w}s...")
                time.sleep(w)
                continue
            print(f"  HTTP {e.code}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"  JSON error: {e}")
            print(f"  Text: {txt[:300] if txt else 'empty'}")
            sys.exit(1)
        except Exception as e:
            print(f"  Error: {e}")
            sys.exit(1)
    sys.exit(1)

def main():
    print("\n=== Newsletter Generation ===\n")
    with open("data/raw_data.json","r",encoding="utf-8") as f:
        raw = json.load(f)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key: print("No API key"); sys.exit(1)
    p = json.dumps(raw.get("prices",{}), ensure_ascii=False)
    dk = raw.get("date_kr","")
    dt = raw.get("date","")

    # 1) Ticker
    ticker = call(api_key, f"오늘:{dk}. 데이터:{p}\n\n8개 시세 ticker JSON 배열을 만들어. 한국어. 포맷: [{{\"label\":\"뉴캐슬 6000\",\"value\":\"$135/t\",\"change\":\"+1.6%\",\"trend\":\"UP\",\"source\":\"출처\",\"date\":\"03/29\"}}]. 스크래핑 데이터의 실제 값을 사용해. JSON만 반환.", "ticker")
    time.sleep(3)

    # 2) Coal
    coal = call(api_key, f"오늘:{dk}. 데이터:{p}\n\n석탄 마켓 분석 JSON. 한국어로. 포맷: {{\"briefHeadline\":\"헤드라인\",\"briefText\":\"브리프2문장\",\"articles\":[{{\"title\":\"제목\",\"source\":\"출처\",\"date\":\"03/29\",\"summary\":\"요약\",\"relevance\":\"HIGH\",\"investmentImplication\":\"시사점\"}}],\"countryIndonesia\":\"1문장\",\"countryChina\":\"1문장\",\"countryIndia\":\"1문장\",\"outlook\":[\"전망1\",\"전망2\",\"전망3\"]}}. 기사 3개. JSON만.", "coal")
    time.sleep(3)

    # 3) Others
    others = call(api_key, f"오늘:{dk}. 데이터:{p}\n\n아래 섹터별 한줄 요약 JSON. 한국어. 포맷: {{\"copper\":{{\"headline\":\"구리요약\",\"summary\":\"2문장\"}},\"uranium\":{{\"headline\":\"우라늄\",\"summary\":\"2문장\"}},\"samsung\":{{\"headline\":\"삼성\",\"summary\":\"2문장\"}},\"lsElectric\":{{\"headline\":\"LS\",\"summary\":\"1문장\"}},\"hyundai\":{{\"headline\":\"현대\",\"summary\":\"1문장\"}},\"kBeauty\":{{\"headline\":\"화장품\",\"summary\":\"1문장\"}},\"teslaTech\":{{\"headline\":\"테슬라테크\",\"summary\":\"1문장\"}},\"macro\":{{\"headline\":\"매크로\",\"summary\":\"2문장\"}},\"miniReport\":{{\"title\":\"이슈\",\"content\":\"2문장\"}}}}. JSON만.", "others")

    # Merge
    newsletter = {"date":dt,"date_kr":dk}
    if isinstance(ticker, list):
        newsletter["ticker"] = ticker
    elif isinstance(ticker, dict) and "ticker" in ticker:
        newsletter["ticker"] = ticker["ticker"]
    else:
        newsletter["ticker"] = []
    newsletter["coal"] = coal
    newsletter.update({k:others.get(k,{}) for k in ["copper","uranium","samsung","lsElectric","hyundai","kBeauty","teslaTech","macro","miniReport"]})

    os.makedirs("data", exist_ok=True)
    with open("data/newsletter.json","w",encoding="utf-8") as f:
        json.dump(newsletter, f, ensure_ascii=False, indent=2)
    print(f"\nDone! {list(newsletter.keys())}")

if __name__ == "__main__":
    main()
