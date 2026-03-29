import json, os, sys, urllib.request
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

def main():
    print("\n=== Claude API Newsletter Generation ===\n")

    if not os.path.exists("data/raw_data.json"):
        print("ERROR: run scraper.py first")
        sys.exit(1)

    with open("data/raw_data.json", "r", encoding="utf-8") as f:
        raw = json.load(f)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    prices_str = json.dumps(raw.get("prices", {}), ensure_ascii=False, indent=2)
    date_kr = raw.get("date_kr", "")

    system = f"""You are a senior multi-market analyst. Today is {date_kr}.
Scraped market data (some values may be null):

{prices_str}

Using this data AND your training knowledge, produce a Korean-language market newsletter.
Return ONLY valid JSON. No markdown. No backticks. All text in Korean.

JSON structure:
{{
  "date": "{raw.get('date','')}",
  "date_kr": "{date_kr}",
  "ticker": [
    {{"label":"뉴캐슬 6000","value":"$XXX/t","change":"±X.X%","trend":"UP|DOWN|STABLE","source":"출처","date":"MM/DD"}}
  ],
  "coal": {{
    "briefHeadline": "한 문장",
    "briefText": "2-3문장",
    "articles": [
      {{"title":"제목","source":"출처","date":"MM/DD","summary":"1-2문장","relevance":"HIGH|MEDIUM|LOW","investmentImplication":"시사점"}}
    ],
    "countryIndonesia": "1-2문장",
    "countryChina": "1-2문장",
    "countryIndia": "1-2문장",
    "outlook": ["전망1","전망2","전망3"],
    "leadingIndicators": [{{"name":"지표","value":"값","source":"출처","date":"날짜","why":"관련성"}}]
  }},
  "copper": {{"headline":"","summary":"","peers":"","leadingIndicators":[]}},
  "uranium": {{"headline":"","summary":"","peers":"","leadingIndicators":[]}},
  "samsung": {{"headline":"","summary":"","peers":"","leadingIndicators":[]}},
  "lsElectric": {{"headline":"","summary":"","leadingIndicators":[]}},
  "hyundai": {{"headline":"","summary":""}},
  "kBeauty": {{"headline":"","summary":""}},
  "teslaTech": {{"headline":"","summary":""}},
  "macro": {{"headline":"","summary":"","indicators":[]}},
  "miniReport": {{"title":"특징 이슈","content":"3-4문장"}}
}}

RULES:
- ticker: 8-10 items with scraped values
- coal: 4-6 articles, detailed
- Leading indicators: explain WHY each matters
- Include source+date for every data point
- miniReport: most impactful theme today"""

    body = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 8000,
        "system": system,
        "messages": [{"role": "user", "content": f"오늘({date_kr}) 멀티마켓 뉴스레터를 생성해주세요."}],
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    print("Calling Claude API (30-90 seconds)...")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"API error: {e}")
        sys.exit(1)

    texts = [b["text"] for b in result.get("content", []) if b.get("type") == "text"]
    if not texts:
        print("ERROR: no text in API response")
        sys.exit(1)

   cleaned = "\n".join(texts).replace("```json", "").replace("```", "").strip()
    if not cleaned.endswith("}"):
        last_brace = cleaned.rfind("}")
        if last_brace > 0:
            cleaned = cleaned[:last_brace + 1]
    try:
        newsletter = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Response preview: {cleaned[:500]}")
        print(f"Response end: {cleaned[-200:]}")
        sys.exit(1)

    with open("data/newsletter.json", "w", encoding="utf-8") as f:
        json.dump(newsletter, f, ensure_ascii=False, indent=2)

    print(f"Done: data/newsletter.json")
    print(f"Sections: {list(newsletter.keys())}")

if __name__ == "__main__":
    main()
