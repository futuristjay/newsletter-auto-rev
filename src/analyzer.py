import json, os, sys, urllib.request, time

def call(api_key, prompt, prefill="{", label=""):
    print(f"  API call: {label}...")
    body = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2048,
        "messages": [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": prefill}
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
            txt = prefill + txt.strip()
            if prefill == "[":
                last = txt.rfind("]")
                if last > 0: txt = txt[:last+1]
            else:
                last = txt.rfind("}")
                if last > 0: txt = txt[:last+1]
            result = json.loads(txt)
            print(f"  OK")
            return result
        except urllib.error.HTTPError as e:
            if e.code == 429:
                w = 60*(attempt+1)
                print(f"  429, waiting {w}s...")
                time.sleep(w)
                continue
            print(f"  HTTP {e.code}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"  JSON err: {e}")
            print(f"  Raw: {txt[:400] if txt else 'empty'}")
            sys.exit(1)
        except Exception as e:
            print(f"  Err: {e}")
            sys.exit(1)
    sys.exit(1)

def main():
    print("\n=== Newsletter Gen ===\n")
    with open("data/raw_data.json","r",encoding="utf-8") as f:
        raw = json.load(f)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key: print("No key"); sys.exit(1)
    p = json.dumps(raw.get("prices",{}), ensure_ascii=False)
    dk = raw.get("date_kr","")
    dt = raw.get("date","")

    # 1) Ticker - prefill with [ for array
    print("Step 1/3: Ticker")
    ticker = call(api_key,
        f"오늘:{dk}. 데이터:{p}\n\n위 데이터에서 8개 시세를 JSON 배열로 만들어. 배열만 반환. 다른 텍스트 금지.\n포맷: [{{\"label\":\"뉴캐슬 6000\",\"value\":\"$135/t\",\"change\":\"+1.6%\",\"trend\":\"UP\",\"source\":\"oilpriceapi\",\"date\":\"03/29\"}}]",
        prefill="[", label="ticker")
    time.sleep(5)

    # 2) Coal
    print("Step 2/3: Coal")
    coal = call(api_key,
        f"오늘:{dk}. 데이터:{p}\n\n석탄 시장 분석을 아래 JSON 포맷으로. 한국어. JSON만 반환.\n{{\"briefHeadline\":\"헤드라인\",\"briefText\":\"2문장\",\"articles\":[{{\"title\":\"제목\",\"source\":\"출처\",\"date\":\"MM/DD\",\"summary\":\"1문장\",\"relevance\":\"HIGH\",\"investmentImplication\":\"1문장\"}}],\"countryIndonesia\":\"1문장\",\"countryChina\":\"1문장\",\"countryIndia\":\"1문장\",\"outlook\":[\"전망1\",\"전망2\",\"전망3\"]}}\n기사는 정확히 3개.",
        prefill="{", label="coal")
    time.sleep(5)

    # 3) Others - all other sectors
    print("Step 3/3: Others")
    others = call(api_key,
        f"오늘:{dk}. 데이터:{p}\n\n아래 포맷으로 각 섹터 한줄 요약. 한국어. JSON만.\n{{\"copper\":{{\"headline\":\"요약\",\"summary\":\"2문장\"}},\"uranium\":{{\"headline\":\"요약\",\"summary\":\"2문장\"}},\"samsung\":{{\"headline\":\"요약\",\"summary\":\"2문장\"}},\"lsElectric\":{{\"headline\":\"요약\",\"summary\":\"1문장\"}},\"hyundai\":{{\"headline\":\"요약\",\"summary\":\"1문장\"}},\"kBeauty\":{{\"headline\":\"요약\",\"summary\":\"1문장\"}},\"teslaTech\":{{\"headline\":\"요약\",\"summary\":\"1문장\"}},\"macro\":{{\"headline\":\"요약\",\"summary\":\"2문장\"}},\"miniReport\":{{\"title\":\"이슈제목\",\"content\":\"2문장\"}}}}",
        prefill="{", label="others")

    # Merge
    newsletter = {"date":dt,"date_kr":dk}
    newsletter["ticker"] = ticker if isinstance(ticker, list) else []
    newsletter["coal"] = coal if isinstance(coal, dict) else {}
    if isinstance(others, dict):
        for k in ["copper","uranium","samsung","lsElectric","hyundai","kBeauty","teslaTech","macro","miniReport"]:
            newsletter[k] = others.get(k, {})

    os.makedirs("data", exist_ok=True)
    with open("data/newsletter.json","w",encoding="utf-8") as f:
        json.dump(newsletter, f, ensure_ascii=False, indent=2)
    print(f"\nDone! Keys: {list(newsletter.keys())}")

if __name__ == "__main__":
    main()
