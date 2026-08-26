"""
============================================================
  ALEX STOR BOT — AI Tools Shop Promotion Bot (Compact v3)
  Single-file, easy Termux deploy
============================================================
"""
import os,json,re,time,random,threading,logging
from datetime import datetime,timedelta
from io import BytesIO
from flask import Flask,redirect,Response,render_template_string,request
import telebot
from telebot.types import InlineKeyboardButton,InlineKeyboardMarkup,InputMediaPhoto,InputMediaVideo
from apscheduler.schedulers.background import BackgroundScheduler

logging.basicConfig(level=logging.INFO,format="%(asctime)s %(message)s")
log=logging.getLogger("alex")

# ---- CONFIG (env vars se aate hain — Render pe environment variables set karna) ----
TOKEN=os.getenv("BOT_TOKEN","")
OWNER=int(os.getenv("OWNER_ID","0"))
DASH_USER=os.getenv("DASH_USER","admin")
DASH_PASS=os.getenv("DASH_PASS","alex@stor2026")
# Render PORT env var provide karta hai; local mein 5000 use
DASH_PORT=int(os.getenv("PORT",os.getenv("DASH_PORT","10000")))
# Public URL click tracking ke liye (Render RENDER_EXTERNAL_URL deta hai)
PUBLIC_URL=os.getenv("RENDER_EXTERNAL_URL",os.getenv("PUBLIC_URL",f"http://127.0.0.1:{DASH_PORT}")).rstrip("/")
TZ=os.getenv("TZ","Asia/Karachi")

# .env file support (local run ke liye)
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env_path):
    for _line in open(_env_path):
        _line=_line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k,_v=_line.split("=",1); os.environ.setdefault(_k.strip(),_v.strip())
    TOKEN=os.getenv("BOT_TOKEN", TOKEN)
    OWNER=int(os.getenv("OWNER_ID", str(OWNER)))
DATA=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data.json")
bot=telebot.TeleBot(TOKEN,threaded=True)
# Timezone-safe init (Termux Python 3.14 mein tzdata chahiye)
try:
    sched=BackgroundScheduler(timezone=TZ)
except Exception as e:
    log.warning(f"Timezone init failed ({e}), falling back to UTC. Run: pkg install tzdata -y")
    sched=BackgroundScheduler(timezone="UTC")
app=Flask(__name__)
STATE={};BOTLOCK={}

def load():
    if os.path.exists(DATA):
        try: return json.load(open(DATA,encoding="utf-8"))
        except: pass
    return {"on":1,"typing":1,"delay":1.0,"jitter":3.0,"randdelay":1,"quiet":{"on":0,"s":"23:00","e":"08:00"},
            "presets":{},"defpreset":"","rotate":0,"targets":{},"blk_u":[],"blk_w":[],"kw":[],
            "queue":[],"qauto":0,"qhrs":24,"stats":{"sent":0,"fail":0,"per":{},"clicks":0,"day":{}},
            "logs":[],"slugs":{},"admins":[OWNER],"react":{}}
