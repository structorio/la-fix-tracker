const LB=window.LEADERBOARD,BR=window.LA_BREAKDOWN,META=window.CITIES_META,$=id=>document.getElementById(id);
const f=v=>v==null?"–":v,pct=v=>v==null?"–":v+"%";
function cell(s){return `<td>${f(s.median_days)}</td><td>${pct(s.pct_7d)}</td><td>${pct(s.pct_30d)}</td><td>${pct(s.same_day_pct)}</td><td>${s.requests.toLocaleString()}</td><td>${s.open.toLocaleString()}</td>`}
const HD="<th>Median days</th><th>≤7 days</th><th>≤30 days</th><th>Same-day</th><th>Requests</th><th>Still open</th>";
function sortable(t){t.querySelectorAll("th").forEach((th,i)=>th.onclick=()=>{const b=t.tBodies[0],r=[...b.rows],d=th.dataset.d=th.dataset.d=="a"?"d":"a";
 const v=x=>{const s=x.cells[i].textContent.replace(/[,%]/g,"");return isNaN(parseFloat(s))?(s=="–"?Infinity:s):parseFloat(s)};
 r.sort((a,c)=>(v(a)>v(c)?1:v(a)<v(c)?-1:0)*(d=="a"?1:-1)).forEach(x=>b.appendChild(x))})}
function catSel(cb){const s=$("cat");if(!s)return;s.innerHTML="<option value=''>All five categories</option>"+LB.categories.map(c=>`<option>${c}</option>`).join("");s.onchange=cb}
const pick=(s,c)=>c?(s.by_category||{})[c]:s;
if($("updated"))$("updated").textContent=`Updated ${LB.generated.slice(0,10)} · requests created since ${LB.since} (last ${LB.window_days} days)`;
if($("board")){const R=()=>{const c=$("cat").value;let i=0;
 const rows=LB.cities.map(s=>[s,pick(s,c)]).filter(x=>x[1]).sort((a,b)=>(b[0].ranked-a[0].ranked)||((a[1].median_days??1e9)-(b[1].median_days??1e9)));
 $("board").innerHTML=`<table><thead><tr><th>#</th><th>City</th><th>County</th>${HD}<th>Per 1k residents</th><th>Source</th></tr></thead><tbody>${rows.map(([s,x])=>`<tr><td>${s.ranked&&x.requests>=30?++i:"–"}</td><td><a href="city.html?c=${encodeURIComponent(s.name)}">${s.name}</a></td><td>${s.county}</td>${cell(x)}<td>${s.population?(1000*x.requests/s.population).toFixed(1):"–"}</td><td class=muted>${s.source.split(" (")[0]}</td></tr>`).join("")}</tbody></table>`;sortable($("board").querySelector("table"))};catSel(R);R()}
if($("city")){const n=new URLSearchParams(location.search).get("c"),s=LB.cities.find(x=>x.name==n);
 $("city").innerHTML=!s?"<p>City not found. <a href='index.html'>Back to leaderboard</a></p>":`<h2>${s.name} <span class=pill>${s.county} County</span></h2><p class=muted>Source: ${s.source} · Population ${s.population?s.population.toLocaleString():"n/a"} · last ${LB.window_days} days, updated ${LB.generated.slice(0,10)}</p>
 <table><thead><tr><th>Category</th>${HD}</tr></thead><tbody><tr><td><b>All five</b></td>${cell(s)}</tr>${Object.entries(s.by_category).map(([c,x])=>`<tr><td>${c}</td>${cell(x)}</tr>`).join("")}</tbody></table>${s.name=="Los Angeles"?"<p><a href='la.html'>See LA by council district and neighborhood →</a></p>":""}${s.ranked?"":"<p class=muted>Too few requests to rank (needs at least 30).</p>"}`;document.title=s?s.name+" · LA Fix Tracker":document.title}
if($("cd")){const T=(id,list,c,q="")=>{$(id).innerHTML=`<table><thead><tr><th>Name</th>${HD}</tr></thead><tbody>${list.filter(s=>s.name.toLowerCase().includes(q)).map(s=>[s,pick(s,c)]).filter(x=>x[1]).sort((a,b)=>(a[1].median_days??1e9)-(b[1].median_days??1e9)).map(([s,x])=>`<tr><td>${s.name}</td>${cell(x)}</tr>`).join("")}</tbody></table>`;sortable($(id).querySelector("table"))};
 const R=()=>{const c=$("cat").value;T("cd",BR.council_districts,c);T("nc",BR.neighborhood_councils,c,$("q").value.toLowerCase())};catSel(R);$("q").oninput=R;R()}
if($("nodata")){const have=new Set(LB.cities.map(c=>c.name)),N=META.portal_notes,list=META.cities.filter(c=>!have.has(c.name)||!LB.cities.find(x=>x.name==c.name).ranked);
 $("nd-count").textContent=`${list.length} of ${META.cities.length} cities in LA and Orange counties (checked ${META.checked}). LA County's unincorporated areas (The Works app) and OC Public Works don't publish open request data either.`;
 $("nodata").innerHTML=`<table><thead><tr><th>City</th><th>County</th><th>Population</th><th>What we found</th></tr></thead><tbody>${list.map(c=>`<tr><td>${c.name}</td><td>${c.county}</td><td>${c.population?c.population.toLocaleString():"–"}</td><td class=muted>${N[c.name]||(have.has(c.name)?"Only a handful of SeeClickFix resident reports; no official open feed":"No public open feed found")}</td></tr>`).join("")}</tbody></table>`;sortable($("nodata").querySelector("table"))}
// Config: set these when the backends exist.
const SIGNUP_ENDPOINT=""; // e.g. Resend audience endpoint; receives POST JSON {email}
const TALLY_FORM_URL=""; // e.g. https://tally.so/r/xxxx
const CONTACT="hello@kordaris.com";
if(TALLY_FORM_URL){const l=document.getElementById("suggest-link");l.href=TALLY_FORM_URL;l.target="_blank";l.rel="noopener"}
document.getElementById("nl-form").addEventListener("submit",async e=>{e.preventDefault();
 const em=document.getElementById("nl-email"),m=document.getElementById("nl-msg"),v=em.value.trim();
 if(!em.checkValidity()||!v){m.textContent="Please enter a valid email address.";em.focus();return}
 if(!SIGNUP_ENDPOINT){m.innerHTML=`Signups open soon — email <a href="mailto:${CONTACT}?subject=Newsletter%20signup&body=Please%20add%20me%3A%20${encodeURIComponent(v)}">${CONTACT}</a> and we'll add you.`;return}
 m.textContent="Subscribing…";
 try{const r=await fetch(SIGNUP_ENDPOINT,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email:v})});
  if(!r.ok)throw 0;m.textContent="Thanks! You're subscribed.";em.value=""}
 catch(_){m.innerHTML=`Something went wrong. Email <a href="mailto:${CONTACT}">${CONTACT}</a> to join.`}});
