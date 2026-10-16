import json,re,requests,concurrent.futures as cf
from bs4 import BeautifulSoup
from urllib.parse import urljoin
m=json.load(open('/workspace/la-fix-tracker/data/cities_meta.json'))['cities']
w=json.load(open('wd_sites.json'))
fix={'Industry':'https://www.cityofindustry.org','Los Angeles':'https://lacity.gov','Pasadena':'https://www.cityofpasadena.net','Anaheim':'https://www.anaheim.net','Fullerton':'https://www.cityoffullerton.com','Irvine':'https://www.cityofirvine.org'}
H={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36'}
KW=re.compile(r'report (a|an)? ?(issue|problem|concern|pothole)|311|request (a )?service|service request|submit a request|request tracker|seeclickfix|gorequest|govoutreach|mycivic|citysourced|publicstuff|qalert|access ?\w+|\bapp\b|concern|cityworks|my ?\w+ ?(app|connect)',re.I)
VEND=re.compile(r'seeclickfix|govoutreach|mycivic|citysourced|publicstuff|qscend|qalert|myla311|crm\.|gogov|vision|accela|cityworks|apps\.apple|play\.google',re.I)
def get(u):
  import subprocess,types
  try:
    p=subprocess.run(['curl','-sL','--compressed','-m','40','-A','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36','-H','Accept: text/html,*/*','-H','Accept-Language: en-US','-w','\n%{http_code} %{url_effective}',u],capture_output=True,timeout=45)
    t=p.stdout.decode('utf8','ignore');body,_,last=t.rpartition('\n');code,url=last.split(' ',1)
    return types.SimpleNamespace(text=body,status_code=int(code),url=url)
  except Exception as e: return None
def do(c):
  n=c['name'];s=[x for x in w.get(n,[]) if x] ;home=fix.get(n) or (s[0] if s else '')
  res={'name':n,'county':c['county'],'home':home,'home_ok':False,'links':[],'phones':[]}
  r=get(home)
  if not r or r.status_code!=200 or len(r.text)<500: return res
  res['home_ok']=True;res['home']=r.url
  soup=BeautifulSoup(r.text,'html.parser');seen=set()
  for a in soup.find_all('a',href=True):
    t=' '.join(a.get_text(' ').split())[:80];h=urljoin(r.url,a['href'])
    if h.startswith('http') and (KW.search(t) and len(t)<60 or VEND.search(h)) and h not in seen and not re.search(r'facebook|twitter|instagram|youtube|linkedin|nextdoor',h):
      seen.add(h);res['links'].append([t,h])
  res['phones']=list(dict.fromkeys(re.findall(r'\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}',soup.get_text(' '))))[:4]
  return res
with cf.ThreadPoolExecutor(10) as ex: out=list(ex.map(do,m))
json.dump(out,open('crawl.json','w'),indent=1)
print(sum(o['home_ok'] for o in out), sum(bool(o['links']) for o in out))