def save(): json.dump(D,open(DATA,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
D=load()
if OWNER and OWNER not in D["admins"]: D["admins"].append(OWNER)
save()

# ---- helpers ----
def is_admin(u): return u and (u.id in D["admins"])
def owner_only(f):
    def w(m,*a,**k):
        if m.from_user and m.from_user.id==OWNER: return f(m,*a,**k)
        bot.reply_to(m,"Sirf owner.")
    return w
def admin_only(f):
    def w(m,*a,**k):
        if is_admin(m.from_user): return f(m,*a,**k)
        bot.reply_to(m,"Admin chahiye.")
    return w
def parse_target(r):
    if not r:return None
    r=r.strip()
    m=re.match(r"^@([A-Za-z0-9_]{3,})$",r)
    if m:return "@"+m.group(1)
    m=re.match(r"^(?:https?://)?(?:www\.)?t\.me/([A-Za-z0-9_]{3,})/?$",r)
    if m:return "@"+m.group(1)
    if r.lstrip("-").isdigit():return int(r)
    return None
def resolve(t):
    if isinstance(t,str) and t.startswith("@"):
        try:return bot.get_chat(t).id
        except:return None
    return t
def kb(btns):
    if not btns:return None
    k=InlineKeyboardMarkup(row_width=1)
    for b in btns:k.add(InlineKeyboardButton(b["t"],url=b["u"]))
    return k
def addlog(e,cid=0,ok=1):
    ts=datetime.now().isoformat(timespec="seconds")
    D["logs"].insert(0,{"ts":ts,"e":e[:200],"c":str(cid) if cid else "","ok":ok})
    D["logs"]=D["logs"][:300]
    if ok:
        D["stats"]["sent"]+=1
        if cid:
            g=str(cid);D["stats"]["per"][g]=D["stats"]["per"].get(g,0)+1
    else: D["stats"]["fail"]+=1
    save()
def quiet():
    if not D["quiet"]["on"]:return False
    n=datetime.now().strftime("%H:%M");s,e=D["quiet"]["s"],D["quiet"]["e"]
    return (s<=n<=e) if s<=e else (n>=s or n<=e)
def ratelimited(g):
    rl=g.get("rl") if isinstance(g,dict) else None
    if not rl:return False
    ls=g.get("ls");
    if not ls:return False
    try:return (datetime.now()-datetime.fromisoformat(ls))<timedelta(minutes=rl)
    except:return False
def blocked(m,g):
    if m.from_user and m.from_user.is_bot:return True
    if BOTLOCK.get(m.chat.id,0) and time.time()-BOTLOCK[m.chat.id]<3:return True
    if m.from_user and m.from_user.id in D["blk_u"]:return True
    t=(m.text or m.caption or "").lower()
    return any(w in t for w in D["blk_w"])
def pick_preset(cid=None):
    if cid:
        g=D["targets"].get(str(cid),{})
        pn=g.get("p")
        if pn and pn in D["presets"]:return D["presets"][pn]
    if D["rotate"] and D["presets"]:return D["presets"][random.choice(list(D["presets"]))]
    dp=D["defpreset"]
    return D["presets"].get(dp)
def jitter(b,j): return max(0.2,b+random.uniform(-j,j))
def apply_tmpl(t,c):
    if not t:return t
    now=datetime.now();ctx={"date":now.strftime("%Y-%m-%d"),"time":now.strftime("%H:%M"),
        "first_name":"friend","username":"","group":"","msg":""}
    ctx.update(c or {})
    def r(m): return str(ctx.get(m.group(1).lower(),m.group(0)))
    return re.sub(r"\{([^}]+)\}",r,t)
import hashlib
def rewrite_urls(text,cid):
    if not text:return text
    base=f"{PUBLIC_URL}/r/"
    def rep(m):
        u=m.group(0).rstrip(").,;");trail=m.group(0)[len(u):]
        slug=hashlib.md5(u.encode()).hexdigest()[:8]
        D["slugs"][slug]=u;return base+slug+f"?s={cid}"+trail
    return re.sub(r"https?://[^\s<>\"']+",rep,text)

def send_one(cid,p,ctx=None):
    txt=apply_tmpl(p.get("t",""),ctx or {})
    txt=rewrite_urls(txt,cid)
    kb1=kb(p.get("b"))
    pm=p.get("pm","HTML")
    silent=p.get("silent",0);nopv=p.get("nopv",0)
    fid=p.get("f")
    kw=dict(reply_markup=kb1,disable_web_page_preview=bool(nopv),parse_mode=pm,disable_notification=bool(silent))
    if D["typing"]:
        try:
            act={"photo":"upload_photo","video":"upload_video","document":"upload_document","audio":"upload_audio","voice":"record_audio"}.get(p["k"],"typing")
            bot.send_chat_action(cid,act);time.sleep(1)
        except:pass
    def call(f,*a,**k):
        for i in range(5):
            try:return f(*a,**k)
            except telebot.apihelper.ApiTelegramException as e:
                if "Too Many Requests" in str(e):
                    mm=re.search(r"retry after (\d+)",str(e));time.sleep(int(mm.group(1))+1 if mm else 2);continue
                raise
            except Exception as e:
                if i==4:raise;time.sleep(2*(i+1))
    if p["k"]=="text":return call(bot.send_message,cid,txt,**kw)
    if p["k"]=="photo":return call(bot.send_photo,cid,fid,caption=txt or None,**kw)
    if p["k"]=="video":return call(bot.send_video,cid,fid,caption=txt or None,**kw)
    if p["k"]=="document":return call(bot.send_document,cid,fid,caption=txt or None,**kw)
    if p["k"]=="audio":return call(bot.send_audio,cid,fid,caption=txt or None,**kw)
    if p["k"]=="voice":return call(bot.send_voice,cid,fid,caption=txt or None,**kw)
    if p["k"]=="album":
        med=[];items=p.get("m",[]);
        if not items:raise Exception("empty album")
        for i,it in enumerate(items):
            cap=txt if i==0 else None
            if it["k"]=="photo":med.append(InputMediaPhoto(it["f"],caption=cap,parse_mode=pm))
            elif it["k"]=="video":med.append(InputMediaVideo(it["f"],caption=cap,parse_mode=pm))
        ms=call(bot.send_media_group,cid,med,disable_notification=bool(silent))
        if kb1:
            try:call(bot.send_message,cid,"⬇️",reply_markup=kb1,disable_notification=bool(silent))
            except:pass
        return ms[0] if ms else None
    raise Exception("unknown "+p["k"])

def send_preset(cid,p,pin=0,sd=0,react=None,ctx=None,trig_mid=None):
    if react and trig_mid:
        try:bot.set_message_reaction(cid,trig_mid,[telebot.types.ReactionTypeEmoji(react)],is_big=False);time.sleep(0.4)
        except:pass
    try:m=send_one(cid,p,ctx=ctx)
    except Exception as e:
        addlog(f"FAIL {p.get('name','?')}: {str(e)[:80]}",cid,0);return False
    mid=m.message_id if hasattr(m,"message_id") else None
    if pin and mid:
        try:bot.pin_chat_message(cid,mid,disable_notification=True)
        except:pass
    if sd and mid:
        def dl(c,mm,d):
            time.sleep(d)
            try:bot.delete_message(c,mm)
            except:pass
        threading.Thread(target=dl,args=(cid,mid,sd),daemon=True).start()
    g=D["targets"].get(str(cid),{});g["ls"]=datetime.now().isoformat(timespec="seconds")
    D["targets"][str(cid)]=g
    addlog(f"SENT {p.get('name','?')} ({p['k']})",cid,1)
    BOTLOCK[cid]=time.time();save();return True

def send_to_targets(p,tgt=None,ctx=None):
    if not D["on"]:return "🔴 Master OFF"
    if not p:return "❌ No preset"
    if quiet():return f"🌙 Quiet hours"
    # Build list of target dicts properly (use .get with fallback instead of direct [] access)
    if tgt:
        rid=resolve(tgt)
        if rid is None:return "❌ Target resolve failed"
        ts=[D["targets"].get(str(rid),{"chat_id":rid,"title":str(rid)})]
    else:
        ts=[t for t in D["targets"].values() if t.get("a",1)]
    if not ts:return "❌ Koi active target nahi"
    ok=0;fail=0
    for t in ts:
        cid=t.get("chat_id")
        if cid is None:continue
        # Resolve @username to numeric ID if needed
        if isinstance(cid,str) and cid.startswith("@"):
            cid=resolve(cid)
            if cid is None:fail+=1;continue
            # Ensure numeric ID is the stored key
            if str(cid) not in D["targets"]:
                t["chat_id"]=cid
                D["targets"][str(cid)]=t
                save()
        dly=float(t.get("d") or D["delay"])
        if D["randdelay"]:dly=jitter(dly,D["jitter"])
        if dly>0:time.sleep(dly)
        if send_preset(cid,p,pin=bool(t.get("pin",0)),sd=t.get("sd",0),react=t.get("r"),ctx=ctx):ok+=1
        else:fail+=1
        time.sleep(0.4)
    return f"✅ Done: {ok} sent, {fail} fail"

def pick_and_send_preset(cid,m):
    g=D["targets"].get(str(cid),{})
    p=None;reason="auto"
    # keyword
    mtxt=(m.text or m.caption or "").lower()
    for k in D["kw"]:
        if k.get("c") and str(k["c"])!=str(cid):continue
        kw=k["k"].lower()
        if (k.get("m","contains")=="exact" and mtxt.strip()==kw) or (k.get("m","contains")=="contains" and kw in mtxt):
            if k["p"] in D["presets"]:p=D["presets"][k["p"]];reason=f"kw '{kw}'";break
    if not p and not blocked(m,g):
        if ratelimited(g):return
        p=pick_preset(cid)
    if not p:return
    ctx={"first_name":(m.from_user.first_name if m.from_user else "friend") or "friend",
         "username":f"@{m.from_user.username}" if m.from_user and m.from_user.username else "",
         "group":m.chat.title or "","msg":m.text or m.caption or ""}
    dly=float(g.get("d") or D["delay"])
    if D["randdelay"]:dly=jitter(dly,D["jitter"])
    def run():
        time.sleep(dly)
        send_preset(cid,p,pin=bool(g.get("pin",0)),sd=g.get("sd",0),react=g.get("r"),ctx=ctx,trig_mid=m.message_id)
    threading.Thread(target=run,daemon=True).start()

# ============ COMMANDS ============

@bot.message_handler(commands=["help2"])
@admin_only
def h_help2(m):
    txt="""<b>📖 Complete Command List</b>

<b>Make Ads (Presets):</b>
/addpreset &lt;name&gt; — create new ad (choose type, send content)
/presets — list all ads
/delpreset &lt;name&gt; — delete an ad
/setdefault &lt;name&gt; — set default ad
/preview &lt;name&gt; — preview an ad
/presetflag &lt;n&gt; silent on|off — send silently (no notification)
/presetflag &lt;n&gt; noprev on|off — disable link preview
/presetflag &lt;n&gt; html|md — change text format
/presetflag &lt;n&gt; btns Text|url,Text2|url2 — add clickable buttons

<b>Groups/Channels (Targets):</b>
/addtarget @username | -100xxx | t.me/link — add target
/bulkadd — add many targets at once (one per line)
/targets — list all targets
/deltarget &lt;n&gt; — delete target
/chatid — get ID of current chat
/tcfg &lt;n&gt; auto on|off — enable/disable for target n
/tcfg &lt;n&gt; preset &lt;name&gt;|off — specific ad for this target
/tcfg &lt;n&gt; delay &lt;sec&gt;|off — custom delay for this target
/tcfg &lt;n&gt; rl &lt;min&gt;|off — rate limit (max 1 per X min)
/tcfg &lt;n&gt; pin on|off — pin after send
/tcfg &lt;n&gt; sd &lt;sec&gt;|off — auto-delete after X seconds
/tcfg &lt;n&gt; react 🔥|off — emoji reaction before reply

<b>Send & Schedule:</b>
/sendnow [@target] — send default ad right now
/schedule YYYY-MM-DD HH:MM [@target] — one-time schedule
/schedulewindow 09:00 11:00 [@target] — daily random time in window
/schedulecron "m h dom mon dow" [@target] — custom cron schedule
/jobs — list scheduled jobs
/canceljobs — cancel all jobs

<b>Content Queue:</b>
/enqueue &lt;preset&gt; [@target] — add to queue
/queue — list queue
/sendnext — send next item now
/qauto on|off [hours] — auto-send next every X hours

<b>Polls:</b>
/poll @t YYYY-MM-DD HH:MM "Question?" opt1|opt2|opt3 [open_min]
/poll @t now "Question?" yes|no — send poll now

<b>Keyword Triggers (ad only when someone says this word):</b>
/kw add &lt;word&gt; &lt;preset&gt; [contains|exact] [@target]
/kw list — list triggers
/kw del &lt;id&gt; — delete trigger

<b>Global Settings:</b>
/auto on|off — turn auto-reply on/off for ALL targets
/toggle on|off — master switch (OFF = nothing sends at all)
/delay &lt;sec&gt; — global delay before reply (default 1s)
/randdelay on|off [jitter] — add random delay ±X sec (human-like)
/typing on|off — show "typing..." indicator
/quiet on|off HH:MM HH:MM — quiet hours (e.g. night time off)
/rotate on|off — pick random preset each time

<b>Safety (Blacklist):</b>
/blacklist adduser &lt;id&gt; — never reply to this user
/blacklist deluser &lt;id&gt;
/blacklist addword &lt;word&gt; — skip if msg contains this word
/blacklist delword &lt;word&gt;
Tip: addwords like "admin","mod","spam","report","ban" to avoid getting banned

<b>Admins:</b>
/addadmin &lt;id&gt; [name] — give someone control (owner only)
/deladmin &lt;id&gt;
/admins — list admins

<b>Info:</b>
/stats — how many sent/failed/clicks
/logs [n] — recent activity log
/status — bot status overview

<b>Backup:</b>
/backup — download all data as JSON file
/restore — send backup file to restore
/cancel — cancel current operation"""
    if len(txt)>4000:txt=txt[:3990]
    bot.send_message(m.chat.id,txt,parse_mode="HTML")

# ---- presets ----
@bot.message_handler(commands=["addpreset"])
@admin_only
def h_addp(m):
    p=m.text.split(maxsplit=1)
    if len(p)<2:bot.reply_to(m,"/addpreset <name>");return
    n=p[1].strip().lower().replace(" ","_")
    if n in D["presets"]:bot.reply_to(m,f"❌ '{n}' exists");return
    STATE[m.from_user.id]={"act":"await_ptype","name":n,"med":[]}
    k=InlineKeyboardMarkup()
    for t in[("Text","text"),("Photo","photo"),("Video","video"),("Doc","document"),("Audio","audio"),("Voice","voice"),("Album","album")]:
        k.add(InlineKeyboardButton(t[0],callback_data=f"pt:{t[1]}:{n}"))
    bot.send_message(m.chat.id,"Type chunein:",reply_markup=k)

@bot.callback_query_handler(func=lambda c:c.data.startswith("pt:"))
def cb_pt(c):
    if not is_admin(c.from_user):bot.answer_callback_query(c.id,"no");return
    _,t,n=c.data.split(":",2);st=STATE.get(c.from_user.id)
    if not st or st.get("name")!=n:bot.answer_callback_query(c.id,"stale");return
    st["t"]=t
    if t=="album":
        bot.edit_message_text(f"📸 Album '{n}' ke liye photos/videos bhejein, phir /done. Pehli item ka caption text hoga.",c.message.chat.id,c.message.message_id,parse_mode="HTML")
    else:
        bot.edit_message_text(f"📝 Ab <b>{t}</b> content bhejein (caption ke saath).",c.message.chat.id,c.message.message_id,parse_mode="HTML")
    bot.answer_callback_query(c.id)

@bot.message_handler(commands=["presets"])
@admin_only
def h_plist(m):
    if not D["presets"]:bot.reply_to(m,"Koi nahi. /addpreset");return
    o="<b>📦 Presets:</b>\n"
    for n,p in D["presets"].items():
        star=" ⭐" if n==D["defpreset"] else ""
        o+=f"• <b>{n}</b>{star} — {p['k']} {len(p.get('b',[]))}btns\n  <i>{(p.get('t','') or '')[:60]}</i>\n"
    bot.send_message(m.chat.id,o,parse_mode="HTML")

@bot.message_handler(commands=["delpreset","setdefault","preview"])
@admin_only
def h_pops(m):
    c=m.text.split()[0][1:];p=m.text.split(maxsplit=1)
    if len(p)<2:bot.reply_to(m,"/"+c+" <name>");return
    n=p[1].strip().lower()
    if c=="delpreset":
        if n not in D["presets"]:bot.reply_to(m,"nahi mila");return
        del D["presets"][n]
        if D["defpreset"]==n:D["defpreset"]=""
        save();bot.reply_to(m,f"🗑️ delete {n}")
    elif c=="setdefault":
        if n not in D["presets"]:bot.reply_to(m,"nai mila");return
        D["defpreset"]=n;save();bot.reply_to(m,f"⭐ default {n}")
    elif c=="preview":
        p=D["presets"].get(n)
        if not p:bot.reply_to(m,"nai mila");return
        bot.send_message(m.chat.id,f"👀 Preview {n}:",parse_mode="HTML")
        send_preset(m.chat.id,p,ctx={"first_name":m.from_user.first_name or "friend","username":f"@{m.from_user.username}" if m.from_user.username else ""})

@bot.message_handler(commands=["presetflag"])
@admin_only
def h_pflag(m):
    p=m.text.split(maxsplit=3)
    if len(p)<3:bot.reply_to(m,"/presetflag <n> <silent|noprev|html|md|btns> <val>");return
    n=p[1];pr=D["presets"].get(n.lower())
    if not pr:bot.reply_to(m,"preset nai mila");return
    fl=p[2].lower();val=p[3] if len(p)>3 else "on"
    if fl=="silent":pr["silent"]=1 if val=="on" else 0
    elif fl=="noprev":pr["nopv"]=1 if val=="on" else 0
    elif fl in ("html","md"):pr["pm"]="HTML" if fl=="html" else "Markdown"
    elif fl=="btns":
        if val.strip()=="-":pr["b"]=[]
        else:
            bs=[]
            for s in val.split(","):
                if "|" not in s:bot.reply_to(m,f"❌ {s} galat");return
                t,u=s.split("|",1);bs.append({"t":t.strip(),"u":u.strip()})
            pr["b"]=bs
    else:bot.reply_to(m,"unknown");return
    D["presets"][n.lower()]=pr;save();bot.reply_to(m,f"✅ {n}.{fl}={val}")
# fix typo
def h_pflag_correct(m):h_pflag(m)
# not needed

# ---- targets ----
@bot.message_handler(commands=["addtarget"])
@admin_only
def h_addt(m):
    p=m.text.split(maxsplit=1)
    if len(p)<2:bot.reply_to(m,"/addtarget @x | -100xx");return
    t=parse_target(p[1])
    if not t:bot.reply_to(m,"❌ invalid");return
    try:
        ch=bot.get_chat(t)
        D["targets"][str(ch.id)]={"title":ch.title or ch.username or str(ch.id),"chat_id":ch.id,"a":1,"p":None,"d":None,"rl":None,"ls":None,"pin":0,"sd":0,"r":None}
        save();bot.reply_to(m,f"✅ Add <b>{ch.title}</b> <code>{ch.id}</code>",parse_mode="HTML")
    except Exception as e:bot.reply_to(m,f"❌ {e}")

@bot.message_handler(commands=["bulkadd"])
@admin_only
def h_bulk(m):STATE[m.from_user.id]={"act":"await_bulk"};bot.reply_to(m,"📋 har line ek target:")

@bot.message_handler(commands=["targets"])
@admin_only
def h_tlist(m):
    if not D["targets"]:bot.reply_to(m,"koi nahi");return
    o="<b>🎯 Targets:</b>\n"
    for i,t in enumerate(D["targets"].values(),1):
        a="🟢" if t.get("a",1) else "🔴";p=t.get("p") or "(default)"
        o+=f"{i}. {a} <b>{t['title']}</b> <code>{t['chat_id']}</code> {p} d:{t.get('d') or D['delay']}s rl:{t.get('rl') or '-'}\n"
    bot.send_message(m.chat.id,o,parse_mode="HTML")

@bot.message_handler(commands=["deltarget"])
@admin_only
def h_delt(m):
    p=m.text.split()
    if len(p)<2 or not p[1].isdigit():bot.reply_to(m,"/deltarget <n>");return
    i=int(p[1])-1;ts=list(D["targets"].keys())
    if not 0<=i<len(ts):bot.reply_to(m,"invalid");return
    k=ts[i];t=D["targets"].pop(k);save();bot.reply_to(m,f"🗑️ {t['title']}")

@bot.message_handler(commands=["chatid"])
def h_cid(m):bot.reply_to(m,f"ID: <code>{m.chat.id}</code> ({m.chat.title or 'pvt'})",parse_mode="HTML")

@bot.message_handler(commands=["tcfg"])
@admin_only
def h_tcfg(m):
    p=m.text.split(maxsplit=3)
    if len(p)<2 or not p[1].isdigit():bot.reply_to(m,"/tcfg <n> <field> <val>");return
    i=int(p[1])-1;ts=list(D["targets"].values())
    if not 0<=i<len(ts):bot.reply_to(m,"invalid");return
    t=ts[i]
    if len(p)<4:bot.reply_to(m,f"<pre>{json.dumps(t,indent=2)}</pre>",parse_mode="HTML");return
    fld=p[2].lower();v=p[3].strip()
    if fld=="auto":t["a"]=1 if v=="on" else 0
    elif fld=="preset":t["p"]=None if v in ("off","none","") else v.lower()
    elif fld=="delay":t["d"]=None if v=="off" else float(v)
    elif fld=="rl":t["rl"]=None if v=="off" else int(v)
    elif fld=="pin":t["pin"]=1 if v=="on" else 0
    elif fld=="sd":t["sd"]=0 if v in ("off","0") else int(v)
    elif fld=="react":t["r"]=None if v=="off" else v
    else:bot.reply_to(m,"fields: auto|preset|delay|rl|pin|sd|react");return
    D["targets"][str(t["chat_id"])]=t;save();bot.reply_to(m,f"✅ {t['title']} {fld}={v}")

@bot.message_handler(commands=["reaction"])
@admin_only
def h_react(m):
    p=m.text.split(maxsplit=2)
    if len(p)<3:bot.reply_to(m,"/reaction 👍 @t");return
    t=parse_target(p[2]);cid=resolve(t)
    if cid is None:bot.reply_to(m,"target?");return
    g=D["targets"].get(str(cid),{})
    if not g:bot.reply_to(m,"pehle /addtarget");return
    g["r"]=None if p[1].lower()=="off" else p[1]
    D["targets"][str(cid)]=g;save();bot.reply_to(m,f"👍 react {p[1]}")

# ---- blacklist ----
@bot.message_handler(commands=["blacklist"])
@admin_only
def h_blk(m):
    p=m.text.split(maxsplit=2)
    if len(p)<2:
        u=", ".join(str(x) for x in D["blk_u"]) or "—";w=", ".join(D["blk_w"]) or "—"
        bot.send_message(m.chat.id,f"<b>🚫 Blacklist</b>\nUsers: {u}\nWords: {w}\n/blacklist adduser|deluser|addword|delword v",parse_mode="HTML");return
    a=p[1].lower();v=p[2].strip() if len(p)>2 else ""
    if a=="adduser" and v.lstrip("-").isdigit():D["blk_u"].append(int(v)) if int(v) not in D["blk_u"] else None
    elif a=="deluser" and v.lstrip("-").isdigit():
        if int(v) in D["blk_u"]:D["blk_u"].remove(int(v))
    elif a=="addword" and v:D["blk_w"].append(v.lower()) if v.lower() not in D["blk_w"] else None
    elif a=="delword" and v:
        if v.lower() in D["blk_w"]:D["blk_w"].remove(v.lower())
    else:bot.reply_to(m,"/blacklist adduser|deluser|addword|delword v");return
    save();bot.reply_to(m,"✅ blk update")

# ---- kw ----
@bot.message_handler(commands=["kw"])
@admin_only
def h_kw(m):
    p=m.text.split(maxsplit=4)
    if len(p)<2 or p[1]=="list":
        if not D["kw"]:bot.reply_to(m,"kuch nahi");return
        o="<b>🔑 Keywords:</b>\n"
        for i,k in enumerate(D["kw"],1):
            o+=f"{i}. [{k.get('m','contains')}] \"{k['k']}\" → <b>{k['p']}</b> ({k.get('c') or 'GLOBAL'})\n"
        bot.send_message(m.chat.id,o,parse_mode="HTML");return
    if p[1]=="del" and len(p)>=3 and p[2].isdigit():
        i=int(p[2])-1
        if 0<=i<len(D["kw"]):D["kw"].pop(i);save();bot.reply_to(m,"🗑️");return
    if p[1]=="add" and len(p)>=4:
        kw=p[2].lower();pn=p[3].lower();mm="contains";tgt=None
        rest=p[4] if len(p)>4 else ""
        for tk in rest.split():
            if tk in ("contains","exact"):mm=tk
            else:
                tt=parse_target(tk)
                if tt:
                    rid=resolve(tt)
                    if rid:tgt=str(rid)
        if pn not in D["presets"]:bot.reply_to(m,"preset nai");return
        D["kw"].append({"k":kw,"p":pn,"m":mm,"c":tgt});save()
        bot.reply_to(m,f"✅ kw '{kw}' → {pn}");return
    bot.reply_to(m,"/kw add|list|del")

# ---- admins ----
@bot.message_handler(commands=["addadmin","deladmin","admins"])
@owner_only
def h_adm(m):
    p=m.text.split(maxsplit=2);c=p[0][1:]
    if c=="admins":
        o="<b>👤 Admins:</b>\n"+"\n".join(f"• <code>{a}</code>" for a in D["admins"])
        bot.send_message(m.chat.id,o,parse_mode="HTML");return
    if len(p)<2 or not p[1].isdigit():bot.reply_to(m,"/"+c+" <id>");return
    uid=int(p[1])
    if c=="addadmin":
        if uid not in D["admins"]:D["admins"].append(uid)
        bot.reply_to(m,"✅ add")
    else:
        if uid==OWNER:bot.reply_to(m,"owner ko nahi");return
        if uid in D["admins"]:D["admins"].remove(uid)
        bot.reply_to(m,"🗑️")
    save()

# ---- send/schedule ----
@bot.message_handler(commands=["sendnow"])
@admin_only
def h_send(m):
    p=m.text.split(maxsplit=1);tgt=None
    if len(p)>1:tgt=parse_target(p[1])
    pr=pick_preset(str(resolve(tgt))) if tgt else pick_preset()
    bot.reply_to(m,send_to_targets(pr,tgt))

def job_run(pn,tgt=None,jid=None):
    try:
        p=D["presets"].get(pn)
        if not p:bot.send_message(OWNER,f"❌ job {jid}: preset {pn} missing");return
        bot.send_message(OWNER,f"⏰ Job: <b>{pn}</b> → {tgt or 'all'}",parse_mode="HTML")
        r=send_to_targets(p,parse_target(tgt) if tgt else None)
        bot.send_message(OWNER,r)
    except Exception as e:log.error(f"job {jid}: {e}")

@bot.message_handler(commands=["schedule"])
@admin_only
def h_sch(m):
    p=m.text.split(maxsplit=2)
    if len(p)<3:bot.reply_to(m,"/schedule YYYY-MM-DD HH:MM [tgt]");return
    rest=p[2];tgt=None;ts=rest
    toks=rest.rsplit(" ",1)
    if len(toks)==2 and parse_target(toks[1]):tgt=parse_target(toks[1]);ts=toks[0]
    try:dt=datetime.strptime(f"{p[1]} {ts.strip()}","%Y-%m-%d %H:%M")
    except Exception as e:bot.reply_to(m,f"❌ {e}");return
    if dt<=datetime.now():bot.reply_to(m,"future?");return
    pn=D["defpreset"]
    if not pn or pn not in D["presets"]:bot.reply_to(m,"setdefault?");return
    jid=f"once_{dt.timestamp()}_{random.randint(1000,9999)}"
    sched.add_job(job_run,"date",run_date=dt,args=[pn,str(tgt) if tgt else None,jid],id=jid,misfire_grace_time=3600)
    bot.reply_to(m,f"⏰ {dt:%Y-%m-%d %H:%M} {pn} → {tgt or 'all'}")

@bot.message_handler(commands=["schedulewindow"])
@admin_only
def h_win(m):
    p=m.text.split(maxsplit=2)
    if len(p)<3:bot.reply_to(m,"/schedulewindow 09:00 11:00 [tgt]");return
    rest=p[2];tgt=None;win=rest
    toks=rest.rsplit(" ",1)
    if len(toks)==2 and parse_target(toks[1]):tgt=parse_target(toks[1]);win=toks[0]
    try:
        s,e=win.strip().split()
        sh,sm=map(int,s.split(":"));eh,em=map(int,e.split(":"))
        smin=sh*60+sm;emin=eh*60+em
        if emin<=smin:emin=24*60
        ch=random.randint(smin,emin);h,mn=divmod(ch,60)
    except:bot.reply_to(m,"format HH:MM HH:MM");return
    pn=D["defpreset"]
    if not pn or pn not in D["presets"]:bot.reply_to(m,"setdefault?");return
    jid=f"cron_{time.time()}_{random.randint(1000,9999)}"
    trig=CronTrigger.from_crontab(f"{mn} {h} * * *",timezone=TZ)
    sched.add_job(job_run,trigger=trig,args=[pn,str(tgt) if tgt else None,jid],id=jid,misfire_grace_time=3600)
    bot.reply_to(m,f"🎲 Roz <b>{h:02d}:{mn:02d}</b> par",parse_mode="HTML")

from apscheduler.triggers.cron import CronTrigger
@bot.message_handler(commands=["schedulecron"])
@admin_only
def h_cron(m):
    p=m.text.split(maxsplit=2)
    if len(p)<3:bot.reply_to(m,'/schedulecron "0 9 * * *" [tgt]');return
    rest=p[2];tgt=None;cr=rest
    toks=rest.rsplit(" ",1)
    if len(toks)==2 and parse_target(toks[1]):tgt=parse_target(toks[1]);cr=toks[0]
    cr=cr.strip().strip('"').strip("'")
    pn=D["defpreset"]
    if not pn:bot.reply_to(m,"default set?");return
    try:
        jid=f"cron_{time.time()}_{random.randint(1000,9999)}"
        trig=CronTrigger.from_crontab(cr,timezone=TZ)
        sched.add_job(job_run,trigger=trig,args=[pn,str(tgt) if tgt else None,jid],id=jid,misfire_grace_time=3600)
    except Exception as e:bot.reply_to(m,f"❌ {e}");return
    bot.reply_to(m,f"⏰ cron add: <code>{cr}</code>",parse_mode="HTML")

@bot.message_handler(commands=["jobs","canceljobs"])
@admin_only
def h_jobs(m):
    if m.text.startswith("/canceljobs"):
        n=0
        for j in sched.get_jobs():
            if j.id not in ("qauto","polls"):j.remove();n+=1
        bot.reply_to(m,f"🗑️ {n} cancel");return
    jobs=[j for j in sched.get_jobs() if j.id not in ("qauto","polls")]
    if not jobs:bot.reply_to(m,"none");return
    o="<b>📅 Jobs:</b>\n"
    for j in jobs:
        nxt=j.next_run_time.strftime("%Y-%m-%d %H:%M") if j.next_run_time else "paused"
        o+=f"• {nxt} — {j.trigger}\n"
    bot.send_message(m.chat.id,o,parse_mode="HTML")

# ---- queue ----
def qpop():
    if not D["queue"]:return None
    it=D["queue"].pop(0);save();return it
def qjob():
    if not D["qauto"]:return
    it=qpop()
    if not it:
        D["qauto"]=0;save()
        try:bot.send_message(OWNER,"📭 queue khatam");return
        except:pass
    p=D["presets"].get(it["p"])
    if not p:return
    r=send_to_targets(p,parse_target(it["t"]) if it.get("t") else None)
    try:bot.send_message(OWNER,f"📤 queue: {it['p']}\n{r}")
    except:pass
def ensure_qjob():
    jid="qauto";ex=sched.get_job(jid)
    if D["qauto"]:
        hrs=max(1,int(D["qhrs"]))
        from apscheduler.triggers.interval import IntervalTrigger
        tr=IntervalTrigger(hours=hrs,timezone=TZ)
        if ex:ex.reschedule(trigger=tr)
        else:sched.add_job(qjob,trigger=tr,id=jid,next_run_time=datetime.now()+timedelta(seconds=10))
    elif ex:ex.remove()

@bot.message_handler(commands=["enqueue","queue","sendnext","qauto"])
@admin_only
def h_q(m):
    p=m.text.split(maxsplit=2);c=p[0][1:]
    if c=="enqueue":
        if len(p)<2:bot.reply_to(m,"/enqueue <p> [t]");return
        pn=p[1].lower();tgt=None
        if len(p)>2:tgt=parse_target(p[2])
        if pn not in D["presets"]:bot.reply_to(m,"preset?");return
        D["queue"].append({"p":pn,"t":str(tgt) if tgt else None,"a":datetime.now().isoformat()})
        save();bot.reply_to(m,f"📥 size {len(D['queue'])}");return
    if c=="queue":
        if not D["queue"]:bot.reply_to(m,"khaali");return
        o="<b>📋 Queue:</b>\n"
        for i,it in enumerate(D["queue"],1):o+=f"{i}. {it['p']} → {it.get('t') or 'all'}\n"
        bot.send_message(m.chat.id,o,parse_mode="HTML");return
    if c=="sendnext":qjob();bot.reply_to(m,"✅ bhej diya agar tha");return
    if c=="qauto":
        if len(p)<2 or p[1] not in ("on","off"):bot.reply_to(m,f"/qauto on|off ({D['qauto']})");return
        D["qauto"]=1 if p[1]=="on" else 0
        if len(p)>2 and p[2].isdigit():D["qhrs"]=int(p[2])
        save();ensure_qjob();bot.reply_to(m,f"🔁 qauto {p[1]}")

# ---- polls ----
@bot.message_handler(commands=["poll"])
@admin_only
def h_poll(m):
    mm=re.match(r"^/poll\s+(\S+)\s+(\S+)\s+(\S+)\s+\"([^\"]+)\"\s+([^|]+(?:\|[^|]+)+)(?:\s+(\d+))?",m.text)
    if not mm:bot.reply_to(m,'/poll @t YYYY-MM-DD HH:MM "Q?" a|b|c [open_min]  — abhi ke liye "now"');return
    t_raw,ds,ts,q,opts,om=mm.groups()
    opts=[o.strip() for o in opts.split("|") if o.strip()]
    tgt=parse_target(t_raw);cid=resolve(tgt)
    if cid is None:bot.reply_to(m,"target?");return
    if ds.lower()=="now":
        try:bot.send_poll(cid,q,opts,is_anonymous=True,open_period=int(om)*60 if om else None);bot.reply_to(m,"✅ bhej diya")
        except Exception as e:bot.reply_to(m,f"❌ {e}");return
    else:
        try:dt=datetime.strptime(f"{ds} {ts}","%Y-%m-%d %H:%M")
        except:bot.reply_to(m,"date?");return
        def pollsend(c=cid,qq=q,oo=opts,op=int(om)*60 if om else None):
            try:bot.send_poll(c,qq,oo,is_anonymous=True,open_period=op);addlog(f"POLL {qq[:30]}",c,1)
            except Exception as e:addlog(f"POLL FAIL {e}",c,0)
        sched.add_job(pollsend,"date",run_date=dt,id=f"poll_{dt.timestamp()}",misfire_grace_time=3600)
        bot.reply_to(m,f"📊 {dt:%Y-%m-%d %H:%M} poll schedule")

# ---- global toggles ----
@bot.message_handler(commands=["auto","toggle","delay","randdelay","typing","quiet","rotate"])
@admin_only
def h_tog(m):
    p=m.text.split();c=p[0][1:]
    if c=="auto":
        if len(p)<2 or p[1] not in ("on","off"):bot.reply_to(m,"/auto on|off");return
        v=1 if p[1]=="on" else 0
        for g in D["targets"].values():g["a"]=v
        save();bot.reply_to(m,f"✅ auto {p[1]}");return
    if c=="toggle":
        if len(p)<2 or p[1] not in ("on","off"):bot.reply_to(m,f"master {D['on']}");return
        D["on"]=1 if p[1]=="on" else 0;save();bot.reply_to(m,f"✅ {p[1]}");return
    if c=="delay":
        if len(p)<2:bot.reply_to(m,f"delay {D['delay']}s");return
        D["delay"]=max(0,float(p[1]));save();bot.reply_to(m,f"✅ {p[1]}s");return
    if c=="randdelay":
        if len(p)<2 or p[1] not in ("on","off"):bot.reply_to(m,f"jitter ±{D['jitter']}s ({D['randdelay']})");return
        D["randdelay"]=1 if p[1]=="on" else 0
        if len(p)>2 and p[2].replace(".","",1).isdigit():D["jitter"]=float(p[2])
        save();bot.reply_to(m,f"✅ {p[1]} ±{D['jitter']}s");return
    if c=="typing":
        if len(p)<2 or p[1] not in ("on","off"):bot.reply_to(m,f"typing {D['typing']}");return
        D["typing"]=1 if p[1]=="on" else 0;save();bot.reply_to(m,f"✅ typing {p[1]}");return
    if c=="quiet":
        if len(p)<2 or p[1] not in ("on","off"):bot.reply_to(m,f"quiet {D['quiet']}");return
        D["quiet"]["on"]=1 if p[1]=="on" else 0
        if len(p)>=4 and re.match(r"\d{1,2}:\d{2}",p[2]) and re.match(r"\d{1,2}:\d{2}",p[3]):
            D["quiet"]["s"]=p[2];D["quiet"]["e"]=p[3]
        save();bot.reply_to(m,"✅ quiet update");return
    if c=="rotate":
        if len(p)<2 or p[1] not in ("on","off"):bot.reply_to(m,f"rotate {D['rotate']}");return
        D["rotate"]=1 if p[1]=="on" else 0;save();bot.reply_to(m,f"✅ rotate {p[1]}")

# ---- stats/logs/status/backup ----
@bot.message_handler(commands=["stats"])
@admin_only
def h_stats(m):
    o=f"<b>📊 Stats</b>\nSent: <b>{D['stats']['sent']}</b>\nFailed: <b>{D['stats']['fail']}</b>\nClicks: <b>{D['stats'].get('clicks',0)}</b>\n"
    for cid,n in list(sorted(D["stats"]["per"].items(),key=lambda x:-x[1]))[:20]:
        t=D["targets"].get(cid,{}).get("title",cid)
        o+=f"• {t}: {n}\n"
    bot.send_message(m.chat.id,o,parse_mode="HTML")

@bot.message_handler(commands=["logs"])
@admin_only
def h_logs(m):
    p=m.text.split();n=min(int(p[1]) if len(p)>1 and p[1].isdigit() else 20,50)
    if not D["logs"]:bot.reply_to(m,"none");return
    o=f"<b>📜 Last {n}</b>\n"
    for e in D["logs"][:n]:
        ok="✅" if e["ok"] else "❌";o+=f"{ok} [{e['ts'][5:16]}] {e['e']} ({e['c']})\n"
    bot.send_message(m.chat.id,o[:4000],parse_mode="HTML")

@bot.message_handler(commands=["status"])
@admin_only
def h_status(m):
    o=f"""<b>📋 Status</b>
Master: {'🟢' if D['on'] else '🔴'}
Typing: {'ON' if D['typing'] else 'OFF'}
Delay: {D['delay']}s ±{D['jitter']}s
Quiet: {'ON' if D['quiet']['on'] else 'OFF'} ({D['quiet']['s']}-{D['quiet']['e']})
Default preset: {D['defpreset'] or 'none'}
Rotate: {'ON' if D['rotate'] else 'OFF'}
Targets: {len(D['targets'])}
Presets: {len(D['presets'])}
Queue: {len(D['queue'])} (auto={D['qauto']} every {D['qhrs']}h)
Jobs: {len([j for j in sched.get_jobs() if j.id not in ('qauto','polls')])}
Blacklist: {len(D['blk_u'])} users, {len(D['blk_w'])} words
Total sent: {D['stats']['sent']} (fail {D['stats']['fail']})"""
    bot.send_message(m.chat.id,o,parse_mode="HTML")

@bot.message_handler(commands=["backup"])
@owner_only
def h_bak(m):
    buf=BytesIO(json.dumps(D,ensure_ascii=False,indent=2).encode("utf-8"))
    buf.name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    bot.send_document(m.chat.id,buf,caption="📁 backup")

@bot.message_handler(commands=["restore"])
@owner_only
def h_res(m):STATE[m.from_user.id]={"act":"await_res"};bot.reply_to(m,"📥 backup JSON file bhejein")

@bot.message_handler(commands=["cancel"])
@admin_only
def h_can(m):STATE.pop(m.from_user.id,None);bot.reply_to(m,"❌ cancel")

# ============ MAIN CONTENT HANDLER ============
@bot.message_handler(content_types=["text","photo","video","document","audio","voice"],func=lambda m:True)
def catch(m):
    uid=m.from_user.id if m.from_user else None;st=STATE.get(uid) if uid else None

    # preset type already chosen — receive content
    if st and st.get("act")=="await_ptype":
        n=st["name"];t=st["t"];cap=m.caption or m.text or "";fid=None;ok=True
        if t=="text":
            if m.content_type!="text":bot.reply_to(m,"text bhejein");return
        elif t=="photo":
            if not m.photo:ok=False
            else:fid=m.photo[-1].file_id
        elif t=="video":
            if not m.video:ok=False
            else:fid=m.video.file_id
        elif t=="document":
            if not m.document:ok=False
            else:fid=m.document.file_id
        elif t=="audio":
            if not m.audio:ok=False
            else:fid=m.audio.file_id
        elif t=="voice":
            if not m.voice:ok=False
            else:fid=m.voice.file_id
        elif t=="album":
            it_t=None;it_f=None
            if m.photo:it_t,it_f="photo",m.photo[-1].file_id
            elif m.video:it_t,it_f="video",m.video.file_id
            elif m.document:it_t,it_f="document",m.document.file_id
            elif m.text and m.text.strip()=="/done":
                items=st.get("med",[])
                if not items:bot.reply_to(m,"kuch nai");return
                D["presets"][n]={"name":n,"k":"album","t":cap or st.get("cap",""),"m":items,"b":[],"pm":"HTML","silent":0,"nopv":0}
                if not D["defpreset"]:D["defpreset"]=n
                STATE.pop(uid,None);save();bot.reply_to(m,f"✅ Album '{n}' ({len(items)} items)");return
            else:bot.reply_to(m,"media bhejo ya /done");return
            st["med"].append({"k":it_t,"f":it_f})
            if not st.get("cap"):st["cap"]=cap
            bot.reply_to(m,f"➕ add ({it_t}) total {len(st['med'])}. Aur bhejo ya /done");return
        if not ok:bot.reply_to(m,f"{t} chahiye");return
        D["presets"][n]={"name":n,"k":t,"t":cap,"f":fid,"m":[],"b":[],"pm":"HTML","silent":0,"nopv":0}
        st["act"]="await_btns"
        bot.reply_to(m,"✅ Content saved. Buttons: <code>Text|url,Text2|url2</code> — nahi to /skip",parse_mode="HTML");return

    if st and st.get("act")=="await_btns":
        n=st["name"]
        if m.text and m.text.strip().lower()=="/skip":
            if not D["defpreset"]:D["defpreset"]=n
            STATE.pop(uid,None);save();bot.reply_to(m,f"✅ '{n}' ready (no buttons)");return
        if not m.text:bot.reply_to(m,"text mein buttons ya /skip");return
        try:
            bs=[]
            for s in m.text.split(","):
                s=s.strip()
                if "|" not in s:raise ValueError("| chahiye")
                t,u=s.split("|",1);t=t.strip();u=u.strip()
                if not u.startswith("http"):raise ValueError(f"url {u}")
                bs.append({"t":t,"u":u})
            D["presets"][n]["b"]=bs
        except Exception as e:
            bot.reply_to(m,f"❌ {e}. Example: Join|https://t.me/x ya /skip");return
        if not D["defpreset"]:D["defpreset"]=n
        STATE.pop(uid,None);save();bot.reply_to(m,f"✅ '{n}' ready with {len(bs)} buttons")
        return

    # bulk add
    if st and st.get("act")=="await_bulk":
        ad=0;fail=0
        for ln in (m.text or "").splitlines():
            t=parse_target(ln.strip())
            if not t:fail+=1;continue
            try:
                ch=bot.get_chat(t)
                D["targets"][str(ch.id)]={"title":ch.title or ch.username,"chat_id":ch.id,"a":1,"p":None,"d":None,"rl":None,"ls":None,"pin":0,"sd":0,"r":None}
                ad+=1
            except:fail+=1
        STATE.pop(uid,None);save();bot.reply_to(m,f"✅ {ad} add, {fail} fail");return

    # restore
    if st and st.get("act")=="await_res":
        if m.content_type!="document":bot.reply_to(m,"JSON doc bhejo");return
        try:
            f=bot.get_file(m.document.file_id);raw=bot.download_file(f.file_path)
            obj=json.loads(raw.decode("utf-8"))
            if not isinstance(obj,dict) or "presets" not in obj:raise ValueError("nai lag raha backup")
            D.update(obj);save();STATE.pop(uid,None);bot.reply_to(m,"✅ restore")
        except Exception as e:bot.reply_to(m,f"❌ {e}");return

    if m.chat.type=="private":return
    # group/channel auto
    if m.chat.type not in ("group","supergroup","channel"):return
    cid=m.chat.id
    if str(cid) not in D["targets"]:return
    if not D["on"]:return
    g=D["targets"][str(cid)]
    if not g.get("a",1):return
    if quiet():return
    if isinstance(m.forward_from_chat or None,object):pass
    if blocked(m,g):return
    pick_and_send_preset(cid,m)

@bot.channel_post_handler(content_types=["text","photo","video","document","audio","voice"],func=lambda m:True)
def ch_follow(m):
    cid=m.chat.id;g=D["targets"].get(str(cid))
    if not g or not D["on"] or not g.get("a",1):return
    if quiet() or ratelimited(g):return
    p=pick_preset(cid)
    if not p:return
    dly=float(g.get("d") or D["delay"])
    if D["randdelay"]:dly=jitter(dly,D["jitter"])
    def run():
        time.sleep(dly)
        send_preset(cid,p,pin=bool(g.get("pin")),sd=g.get("sd"),react=g.get("r"),
                   ctx={"first_name":"subscriber","group":m.chat.title or "","msg":m.text or m.caption or ""})
    threading.Thread(target=run,daemon=True).start()

# ============ DASHBOARD ============
@app.route("/health")
def health():
    return {"ok": True, "bot": "alex-stor-bot", "uptime": True}, 200

@app.route("/")
def dash():
    auth=request.authorization
    if not auth or auth.username!=DASH_USER or auth.password!=DASH_PASS:
        return Response("Login required",401,{"WWW-Authenticate":'Basic realm="Alex Bot"'})
    # Build simple dashboard inline if file missing
    jobs=[j for j in sched.get_jobs() if j.id not in ("qauto","polls")]
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport"content="width=device-width,initial-scale=1">
<title>Alex Stor Bot</title>
<style>body{{font-family:sans-serif;background:#0f172a;color:#e2e8f0;padding:20px}}h1{{color:#6366f1}}
.card{{background:#1e293b;padding:16px;border-radius:12px;margin:8px 0}}.ok{{color:#10b981}}.bad{{color:#ef4444}}
.pill{{padding:3px 8px;border-radius:6px;background:#334155;color:#fff;font-size:12px}}</style></head><body>
<h1>🤖 Alex Stor Bot Dashboard</h1>
<div class="card"><b>Status:</b> Master {'🟢 ON' if D['on'] else '🔴 OFF'} · Auto-rotate {'ON' if D['rotate'] else 'OFF'} · Typing {'ON' if D['typing'] else 'OFF'}<br>
Delay: {D['delay']}s ±{D['jitter']}s · Quiet: {'ON' if D['quiet']['on'] else 'OFF'} ({D['quiet']['s']}-{D['quiet']['e']})</div>
<div class="card"><h3>📊 Stats</h3>Sent: {D['stats']['sent']} | Failed: {D['stats']['fail']} | Clicks: {D['stats'].get('clicks',0)}<br>
Targets: {len(D['targets'])} | Presets: {len(D['presets'])} | Queue: {len(D['queue'])} | Jobs: {len(jobs)}</div>
<div class="card"><h3>🎯 Targets</h3><ol>{''.join(f"<li>{t['title']} ({t['chat_id']}) — {'ON' if t.get('a',1) else 'OFF'}</li>" for t in D['targets'].values())}</ol></div>
<div class="card"><h3>📦 Presets</h3><ul>{''.join(f"<li><b>{n}</b> — {p['k']}</li>" for n,p in D['presets'].items())}</ul></div>
<div class="card"><h3>📜 Recent logs (10)</h3>{''.join(f"<div>{'✅' if e['ok'] else '❌'} [{e['ts'][5:16]}] {e['e']}</div>" for e in D['logs'][:10])}</div>
<p style="color:#94a3b8">Alex Stor Bot v3 · <a href="/backup"style="color:#93c5fd">Download backup JSON</a></p>
</body></html>"""

@app.route("/backup")
def dash_backup():
    auth=request.authorization
    if not auth or auth.username!=DASH_USER or auth.password!=DASH_PASS:return Response("Login",401,{"WWW-Authenticate":'Basic realm="r"'})
    return Response(json.dumps(D,ensure_ascii=False,indent=2),mimetype="application/json",
                    headers={"Content-Disposition":f"attachment; filename=backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json"})

@app.route("/r/<slug>")
def track(slug):
    u=D["slugs"].get(slug)
    if u:
        D["stats"]["clicks"]=D["stats"].get("clicks",0)+1
        s=request.args.get("s","")
        addlog(f"CLICK {slug}",s or 0,1)
        return redirect(u,302)
    return "Not found",404

def run_dash():app.run(host="0.0.0.0",port=DASH_PORT,debug=False,use_reloader=False,threaded=True)

# ============ MAIN ============
def main():
    if not TOKEN or ":" not in TOKEN or not OWNER:
        print("BOT_TOKEN / OWNER_ID set nahi.");return
    sched.start()
    ensure_qjob()
    threading.Thread(target=run_dash,daemon=True).start()
    log.info(f"Alex Stor Bot chalu. Dashboard http://0.0.0.0:{DASH_PORT} — user {DASH_USER}")
    try:bot.infinity_polling(allowed_updates=telebot.util.update_types,long_polling_timeout=30)
    except(KeyboardInterrupt,SystemExit):pass
    sched.shutdown()

if __name__=="__main__":main()

# ============ INLINE MENU SYSTEM (Tap-Tap Buttons) ============
MAIN_MENU_TEXT = "<b>🏠 Main Menu</b>\nNeeche se option choose karein:"

def kb_main():
    k=InlineKeyboardMarkup(row_width=2)
    k.add(InlineKeyboardButton("📝 New Ad (Preset)",callback_data="m_addpreset"),
          InlineKeyboardButton("📦 My Ads",callback_data="m_presets"))
    k.add(InlineKeyboardButton("🎯 Targets",callback_data="m_targets"),
          InlineKeyboardButton("➕ Add Target",callback_data="m_addtarget"))
    k.add(InlineKeyboardButton("⚡ Send Now",callback_data="m_sendnow"),
          InlineKeyboardButton("⏰ Schedule",callback_data="m_schedule"))
    k.add(InlineKeyboardButton("🔑 Keyword Triggers",callback_data="m_kw"),
          InlineKeyboardButton("📋 Queue",callback_data="m_queue"))
    k.add(InlineKeyboardButton("⚙️ Settings",callback_data="m_settings"),
          InlineKeyboardButton("📊 Stats & Logs",callback_data="m_stats"))
    k.add(InlineKeyboardButton("🆘 Help / Commands",callback_data="m_help"),
          InlineKeyboardButton("❌ Close Menu",callback_data="m_close"))
    return k

def kb_back(target="m_main", label="⬅️ Back"):
    k=InlineKeyboardMarkup()
    k.add(InlineKeyboardButton(label,callback_data=target))
    return k

def kb_targets():
    ts=list(D["targets"].values())
    k=InlineKeyboardMarkup(row_width=1)
    if not ts:
        k.add(InlineKeyboardButton("Koi target nahi — add karo",callback_data="m_addtarget"))
    else:
        for i,t in enumerate(ts,1):
            icon="🟢" if t.get("a",1) else "🔴"
            k.add(InlineKeyboardButton(f"{icon} {i}. {t['title'][:30]}",callback_data=f"t_view_{t['chat_id']}"))
    k.add(InlineKeyboardButton("➕ Add Target",callback_data="m_addtarget"),
          InlineKeyboardButton("⬅️ Main Menu",callback_data="m_main"))
    return k

def kb_target_view(cid):
    g=D["targets"].get(str(cid),{})
    if not g: return kb_back()
    k=InlineKeyboardMarkup(row_width=2)
    a_t="🔴 Auto: OFF" if not g.get("a",1) else "🟢 Auto: ON"
    k.add(InlineKeyboardButton(a_t,callback_data=f"t_toggleauto_{cid}"))
    pin_t="📌 Pin: ON" if g.get("pin") else "📍 Pin: OFF"
    k.add(InlineKeyboardButton(pin_t,callback_data=f"t_togglepin_{cid}"))
    k.add(InlineKeyboardButton("⏱ Delay",callback_data=f"t_delay_{cid}"),
          InlineKeyboardButton("🚦 Rate Limit",callback_data=f"t_rl_{cid}"))
    k.add(InlineKeyboardButton("👍 Reaction",callback_data=f"t_react_{cid}"),
          InlineKeyboardButton("🗑 Delete",callback_data=f"t_del_{cid}"))
    k.add(InlineKeyboardButton("⬅️ Back to Targets",callback_data="m_targets"))
    return k

def kb_presets():
    ps=list(D["presets"].items())
    k=InlineKeyboardMarkup(row_width=1)
    if not ps:
        k.add(InlineKeyboardButton("Koi ad nahi — banao",callback_data="m_addpreset"))
    else:
        for n,p in ps:
            star=" ⭐" if n==D["defpreset"] else ""
            k.add(InlineKeyboardButton(f"📝 {n}{star} ({p['k']})",callback_data=f"p_view_{n}"))
    k.add(InlineKeyboardButton("➕ New Ad",callback_data="m_addpreset"),
          InlineKeyboardButton("⬅️ Main Menu",callback_data="m_main"))
    return k

def kb_preset_view(name):
    p=D["presets"].get(name)
    if not p: return kb_back("m_presets")
    k=InlineKeyboardMarkup(row_width=2)
    k.add(InlineKeyboardButton("👀 Preview",callback_data=f"p_preview_{name}"),
          InlineKeyboardButton(f"{'⭐ Default' if D['defpreset']!=name else '★ Default ✓'}",callback_data=f"p_setdef_{name}"))
    k.add(InlineKeyboardButton("🔇 Silent on/off",callback_data=f"p_togglesilent_{name}"),
          InlineKeyboardButton("🔗 Links preview",callback_data=f"p_togglenopv_{name}"))
    k.add(InlineKeyboardButton("✏️ Edit Buttons",callback_data=f"p_editbtns_{name}"),
          InlineKeyboardButton("🗑 Delete",callback_data=f"p_del_{name}"))
    k.add(InlineKeyboardButton("⬅️ Back to Ads",callback_data="m_presets"))
    return k

def kb_settings():
    k=InlineKeyboardMarkup(row_width=2)
    k.add(InlineKeyboardButton(f"{'🟢' if D['on'] else '🔴'} Master Switch",callback_data="s_togglemaster"))
    k.add(InlineKeyboardButton(f"{'🟢' if D['typing'] else '🔴'} Typing Indicator",callback_data="s_toggletyping"))
    k.add(InlineKeyboardButton(f"{'🟢' if D['randdelay'] else '🔴'} Random Delay",callback_data="s_toggleranddelay"))
    k.add(InlineKeyboardButton(f"{'🟢' if D['rotate'] else '🔴'} Ad Rotation",callback_data="s_togglerotate"))
    k.add(InlineKeyboardButton(f"{'🌙 ON' if D['quiet']['on'] else '☀️ OFF'} Quiet Hours",callback_data="s_quiet"))
    k.add(InlineKeyboardButton(f"⏱ Delay: {D['delay']}s",callback_data="s_delay"),
          InlineKeyboardButton(f"🎲 Jitter: ±{D['jitter']}s",callback_data="s_jitter"))
    k.add(InlineKeyboardButton("🚫 Blacklist",callback_data="s_blacklist"),
          InlineKeyboardButton("👥 Admins",callback_data="s_admins"))
    k.add(InlineKeyboardButton("📁 Backup",callback_data="s_backup"))
    k.add(InlineKeyboardButton("⬅️ Main Menu",callback_data="m_main"))
    return k

def kb_sendnow():
    k=InlineKeyboardMarkup(row_width=1)
    k.add(InlineKeyboardButton("📢 Send to ALL Targets",callback_data="sn_all"))
    if D["targets"]:
        for i,t in enumerate(D["targets"].values(),1):
            k.add(InlineKeyboardButton(f"👉 {i}. {t['title'][:30]}",callback_data=f"sn_one_{t['chat_id']}"))
    k.add(InlineKeyboardButton("⬅️ Main Menu",callback_data="m_main"))
    return k

def kb_schedule():
    k=InlineKeyboardMarkup(row_width=1)
    k.add(InlineKeyboardButton("⏰ Fixed Time (one-time)",callback_data="sch_once"),
          InlineKeyboardButton("🎲 Daily Random Window",callback_data="sch_window"),
          InlineKeyboardButton("🔁 Recurring (cron)",callback_data="sch_cron"),
          InlineKeyboardButton("📋 View Scheduled Jobs",callback_data="sch_list"),
          InlineKeyboardButton("⬅️ Main Menu",callback_data="m_main"))
    return k

def kb_stats():
    k=InlineKeyboardMarkup(row_width=2)
    k.add(InlineKeyboardButton("📊 Stats",callback_data="st_show"),
          InlineKeyboardButton("📜 Logs (20)",callback_data="st_logs20"))
    k.add(InlineKeyboardButton("📋 Status",callback_data="st_status"),
          InlineKeyboardButton("📁 Download Backup",callback_data="s_backup"))
    k.add(InlineKeyboardButton("⬅️ Main Menu",callback_data="m_main"))
    return k

def kb_kw():
    k=InlineKeyboardMarkup(row_width=1)
    k.add(InlineKeyboardButton("➕ Add Keyword Trigger",callback_data="kw_add"))
    if D["kw"]:
        for i,t in enumerate(D["kw"],1):
            k.add(InlineKeyboardButton(f"🔑 \"{t['k']}\" → {t['p']} ❌",callback_data=f"kw_del_{i-1}"))
    k.add(InlineKeyboardButton("⬅️ Main Menu",callback_data="m_main"))
    return k

def kb_queue():
    k=InlineKeyboardMarkup(row_width=2)
    k.add(InlineKeyboardButton("➕ Enqueue Default",callback_data="q_adddef"),
          InlineKeyboardButton("📤 Send Next Now",callback_data="q_sendnext"))
    k.add(InlineKeyboardButton(f"🔁 Autoplay: {'ON' if D['qauto'] else 'OFF'}",callback_data="q_toggleauto"))
    k.add(InlineKeyboardButton("🗑 Clear All",callback_data="q_clear"))
    k.add(InlineKeyboardButton("⬅️ Main Menu",callback_data="m_main"))
    return k

# =============== /menu command ===============
@bot.message_handler(commands=["menu"])
@admin_only
def h_menu(m):bot.send_message(m.chat.id,MAIN_MENU_TEXT,reply_markup=kb_main(),parse_mode="HTML")

# =============== START: add menu button to /start ===============
@bot.message_handler(commands=["start","help"])
@admin_only
def h_start(m):
    bot.send_message(m.chat.id,
"""<b>🤖 Welcome to Alex Stor Bot v3 — AI Shop Promotion Bot!</b>

<b>Quick Start:</b>
1. Tap <i>📝 New Ad</i> to create your first ad
2. Tap <i>➕ Add Target</i> to add a group/channel
3. Set safety: <i>⚙️ Settings</i> (delay 5s, random on, blacklist "admin")

Neeche button menu hai — sab kuch tap karke karo!
Type /help2 for full text command list, /menu for menu.""", parse_mode="HTML", reply_markup=kb_main())

# =============== CALLBACK ROUTER ===============
@bot.callback_query_handler(func=lambda c:True)
def cb_router(c):
    if not is_admin(c.from_user):
        bot.answer_callback_query(c.id,"Not allowed");return
    d=c.data
    try:
        if d=="m_main":
            bot.edit_message_text(MAIN_MENU_TEXT,c.message.chat.id,c.message.id,reply_markup=kb_main(),parse_mode="HTML")
        elif d=="m_close":
            bot.delete_message(c.message.chat.id,c.message.id)
        elif d=="m_addpreset":
            STATE[c.from_user.id]={"act":"menu_newpreset"}
            bot.edit_message_text("<b>📝 New Ad</b>\n\nAd ka naam likh ke bhejein (e.g. promo, deal, welcome):",c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_back("m_main"))
        elif d=="m_presets":
            bot.edit_message_text("<b>📦 My Ads (Presets)</b>\nTap to view/edit:",c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_presets())
        elif d=="m_targets":
            bot.edit_message_text(f"<b>🎯 Targets ({len(D['targets'])})</b>\nTap to configure:",c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_targets())
        elif d=="m_addtarget":
            STATE[c.from_user.id]={"act":"menu_addtarget"}
            bot.edit_message_text("<b>➕ Add Target</b>\n\nTarget bhejein (@username, -100xxx, ya t.me link):",c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_back("m_targets"))
        elif d=="m_sendnow":
            p=pick_preset()
            if not p:
                bot.answer_callback_query(c.id,"Pehle ad banao!",show_alert=True);return
            bot.edit_message_text("<b>⚡ Send Now</b>\nKahan bhejna hai?",c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_sendnow())
        elif d=="m_schedule":
            bot.edit_message_text("<b>⏰ Schedule</b>\nChoose type:",c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_schedule())
        elif d=="m_kw":
            bot.edit_message_text("<b>🔑 Keyword Triggers</b>\nJab koi group mein ye word bole, ad auto-jayega:",c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_kw())
        elif d=="m_queue":
            items=D["queue"]
            txt=f"<b>📋 Queue ({len(items)})</b>\n"
            for i,it in enumerate(items,1): txt+=f"{i}. {it['p']} → {it.get('t') or 'all'}\n"
            bot.edit_message_text(txt,c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_queue())
        elif d=="m_settings":
            bot.edit_message_text("<b>⚙️ Settings</b>",c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_settings())
        elif d=="m_stats":
            bot.edit_message_text("<b>📊 Stats & Logs</b>",c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_stats())
        elif d=="m_help":
            txt="<b>🆘 Quick Help</b>\n\n1. Pehle /setprivacy ko @BotFather se DISABLE karna mat bhoolna\n2. Bot ko group mein ADMIN banana zaroori hai\n3. <b>Safety tips:</b>\n   • Delay 5+ seconds rakho\n   • Blacklist mein 'admin','mod','spam' add karo\n   • Random delay ON rakho (insan lage)\n   • Quiet hours raat ko chalao\n4. Tap menu se sab kuch ho jata hai\n\nFull commands: /help2"
            bot.edit_message_text(txt,c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_back("m_main"))
        # ----- Target actions -----
        elif d.startswith("t_view_"):
            cid=d.split("_",2)[2]
            g=D["targets"].get(str(cid),{})
            txt=f"<b>🎯 {g.get('title','?')}</b>\nID: <code>{cid}</code>\nAuto: {'ON' if g.get('a',1) else 'OFF'}\nDelay: {g.get('d') or D['delay']}s\nRate limit: {g.get('rl') or 'off'}\nPin: {'ON' if g.get('pin') else 'OFF'}\nReaction: {g.get('r') or 'none'}\nAd: {g.get('p') or '(default)'}"
            bot.edit_message_text(txt,c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_target_view(cid))
        elif d.startswith("t_toggleauto_"):
            cid=d.split("_",2)[2]
            g=D["targets"][str(cid)];g["a"]=0 if g.get("a",1) else 1;D["targets"][str(cid)]=g;save()
            bot.answer_callback_query(c.id,f"Auto: {'ON' if g['a'] else 'OFF'}")
            bot.edit_message_reply_markup(c.message.chat.id,c.message.id,reply_markup=kb_target_view(cid))
        elif d.startswith("t_togglepin_"):
            cid=d.split("_",2)[2]
            g=D["targets"][str(cid)];g["pin"]=0 if g.get("pin") else 1;D["targets"][str(cid)]=g;save()
            bot.answer_callback_query(c.id,f"Pin: {'ON' if g['pin'] else 'OFF'}")
            bot.edit_message_reply_markup(c.message.chat.id,c.message.id,reply_markup=kb_target_view(cid))
        elif d.startswith("t_del_"):
            cid=d.split("_",2)[2]
            if str(cid) in D["targets"]:
                t=D["targets"].pop(str(cid));save()
            bot.answer_callback_query(c.id,"Deleted");
            bot.edit_message_text(f"🗑 Target delete ho gaya.",c.message.chat.id,c.message.id,reply_markup=kb_back("m_targets"))
        elif d.startswith("t_delay_"):
            cid=d.split("_",2)[2]
            STATE[c.from_user.id]={"act":"menu_t_delay","cid":cid}
            bot.edit_message_text("⏱ Delay seconds mein likho (e.g. 5):",c.message.chat.id,c.message.id,reply_markup=kb_back(f"t_view_{cid}"))
        elif d.startswith("t_rl_"):
            cid=d.split("_",2)[2]
            STATE[c.from_user.id]={"act":"menu_t_rl","cid":cid}
            bot.edit_message_text("🚦 Rate limit minutes mein likho (e.g. 20 — 20 min mein 1 hi ad):",c.message.chat.id,c.message.id,reply_markup=kb_back(f"t_view_{cid}"))
        elif d.startswith("t_react_"):
            cid=d.split("_",2)[2]
            STATE[c.from_user.id]={"act":"menu_t_react","cid":cid}
            bot.edit_message_text("👍 Reaction emoji bhejo (ya off likho):",c.message.chat.id,c.message.id,reply_markup=kb_back(f"t_view_{cid}"))
        # ----- Preset actions -----
        elif d.startswith("p_view_"):
            n=d.split("_",2)[2]
            p=D["presets"][n]
            txt=f"<b>📝 Ad: {n}</b>\nType: {p['k']}\nButtons: {len(p.get('b',[]))}\nSilent: {'ON' if p.get('silent') else 'OFF'}\nPreview: {'OFF' if p.get('nopv') else 'ON'}\n\nText: {(p.get('t','') or '')[:300]}"
            bot.edit_message_text(txt,c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_preset_view(n))
        elif d.startswith("p_preview_"):
            n=d.split("_",2)[2]
            bot.answer_callback_query(c.id,"Preview bhej raha hoon...")
            send_preset(c.message.chat.id,D["presets"][n],ctx={"first_name":c.from_user.first_name or "friend","username":f"@{c.from_user.username}" if c.from_user.username else ""})
        elif d.startswith("p_setdef_"):
            n=d.split("_",2)[2]
            D["defpreset"]=n;save()
            bot.answer_callback_query(c.id,f"Default: {n}")
            bot.edit_message_reply_markup(c.message.chat.id,c.message.id,reply_markup=kb_preset_view(n))
        elif d.startswith("p_togglesilent_"):
            n=d.split("_",2)[2]
            p=D["presets"][n];p["silent"]=0 if p.get("silent") else 1;D["presets"][n]=p;save()
            bot.answer_callback_query(c.id,f"Silent: {'ON' if p['silent'] else 'OFF'}")
            bot.edit_message_reply_markup(c.message.chat.id,c.message.id,reply_markup=kb_preset_view(n))
        elif d.startswith("p_togglenopv_"):
            n=d.split("_",2)[2]
            p=D["presets"][n];p["nopv"]=0 if p.get("nopv") else 1;D["presets"][n]=p;save()
            bot.answer_callback_query(c.id,f"Link preview: {'OFF' if p['nopv'] else 'ON'}")
            bot.edit_message_reply_markup(c.message.chat.id,c.message.id,reply_markup=kb_preset_view(n))
        elif d.startswith("p_del_"):
            n=d.split("_",2)[2]
            if n in D["presets"]:
                del D["presets"][n]
                if D["defpreset"]==n:D["defpreset"]=""
                save()
            bot.answer_callback_query(c.id,"Deleted")
            bot.edit_message_text(f"🗑 Ad '{n}' delete ho gaya.",c.message.chat.id,c.message.id,reply_markup=kb_back("m_presets"))
        elif d.startswith("p_editbtns_"):
            n=d.split("_",2)[2]
            STATE[c.from_user.id]={"act":"menu_p_btns","name":n}
            bot.edit_message_text(f"✏️ Buttons format mein bhejein:\n<code>Text1|https://url1, Text2|https://url2</code>\nYa - likho for no buttons:",c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_back(f"p_view_{n}"))
        # ----- Settings toggles -----
        elif d=="s_togglemaster":
            D["on"]=0 if D["on"] else 1;save()
            bot.answer_callback_query(c.id,f"Master: {'ON' if D['on'] else 'OFF'}")
            bot.edit_message_reply_markup(c.message.chat.id,c.message.id,reply_markup=kb_settings())
        elif d=="s_toggletyping":
            D["typing"]=0 if D["typing"] else 1;save()
            bot.answer_callback_query(c.id,f"Typing: {'ON' if D['typing'] else 'OFF'}")
            bot.edit_message_reply_markup(c.message.chat.id,c.message.id,reply_markup=kb_settings())
        elif d=="s_toggleranddelay":
            D["randdelay"]=0 if D["randdelay"] else 1;save()
            bot.answer_callback_query(c.id,f"Random: {'ON' if D['randdelay'] else 'OFF'}")
            bot.edit_message_reply_markup(c.message.chat.id,c.message.id,reply_markup=kb_settings())
        elif d=="s_togglerotate":
            D["rotate"]=0 if D["rotate"] else 1;save()
            bot.answer_callback_query(c.id,f"Rotate: {'ON' if D['rotate'] else 'OFF'}")
            bot.edit_message_reply_markup(c.message.chat.id,c.message.id,reply_markup=kb_settings())
        elif d=="s_quiet":
            D["quiet"]["on"]=0 if D["quiet"]["on"] else 1;save()
            bot.answer_callback_query(c.id,f"Quiet: {'ON' if D['quiet']['on'] else 'OFF'}")
            bot.edit_message_reply_markup(c.message.chat.id,c.message.id,reply_markup=kb_settings())
        elif d=="s_delay":
            STATE[c.from_user.id]={"act":"menu_s_delay"}
            bot.edit_message_text("⏱ Global delay seconds mein (e.g. 5):",c.message.chat.id,c.message.id,reply_markup=kb_back("m_settings"))
        elif d=="s_jitter":
            STATE[c.from_user.id]={"act":"menu_s_jitter"}
            bot.edit_message_text("🎲 Random jitter seconds mein (e.g. 6 = ±6s):",c.message.chat.id,c.message.id,reply_markup=kb_back("m_settings"))
        elif d=="s_blacklist":
            blk_u=", ".join(str(x) for x in D["blk_u"]) or "none"
            blk_w=", ".join(D["blk_w"]) or "none"
            STATE[c.from_user.id]={"act":"menu_blacklist"}
            bot.edit_message_text(f"<b>🚫 Blacklist</b>\nUsers: {blk_u}\nWords: {blk_w}\n\nUser ID add/remove karne ke liye ID bhejo, word add/remove ke liye word bhejo (prefix 'user:' ya 'word:'):\nExample: <code>word:admin</code>",c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_back("m_settings"))
        elif d=="s_admins":
            al=", ".join(str(x) for x in D["admins"]) or "none"
            STATE[c.from_user.id]={"act":"menu_admin"}
            bot.edit_message_text(f"<b>👥 Admins:</b> {al}\n\nNaya admin add karne ke liye ID bhejo:",c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_back("m_settings"))
        elif d=="s_backup":
            buf=BytesIO(json.dumps(D,ensure_ascii=False,indent=2).encode("utf-8"))
            buf.name=f"backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
            bot.send_document(c.message.chat.id,buf,caption="📁 Backup file")
            bot.answer_callback_query(c.id,"Backup bhej diya")
        # ----- Send now -----
        elif d=="sn_all":
            p=pick_preset()
            res=send_to_targets(p)
            bot.answer_callback_query(c.id,res,show_alert=True)
        elif d.startswith("sn_one_"):
            cid=int(d.split("_",2)[2])
            p=pick_preset(str(cid))
            res=send_to_targets(p,cid)
            bot.answer_callback_query(c.id,res,show_alert=True)
        # ----- Schedule -----
        elif d=="sch_once":
            STATE[c.from_user.id]={"act":"menu_sch_once"}
            bot.edit_message_text("⏰ Date+time bhejein format mein:\n<code>2026-09-01 20:00</code>\nTarget agar specific chahiye to end mein @username add kar do.",c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_back("m_schedule"))
        elif d=="sch_window":
            STATE[c.from_user.id]={"act":"menu_sch_window"}
            bot.edit_message_text("🎲 Time range bhejein:\n<code>09:00 11:00</code>\nHar din is range mein koi random time par ad jayega.",c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_back("m_schedule"))
        elif d=="sch_cron":
            STATE[c.from_user.id]={"act":"menu_sch_cron"}
            bot.edit_message_text('🔁 Cron expression bhejein (m h dom mon dow):\nExample: <code>0 9 * * *</code> (har din 9 AM)',c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_back("m_schedule"))
        elif d=="sch_list":
            jobs=[j for j in sched.get_jobs() if j.id not in ("qauto","polls")]
            if not jobs:
                bot.edit_message_text("📅 Koi scheduled job nahi.",c.message.chat.id,c.message.id,reply_markup=kb_back("m_schedule"));return
            txt="<b>📅 Scheduled Jobs:</b>\n"
            for j in jobs:
                nxt=j.next_run_time.strftime("%Y-%m-%d %H:%M") if j.next_run_time else "paused"
                txt+=f"• {nxt} — {str(j.trigger)[:40]}\n"
            txt+="\n/canceljobs se sab cancel."
            bot.edit_message_text(txt,c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_back("m_schedule"))
        # ----- Stats -----
        elif d=="st_show":
            o=f"<b>📊 Stats</b>\nSent: <b>{D['stats']['sent']}</b>\nFailed: <b>{D['stats']['fail']}</b>\nClicks: <b>{D['stats'].get('clicks',0)}</b>\n\n<b>Per group:</b>\n"
            targets_by_id={str(t['chat_id']):t.get('title',t['chat_id']) for t in D["targets"].values()}
            for cid,n in list(sorted(D["stats"]["per"].items(),key=lambda x:-x[1]))[:15]:
                o+=f"• {targets_by_id.get(cid,cid)}: {n}\n"
            bot.edit_message_text(o,c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_back("m_stats"))
        elif d=="st_logs20":
            if not D["logs"]:
                bot.edit_message_text("📜 Koi log nahi.",c.message.chat.id,c.message.id,reply_markup=kb_back("m_stats"));return
            txt="<b>📜 Last 20 logs:</b>\n"
            for e in D["logs"][:20]:
                mk="✅" if e["ok"] else "❌"
                txt+=f"{mk} [{e['ts'][5:16]}] {e['e'][:50]}\n"
            bot.edit_message_text(txt[:4000],c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_back("m_stats"))
        elif d=="st_status":
            o=f"""<b>📋 Status</b>
Master: {'🟢 ON' if D['on'] else '🔴 OFF'}
Typing: {'ON' if D['typing'] else 'OFF'}
Delay: {D['delay']}s ±{D['jitter']}s (random {'ON' if D['randdelay'] else 'OFF'})
Quiet: {'ON' if D['quiet']['on'] else 'OFF'} ({D['quiet']['s']}-{D['quiet']['e']})
Default ad: {D['defpreset'] or 'none'}
Rotate: {'ON' if D['rotate'] else 'OFF'}
Targets: {len(D['targets'])}
Ads: {len(D['presets'])}
Queue: {len(D['queue'])} (autoplay {'ON' if D['qauto'] else 'OFF'})
Jobs: {len([j for j in sched.get_jobs() if j.id not in ('qauto','polls')])}
Blacklist: {len(D['blk_u'])}u/{len(D['blk_w'])}w
Total sent: {D['stats']['sent']} (fail {D['stats']['fail']})"""
            bot.edit_message_text(o,c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_back("m_stats"))
        # ----- Queue -----
        elif d=="q_adddef":
            pn=D["defpreset"]
            if not pn:
                bot.answer_callback_query(c.id,"Pehle default ad set karo!",show_alert=True);return
            D["queue"].append({"p":pn,"t":None,"a":datetime.now().isoformat()});save()
            bot.answer_callback_query(c.id,"Queue mein add")
            bot.edit_message_reply_markup(c.message.chat.id,c.message.id,reply_markup=kb_queue())
        elif d=="q_sendnext":
            qjob();bot.answer_callback_query(c.id,"Agla item bhej diya agar tha")
        elif d=="q_toggleauto":
            D["qauto"]=0 if D["qauto"] else 1;save();ensure_qjob()
            bot.answer_callback_query(c.id,f"Autoplay: {'ON' if D['qauto'] else 'OFF'}")
            bot.edit_message_reply_markup(c.message.chat.id,c.message.id,reply_markup=kb_queue())
        elif d=="q_clear":
            D["queue"]=[];save()
            bot.answer_callback_query(c.id,"Clear");bot.edit_message_reply_markup(c.message.chat.id,c.message.id,reply_markup=kb_queue())
        # ----- KW -----
        elif d=="kw_add":
            STATE[c.from_user.id]={"act":"menu_kw_add"}
            bot.edit_message_text('🔑 Keyword trigger add karo format mein:\n<code>word | preset_name</code>\nExample: <code>chatgpt | promo</code>',c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_back("m_kw"))
        elif d.startswith("kw_del_"):
            i=int(d.split("_",2)[2])
            if 0<=i<len(D["kw"]):D["kw"].pop(i);save()
            bot.answer_callback_query(c.id,"Delete")
            bot.edit_message_text("<b>🔑 Keyword Triggers:</b>",c.message.chat.id,c.message.id,parse_mode="HTML",reply_markup=kb_kw())
        else:
            bot.answer_callback_query(c.id,f"?: {d}")
    except Exception as e:
        log.error(f"Callback error {d}: {e}")
        try:bot.answer_callback_query(c.id,f"Error: {str(e)[:60]}",show_alert=True)
        except:pass

# Update text handler to process menu-state text inputs too
# Wrap original catch to also handle menu states
_orig_catch = catch
def catch_with_menu(m):
    uid=m.from_user.id if m.from_user else None
    st=STATE.get(uid) if uid else None
    if is_admin(m.from_user) and st and st.get("act","").startswith("menu_"):
        act=st["act"];txt=(m.text or "").strip()
        try:
            if act=="menu_newpreset":
                if not txt:bot.reply_to(m,"Naam likho");return
                n=txt.lower().replace(" ","_")
                if n in D["presets"]:bot.reply_to(m,f"❌ '{n}' exists");return
                STATE[uid]={"act":"await_ptype","name":n,"med":[]}
                k=InlineKeyboardMarkup()
                for t in[("Text","text"),("Photo","photo"),("Video","video"),("Doc","document"),("Audio","audio"),("Voice","voice"),("Album","album")]:
                    k.add(InlineKeyboardButton(t[0],callback_data=f"pt:{t[1]}:{n}"))
                bot.send_message(m.chat.id,f"Type choose karein for ad '<b>{n}</b>':",reply_markup=k,parse_mode="HTML")
                return
            if act=="menu_addtarget":
                t=parse_target(txt)
                if not t:bot.reply_to(m,"Invalid. @username ya -100xxx bhejo");return
                try:
                    ch=bot.get_chat(t)
                    D["targets"][str(ch.id)]={"title":ch.title or ch.username or str(ch.id),"chat_id":ch.id,"a":1,"p":None,"d":None,"rl":None,"ls":None,"pin":0,"sd":0,"r":None}
                    save();bot.reply_to(m,f"✅ Add <b>{ch.title}</b>",parse_mode="HTML",reply_markup=kb_main())
                except Exception as e:bot.reply_to(m,f"❌ {e}")
                STATE.pop(uid,None);return
            if act=="menu_t_delay":
                try:
                    v=float(txt);cid=str(st["cid"])
                    if cid in D["targets"]:
                        D["targets"][cid]["d"]=None if v<=0 else v;save()
                    bot.reply_to(m,f"✅ Delay {v}s",reply_markup=kb_target_view(st["cid"]))
                except:bot.reply_to(m,"Number daalein")
                STATE.pop(uid,None);return
            if act=="menu_t_rl":
                cid=str(st["cid"])
                if txt.lower()=="off":v=None
                else:
                    try:v=int(txt)
                    except:bot.reply_to(m,"Number daalein ya off likho");return
                if cid in D["targets"]:
                    D["targets"][cid]["rl"]=v;save()
                bot.reply_to(m,f"✅ Rate limit: {v if v else 'off'}",reply_markup=kb_target_view(st["cid"]))
                STATE.pop(uid,None);return
            if act=="menu_t_react":
                cid=str(st["cid"])
                v=None if txt.lower()=="off" else txt
                if cid in D["targets"]:
                    D["targets"][cid]["r"]=v;save()
                bot.reply_to(m,f"✅ Reaction: {v if v else 'off'}",reply_markup=kb_target_view(st["cid"]))
                STATE.pop(uid,None);return
            if act=="menu_p_btns":
                n=st["name"];p=D["presets"].get(n)
                if not p:bot.reply_to(m,"Preset nahi mila");STATE.pop(uid,None);return
                if txt=="-":
                    p["b"]=[]
                else:
                    bs=[]
                    for seg in txt.split(","):
                        seg=seg.strip()
                        if "|" not in seg:bot.reply_to(m,"❌ Format galat. Text|url");return
                        t,u=seg.split("|",1);bs.append({"t":t.strip(),"u":u.strip()})
                    p["b"]=bs
                D["presets"][n]=p;save()
                bot.reply_to(m,f"✅ Buttons set ({len(p['b'])} pcs)",reply_markup=kb_preset_view(n))
                STATE.pop(uid,None);return
            if act=="menu_s_delay":
                try:D["delay"]=max(0,float(txt));save();bot.reply_to(m,f"✅ Delay {D['delay']}s",reply_markup=kb_settings())
                except:bot.reply_to(m,"Number daalein")
                STATE.pop(uid,None);return
            if act=="menu_s_jitter":
                try:D["jitter"]=max(0,float(txt));save();bot.reply_to(m,f"✅ Jitter ±{D['jitter']}s",reply_markup=kb_settings())
                except:bot.reply_to(m,"Number daalein")
                STATE.pop(uid,None);return
            if act=="menu_blacklist":
                if txt.lower().startswith("user:"):
                    try:
                        uidv=int(txt[5:].strip())
                        if uidv in D["blk_u"]:D["blk_u"].remove(uidv);msg="remove"
                        else:D["blk_u"].append(uidv);msg="add"
                        save();bot.reply_to(m,f"✅ User {msg}",reply_markup=kb_settings())
                    except:bot.reply_to(m,"user:ID")
                elif txt.lower().startswith("word:"):
                    w=txt[5:].strip().lower()
                    if w in D["blk_w"]:D["blk_w"].remove(w);msg="remove"
                    else:D["blk_w"].append(w);msg="add"
                    save();bot.reply_to(m,f"✅ Word {msg}",reply_markup=kb_settings())
                else:
                    bot.reply_to(m,"Prefix 'user:' ya 'word:' lagao. Example: word:admin");return
                STATE.pop(uid,None);return
            if act=="menu_admin":
                if not txt.lstrip("-").isdigit():bot.reply_to(m,"ID number daalein");return
                aid=int(txt)
                if aid==OWNER:bot.reply_to(m,"Owner already admin");return
                if aid in D["admins"]:D["admins"].remove(aid);m2="remove"
                else:D["admins"].append(aid);m2="add"
                save();bot.reply_to(m,f"✅ Admin {m2}",reply_markup=kb_settings())
                STATE.pop(uid,None);return
            if act=="menu_sch_once":
                toks=txt.rsplit(" ",1);tgt=None;ts=txt
                if len(toks)==2 and parse_target(toks[1]):tgt=parse_target(toks[1]);ts=toks[0]
                try:dt=datetime.strptime(ts.strip(),"%Y-%m-%d %H:%M")
                except:bot.reply_to(m,"Format galat. YYYY-MM-DD HH:MM");return
                pn=D["defpreset"]
                if not pn:bot.reply_to(m,"Pehle default ad set karo");return
                jid=f"once_{dt.timestamp()}_{random.randint(1000,9999)}"
                sched.add_job(job_run,"date",run_date=dt,args=[pn,str(tgt) if tgt else None,jid],id=jid,misfire_grace_time=3600)
                bot.reply_to(m,f"⏰ Schedule: {dt:%Y-%m-%d %H:%M}",reply_markup=kb_back("m_schedule"))
                STATE.pop(uid,None);return
            if act=="menu_sch_window":
                toks=txt.rsplit(" ",1);tgt=None;win=txt
                if len(toks)==2 and parse_target(toks[1]):tgt=parse_target(toks[1]);win=toks[0]
                try:
                    s,e=win.strip().split()
                    sh,sm=map(int,s.split(":"));eh,em=map(int,e.split(":"))
                    smin=sh*60+sm;emin=eh*60+em
                    if emin<=smin:emin=24*60
                    ch=random.randint(smin,emin);h,mn=divmod(ch,60)
                except:bot.reply_to(m,"Format HH:MM HH:MM");return
                pn=D["defpreset"]
                if not pn:bot.reply_to(m,"Pehle default ad set karo");return
                jid=f"cron_{time.time()}_{random.randint(1000,9999)}"
                trig=CronTrigger.from_crontab(f"{mn} {h} * * *",timezone=TZ)
                sched.add_job(job_run,trigger=trig,args=[pn,str(tgt) if tgt else None,jid],id=jid,misfire_grace_time=3600)
                bot.reply_to(m,f"🎲 Roz <b>{h:02d}:{mn:02d}</b> par (random in {win})",parse_mode="HTML",reply_markup=kb_back("m_schedule"))
                STATE.pop(uid,None);return
            if act=="menu_sch_cron":
                toks=txt.rsplit(" ",1);tgt=None;cr=txt
                if len(toks)==2 and parse_target(toks[1]):tgt=parse_target(toks[1]);cr=toks[0]
                cr=cr.strip().strip('"')
                pn=D["defpreset"]
                if not pn:bot.reply_to(m,"Pehle default ad set karo");return
                try:
                    jid=f"cron_{time.time()}_{random.randint(1000,9999)}"
                    trig=CronTrigger.from_crontab(cr,timezone=TZ)
                    sched.add_job(job_run,trigger=trig,args=[pn,str(tgt) if tgt else None,jid],id=jid,misfire_grace_time=3600)
                except Exception as e:bot.reply_to(m,f"❌ Cron invalid: {e}");return
                bot.reply_to(m,f"⏰ Cron add: {cr}",reply_markup=kb_back("m_schedule"))
                STATE.pop(uid,None);return
            if act=="menu_kw_add":
                if "|" not in txt:bot.reply_to(m,"Format: word | preset");return
                kw,pn=[x.strip().lower() for x in txt.split("|",1)]
                if pn not in D["presets"]:bot.reply_to(m,"Preset nahi mila");return
                D["kw"].append({"k":kw,"p":pn,"m":"contains","c":None});save()
                bot.reply_to(m,f"✅ Trigger '{kw}' → {pn}",reply_markup=kb_kw())
                STATE.pop(uid,None);return
        except Exception as e:
            bot.reply_to(m,f"❌ {e}");STATE.pop(uid,None)
        return
    return _orig_catch(m)

# Replace original
catch = catch_with_menu

# Also add /menu to BotFather bot commands list for easy access
# (User can set this in BotFather via /setcommands)
