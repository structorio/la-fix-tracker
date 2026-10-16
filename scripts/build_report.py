"""Generate 'Report it here' pages from data/report_channels.json."""
import json,re,os,html
R=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d=json.load(open(f'{R}/data/report_channels.json'))
lb={c['name'] for c in json.load(open(f'{R}/data/leaderboard.json'))['cities']}
NAV='<nav><a href="{p}index.html">Leaderboard</a><a href="{p}la.html">LA neighborhoods</a><a href="{p}report.html">Report it here</a><a href="{p}no-data.html">Cities without open data</a><a href="{p}methodology.html">Methodology</a></nav>'
e=html.escape
slug=lambda n:re.sub(r'[^a-z0-9]+','-',n.lower().replace('ñ','n')).strip('-')
def head(t,desc,p): return f'<!doctype html><html><head><meta charset="utf-8"><title>{e(t)}</title><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="{e(desc)}"><link rel="stylesheet" href="{p}style.css"></head><body>\n<header><h1>🛠️ LA Fix Tracker</h1><p>Report it here: the official way to report potholes, streetlights, graffiti and dumping in every LA and Orange County city.</p></header>\n'+NAV.format(p=p)
def body(r,p):
  s=[]
  if r['app']: s.append(f"<p><b>App:</b> {e(r['app'])}</p>")
  if r['vendor']: s.append(f"<p><b>Platform:</b> {e(r['vendor'])}</p>")
  if r['channels']:
    s.append('<ul>'+''.join(f'<li><a href="{e(c["url"])}" rel="nofollow noopener">{e(c["label"])}</a>'+('' if c['verified'] else ' <span class="muted">(unverified: the link didn\'t load for our checker)</span>')+'</li>' for c in r['channels'])+'</ul>')
  else: s.append('<p>Online reporting channel: <b>not found yet</b>. Try the city\'s main website or city hall phone below.</p>')
  if r['phone']: s.append(f"<p><b>Phone:</b> {e(r['phone'])}"+(f" <span class='muted'>({e(r['phone_note'])})</span>" if r.get('phone_note') else '')+'</p>')
  if r['email']: s.append(f"<p><b>Email:</b> {e(r['email'])}</p>")
  if r['official_site']: s.append(f'<p><b>Official site:</b> <a href="{e(r["official_site"])}" rel="nofollow noopener">{e(r["official_site"])}</a></p>')
  s.append(f'<p>For emergencies call 911.</p>')
  if r['name'] in lb: s.append(f'<p>📊 <a href="{p}city.html?c={e(r["name"])}">See how fast {e(r["name"])} fixes things on the leaderboard</a></p>')
  elif r['type']=='city': s.append(f'<p class="muted">{e(r["name"])} doesn\'t publish fix-time data yet, so it isn\'t on the <a href="{p}index.html">leaderboard</a>. <a href="{p}no-data.html">Why?</a></p>')
  s.append(f"<p class='muted'>Last checked {r['last_checked']}. Sources: "+', '.join(f'<a href="{e(u)}" rel="nofollow">{i+1}</a>' for i,u in enumerate(r['sources']))+'. Spot something wrong? <a href="mailto:hello@kordaris.com?subject=Report%20channel%20correction">Tell us</a>.</p>')
  return ''.join(s)
FOOT='<footer>Links point to official city channels; LA Fix Tracker is not affiliated with any city. Data in <a href="{p}data/report_channels.json">report_channels.json</a>.</footer></body></html>'
os.makedirs(f'{R}/report',exist_ok=True)
P=sorted(d['places'],key=lambda r:(r['county'],r['type']!='city',r['name']))
for r in P:
  n=r['name'];where=n if r['type']=='city' else 'unincorporated LA County'
  t=f'How to report a pothole in {where} | LA Fix Tracker'
  desc=f'Official ways to report potholes, broken streetlights, graffiti and illegal dumping in {where}, {r["county"]} County: app, web form and phone.'
  open(f'{R}/report/{slug(n)}.html','w').write(head(t,desc,'../')+f'<main class="wrap" style="display:block"><p><a href="../report.html">← All cities</a></p><h2>How to report a pothole in {e(where)}</h2><p>Potholes, streetlights, graffiti, sidewalks and illegal dumping in {e(where)} ({e(r["county"])} County) go to the channels below.</p>'+body(r,'../')+'</main>'+FOOT.format(p='../'))
rows=[]
for cty in ('Los Angeles','Orange'):
  L=[r for r in P if r['county']==cty];f=sum(r['status']=='found' for r in L)
  rows.append(f'<h3>{cty} County <span class="muted">({f} of {len(L)} with an online channel found)</span></h3><ul class="rlist">')
  for r in L: rows.append(f'<li data-n="{e(r["name"].lower())}"><a href="report/{slug(r["name"])}.html">{e(r["name"])}</a> <span class="muted">{e(r["app"] or (r["channels"][0]["label"] if r["channels"] else "not found yet"))}</span></li>')
  rows.append('</ul>')
open(f'{R}/report.html','w').write(head('How to report a pothole in your LA or Orange County city | LA Fix Tracker','Find the official app, web form and phone number to report potholes, streetlights, graffiti and dumping in all 88 LA County and 34 Orange County cities.','')+'<main class="wrap" style="display:block"><h2>Report it here</h2><p>Every LA County and Orange County city, plus unincorporated LA County, with its official app, web form and phone number for reporting problems.</p><label>Find your city: <input id="q" type="search" placeholder="e.g. Placentia"></label>'+''.join(rows)+'</main><script>q.oninput=()=>{const v=q.value.toLowerCase();document.querySelectorAll(".rlist li").forEach(l=>l.hidden=!l.dataset.n.includes(v))}</script>'+FOOT.format(p=''))
print('pages',len(P))
