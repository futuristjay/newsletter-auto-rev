import json, os, sys

def main():
    print("\n=== Building HTML ===\n")
    if not os.path.exists("data/newsletter.json"):
        print("ERROR: run analyzer.py first")
        sys.exit(1)

    with open("data/newsletter.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    d = json.dumps(data, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Market Intelligence</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Noto Sans KR',-apple-system,sans-serif;background:#0d0b09;color:#e2d9ce;min-height:100vh}}
@keyframes tk{{from{{transform:translateX(0)}}to{{transform:translateX(-50%)}}}}
.hd{{background:rgba(13,11,9,.95);border-bottom:1px solid rgba(148,163,184,.1);padding:0 20px;position:sticky;top:0;z-index:99}}
.hdi{{max-width:1100px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;height:52px}}
.logo{{font-family:monospace;font-size:16px;font-weight:700;color:#ff8a65;letter-spacing:.06em}}
.dt{{font-family:monospace;font-size:11px;color:#57534e}}
.tk{{background:#1a1612;border-bottom:1px solid rgba(148,163,184,.1);height:38px;display:flex;align-items:center;overflow:hidden}}
.tkl{{background:#e64a19;color:#fff;font-family:monospace;font-size:10px;font-weight:700;padding:0 14px;height:100%;display:flex;align-items:center;letter-spacing:.1em}}
.tks{{overflow:hidden;flex:1}}
.tkt{{display:flex;animation:tk 40s linear infinite;width:max-content}}
.tki{{display:flex;align-items:center;gap:7px;padding:0 20px;border-right:1px solid rgba(148,163,184,.08);font-family:monospace;font-size:12px;white-space:nowrap}}
.mn{{max-width:1100px;margin:0 auto;padding:24px 20px 48px}}
.sl{{display:flex;align-items:center;gap:8px;margin:20px 0 14px;font-family:monospace;font-size:11px;color:#e64a19;letter-spacing:.15em}}
.sll{{flex:1;height:1px;background:rgba(148,163,184,.1)}}
.cd{{background:#1a1612;border:1px solid rgba(148,163,184,.1);border-radius:10px;padding:16px 18px;margin-bottom:12px}}
.cb{{background:linear-gradient(135deg,rgba(230,74,25,.08),transparent);border:1px solid rgba(230,74,25,.18)}}
.ch{{font-family:Georgia,serif;font-size:17px;color:#faf6f1;line-height:1.4;margin-bottom:10px}}
.ct{{font-size:13px;line-height:1.75;color:#a8a29e}}
.tg{{padding:2px 7px;border-radius:4px;font-size:10px;font-weight:700;font-family:monospace}}
.tH{{background:rgba(230,74,25,.15);color:#ff8a65}}
.tM{{background:rgba(245,158,11,.12);color:#f59e0b}}
.tL{{background:rgba(148,163,184,.08);color:#64748b}}
.imp{{margin-top:10px;padding:9px 13px;background:rgba(230,74,25,.05);border-left:3px solid rgba(230,74,25,.35);border-radius:0 6px 6px 0}}
.imp b{{font-size:10px;font-family:monospace;color:#e64a19;letter-spacing:.1em;display:block;margin-bottom:3px}}
.imp p{{margin:0;font-size:12px;line-height:1.6;color:#a8a29e}}
.ex{{background:#1a1612;border:1px solid rgba(148,163,184,.1);border-radius:10px;overflow:hidden;margin-bottom:12px}}
.exh{{padding:14px 18px;cursor:pointer;display:flex;align-items:center;justify-content:space-between}}
.ext{{font-family:monospace;font-size:14px;font-weight:700;color:#faf6f1}}
.exs{{font-family:monospace;font-size:11px;color:#57534e}}
.exa{{font-family:monospace;font-size:14px;color:#ff8a65;transition:transform .3s}}
.exb{{padding:0 18px 18px;border-top:1px solid rgba(148,163,184,.1);display:none;padding-top:14px}}
.li{{padding:8px 0;border-bottom:1px solid rgba(148,163,184,.1)}}
.lit{{display:flex;justify-content:space-between;margin-bottom:4px}}
.lin{{font-family:monospace;font-size:12px;color:#faf6f1;font-weight:500}}
.liv{{font-family:monospace;font-size:12px;color:#ff8a65}}
.liw{{margin:0;font-size:11px;line-height:1.5;color:#57534e}}
.lis{{font-size:10px;color:#44403c;font-family:monospace;margin-top:2px}}
.mr{{background:linear-gradient(135deg,rgba(239,68,68,.06),transparent);border:1px solid rgba(239,68,68,.15);border-radius:10px;padding:16px 18px;margin-top:24px}}
.up{{color:#22c55e}}.dn{{color:#ef4444}}.fl{{color:#94a3b8}}
.ft{{text-align:center;padding:20px;font-size:11px;color:#2a2420;font-family:monospace;border-top:1px solid rgba(148,163,184,.06)}}
</style>
</head>
<body>
<div class="hd"><div class="hdi"><div class="logo">⛏ MARKET INTELLIGENCE</div><div class="dt" id="dt"></div></div></div>
<div class="tk"><div class="tkl">LIVE</div><div class="tks"><div class="tkt" id="ticker"></div></div></div>
<div class="mn" id="main"></div>
<div class="ft" id="ft"></div>
<script>
const D={d};
document.getElementById('dt').textContent=D.date_kr||'';
document.getElementById('ft').textContent='MARKET INTELLIGENCE · '+(D.date_kr||'')+' · 투자 참고용이며 투자 권유가 아닙니다';
const tc=t=>t==='UP'?'up':t==='DOWN'?'dn':'fl';
const ti=t=>t==='UP'?'▲':t==='DOWN'?'▼':'━';
let tk='';
const items=[...(D.ticker||[]),...(D.ticker||[])];
items.forEach(p=>{{tk+=`<div class="tki"><span style="color:#57534e;font-size:10px">${{p.label}}</span><span style="color:#faf6f1;font-weight:600">${{p.value}}</span><span class="${{tc(p.trend)}}" style="font-size:10px">${{ti(p.trend)}} ${{p.change}}</span></div>`}});
document.getElementById('ticker').innerHTML=tk;
let h='';
const coal=D.coal||{{}};
if(coal.briefHeadline){{h+=`<div class="sl">⛏ 석탄 — FULL DETAIL<div class="sll"></div></div><div class="cd cb"><div class="ch">${{coal.briefHeadline}}</div><p class="ct">${{coal.briefText||''}}</p></div>`}}
(coal.articles||[]).forEach(a=>{{const c=a.relevance==='HIGH'?'tH':a.relevance==='MEDIUM'?'tM':'tL';const l=a.relevance==='HIGH'?'🔴 핵심':a.relevance==='MEDIUM'?'🟡 주목':'⚪ 참고';h+=`<div class="cd"><div style="display:flex;align-items:center;gap:8px;margin-bottom:8px"><span class="tg ${{c}}">${{l}}</span><span style="font-size:11px;color:#44403c;font-family:monospace">${{a.source}} · ${{a.date}}</span></div><h3 style="font-family:Georgia,serif;font-size:15px;color:#f0ece7;line-height:1.35;margin-bottom:7px">${{a.title}}</h3><p style="font-size:13px;line-height:1.7;color:#78716c">${{a.summary}}</p>${{a.investmentImplication?`<div class="imp"><b>💡 시사점</b><p>${{a.investmentImplication}}</p></div>`:''}}</div>`}});
(coal.leadingIndicators||[]).forEach(li=>{{h+=`<div class="li"><div class="lit"><span class="lin">${{li.name}}</span><span class="liv">${{li.value}}</span></div><p class="liw">→ ${{li.why}}</p><div class="lis">${{li.source}} · ${{li.date}}</div></div>`}});
const secs=[['copper','🔶 구리'],['uranium','☢️ 우라늄'],['samsung','💾 삼성전자'],['lsElectric','⚡ LS Electric'],['hyundai','🚗 현대차'],['kBeauty','💄 K-Beauty'],['teslaTech','🤖 Tesla+테크'],['macro','🌐 매크로']];
secs.forEach(([k,icon])=>{{const s=D[k];if(!s)return;const id='ex_'+k;h+=`<div class="ex" id="${{id}}"><div class="exh" onclick="toggle('${{id}}')"><div><div class="ext">${{icon}}</div><div class="exs">${{s.headline||''}}</div></div><span class="exa" id="${{id}}_a">▼</span></div><div class="exb" id="${{id}}_b"><div class="cd"><p class="ct">${{s.summary||''}}</p>${{s.peers?`<p style="font-size:12px;color:#78716c;margin-top:8px"><strong style="color:#faf6f1">피어그룹:</strong> ${{s.peers}}</p>`:''}}</div>${{(s.leadingIndicators||s.indicators||[]).map(li=>`<div class="li"><div class="lit"><span class="lin">${{li.name}}</span><span class="liv">${{li.value}}</span></div><p class="liw">→ ${{li.why}}</p><div class="lis">${{li.source}} · ${{li.date}}</div></div>`).join('')}}</div></div>`}});
if(D.miniReport){{h+=`<div class="sl">🔥 미니 리포트<div class="sll"></div></div><div class="mr"><div class="ch">${{D.miniReport.title||''}}</div><p class="ct">${{D.miniReport.content||''}}</p></div>`}}
document.getElementById('main').innerHTML=h;
function toggle(id){{const b=document.getElementById(id+'_b');const a=document.getElementById(id+'_a');if(b.style.display==='block'){{b.style.display='none';a.style.transform='rotate(0)'}}else{{b.style.display='block';a.style.transform='rotate(180deg)'}}}}
</script>
</body>
</html>'''

    os.makedirs("dist", exist_ok=True)
    with open("dist/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Done: dist/index.html ({len(html)//1024}KB)")

if __name__ == "__main__":
    main()
