import json,re,subprocess,concurrent.futures as cf
T='2026-10-16'
o=json.load(open('crawl.json'))
GOOD=re.compile(r'report|service request|request (a )?service|311|\bapp\b|concern|go hermosa|gardena direct|orange 24|request tracker|make a request',re.I)
BAD=re.compile(r'accessib|ada\b|records|noise|coyote|vision|television|parking ticket|survey|ad-hoc|public notices|odor',re.I)
VEND={'govoutreach':'GOGov / GORequest','citysourced':'CitySourced (Granicus)','publicstuff':'PublicStuff (Accela)','accela':'Accela Citizen Access','comcate':'Comcate','tylerportico':'Tyler Technologies','mycivic':'MyCivic (Tyler)','seeclickfix':'SeeClickFix (CivicPlus)','myla311':'MyLA311 (Salesforce)','311.santamonica':'Santa Monica 311','311.burbankca':'Burbank 311'}
def vendor(u):
  for k,v in VEND.items():
    if k in u: return v
  return None
M={ # manual research via web search 2026-10-16
'Placentia':dict(app='iPlacentia',channels=[['iPlacentia app','https://www.placentia.org/751/iPlacentia-App'],['GORequest web form','https://user.govoutreach.com/placentiaca/support.php']],phone='(714) 993-8131',vendor='GOGov / GORequest'),
'Yorba Linda':dict(app='MyCivic 311',channels=[['MyCivic 311 web portal','https://www.yorbalindaca.gov/828/MyCivic-311-Web-Portal'],['MyCivic 311 service requests','https://www.yorbalindaca.gov/827/MyCivic-311-Service-Requests']],phone='714-386-3140 (Public Works); code enforcement hotline 714-961-7138',email='mycivic311@yorbalindaca.gov',vendor='MyCivic (Tyler Technologies)'),
'Anaheim':dict(app='My Anaheim / Anaheim Anytime',channels=[['Anaheim Anytime','https://www.anaheim.net/2128/Anaheim-Anytime'],['My Anaheim app','https://www.anaheim.net/1409/My-Anaheim-App']],phone='311 or (714) 765-4311',email='mobilesupport@anaheim.net (app support)'),
'Pasadena':dict(app='Pasadena CSC',channels=[['City Service Center','https://www.cityofpasadena.net/city-service-center/'],['Pasadena CSC app','https://www.cityofpasadena.net/city-service-center/mobile-app/']],phone='626-744-7311',email='csc@cityofpasadena.net',vendor='GOGov / GORequest'),
'Santa Clarita':dict(app='City of Santa Clarita app (Resident Service Center)',channels=[['Resident Service Center','https://user.govoutreach.com/santaclarita/support.php']],vendor='GOGov / GORequest'),
'Pomona':dict(app='Pomona Go',channels=[['Pomona Go web portal','https://pomonaca.citysourced.com/servicerequests/create'],['About Pomona Go','https://www.pomonaca.gov/our-city/online-services/new-pomona-go']],phone='909-620-3665 (potholes); after hours 909-282-2835',vendor='CitySourced (Granicus)'),
'Palmdale':dict(app='My Palmdale',channels=[['Report maintenance issue form','https://www.cityofpalmdaleca.gov/1234/Maintenance-Issue'],['My Palmdale (Google Play)','https://play.google.com/store/apps/details?id=com.govoutreach.palmdalecityca']],phone='661-267-5338 (Maintenance)',vendor='GOGov'),
}
recs=[]
for x in o:
  n=x['name'];r={'name':n,'county':x['county'],'type':'city','official_site':x['home'] or None,'app':None,'vendor':None,'channels':[],'phone':None,'email':None,'sources':[],'last_checked':T,'status':'not found yet'}
  if x['home_ok']:
    seen=set()
    for t,u in x['links']:
      u=u.strip()
      if GOOD.search(t) and not BAD.search(t) or vendor(u):
        if u.rstrip('/')==x['home'].rstrip('/') or u in seen: continue
        seen.add(u);r['channels'].append({'label':t or 'Report link','url':u})
    r['channels']=r['channels'][:4]
    r['phone']=(x['phones'] or [None])[0]; 
    if r['phone']: r['phone_note']='main city hall number from homepage'
    r['sources'].append(x['home'])
    for c in r['channels']:
      v=vendor(c['url']); r['vendor']=r['vendor'] or v
  if n in M:
    m=M[n];r['channels']=[{'label':a,'url':b} for a,b in m['channels']];r.pop('phone_note',None)
    for k in('app','phone','email','vendor'):
      if m.get(k): r[k]=m[k]
    r['sources']=[c['url'] for c in r['channels']]
  if r['channels']: r['status']='found'
  recs.append(r)
recs.append({'name':'Unincorporated LA County','county':'Los Angeles','type':'unincorporated','official_site':'https://pw.lacounty.gov','app':'The Works (LA County Public Works)','vendor':None,'channels':[{'label':'The Works','url':'https://dpw.lacounty.gov/theWorks/'},{'label':'Report a Problem (Public Works)','url':'https://content.pw.lacounty.gov/explore-public-works/report-a-problem/'}],'phone':'(626) 458-3981 (Road Maintenance)','email':None,'sources':['https://dpw.lacounty.gov/theWorks/'],'last_checked':T,'status':'found'})
def chk(u):
  p=subprocess.run(['curl','-sL','-o','/dev/null','-m','30','-A','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36','-w','%{http_code}',u],capture_output=True,text=True);return p.stdout
urls=sorted({c['url'] for r in recs for c in r['channels']})
with cf.ThreadPoolExecutor(12) as ex: st=dict(zip(urls,ex.map(chk,urls)))
for r in recs:
  for c in r['channels']: c['verified']=st[c['url']]=='200'; c['http']=st[c['url']]
json.dump({'checked':T,'note':'Channels gathered from each city\'s official homepage links (automated crawl) plus targeted web research. "verified" = URL returned HTTP 200 from our checker on last_checked. Cities whose sites blocked or timed out our checker are "not found yet".','places':recs},open('/workspace/la-fix-tracker/data/report_channels.json','w'),indent=1,ensure_ascii=False)
f=[r for r in recs if r['status']=='found'];print(len(recs),len(f),sum(c['verified'] for r in recs for c in r['channels']),len(urls))
for cty in ('Los Angeles','Orange'): print(cty,sum(1 for r in f if r['county']==cty),sum(1 for r in recs if r['county']==cty))
print([ (c['url'],c['http']) for r in recs for c in r['channels'] if not c['verified']])
