
import json, os, sqlite3, secrets, hashlib, hmac
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
from pathlib import Path

APP_VERSION = "4.1"

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
DB_PATH = ROOT / "bachaco.db"
PORT = int(os.environ.get("PORT", "3000"))
SESSIONS = {}
SESSION_TTL = 60 * 60 * 24 * 30

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn=db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT NOT NULL UNIQUE COLLATE NOCASE,
      name TEXT NOT NULL,
      password_salt TEXT NOT NULL,
      password_hash TEXT NOT NULL,
      is_admin INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS user_data(
      user_id INTEGER PRIMARY KEY,
      data TEXT NOT NULL,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    row=conn.execute("SELECT COUNT(*) n FROM users").fetchone()
    if row["n"]==0:
        salt, digest=make_password("Z0885259V")
        cur=conn.execute(
          "INSERT INTO users(username,name,password_salt,password_hash,is_admin) VALUES(?,?,?,?,1)",
          ("Diego","Diego",salt,digest))
        conn.execute("INSERT INTO user_data(user_id,data) VALUES(?,?)",
                     (cur.lastrowid,json.dumps(default_data(),ensure_ascii=False)))
        conn.commit()
        print("Usuario inicial creado: Diego")
    conn.close()

def default_data():
    return {
      "transactions":[],
      "fixed":[
        {"id":"f1","name":"Arriendo","amount":0,"active":True,"icon":"🏠"},
        {"id":"f2","name":"Mercado","amount":0,"active":True,"icon":"🛒"},
        {"id":"f3","name":"Transporte","amount":0,"active":True,"icon":"🚌"}],
      "goals":[
        {"id":"g1","name":"Clases Autoescuela","icon":"🎓","target":0,"pct":0},
        {"id":"g2","name":"PC Gamer","icon":"💻","target":0,"pct":0},
        {"id":"g3","name":"Entrada Primer Coche","icon":"🚗","target":0,"pct":0}],
      "fixedSnapshots":{},
      "futureExpenses":[],
    "privateData":{"pareja":[],"tarjeta":[],"tarjetaMeta":{"creditUsed":0,"limit":0}}
    }

def make_password(password):
    salt=secrets.token_bytes(16)
    digest=hashlib.scrypt(password.encode(),salt=salt,n=16384,r=8,p=1,dklen=64)
    return salt.hex(),digest.hex()

def check_password(password,salt_hex,digest_hex):
    try:
        actual=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt_hex),n=16384,r=8,p=1,dklen=64).hex()
        return hmac.compare_digest(actual,digest_hex)
    except Exception:
        return False

def clean_data(d):
    base=default_data()
    if not isinstance(d,dict): return base
    pd=d.get("privateData",{})
    meta=pd.get("tarjetaMeta",{}) if isinstance(pd,dict) else {}
    if not isinstance(meta,dict): meta={}
    try: credit_used=max(0,float(meta.get("creditUsed",0) or 0))
    except (TypeError,ValueError): credit_used=0
    try: card_limit=max(0,float(meta.get("limit",0) or 0))
    except (TypeError,ValueError): card_limit=0
    return {
      "transactions": d.get("transactions",[]) if isinstance(d.get("transactions",[]),list) else [],
      "fixed": d.get("fixed",base["fixed"]) if isinstance(d.get("fixed",base["fixed"]),list) else base["fixed"],
      "goals": d.get("goals",base["goals"]) if isinstance(d.get("goals",base["goals"]),list) else base["goals"],
      "fixedSnapshots": d.get("fixedSnapshots",{}) if isinstance(d.get("fixedSnapshots",{}),dict) else {},
      "futureExpenses": d.get("futureExpenses",[]) if isinstance(d.get("futureExpenses",[]),list) else [],
      "privateData":{
        "pareja":pd.get("pareja",[]) if isinstance(pd,dict) and isinstance(pd.get("pareja",[]),list) else [],
                "tarjeta":pd.get("tarjeta",[]) if isinstance(pd,dict) and isinstance(pd.get("tarjeta",[]),list) else [],
                "tarjetaMeta":{"creditUsed":credit_used,"limit":card_limit}
      }
    }

def current_user(handler):
    token=handler.cookies.get("bachaco_session")
    if not token: return None
    item=SESSIONS.get(token)
    if not item: return None
    user_id, expires=item
    import time
    if expires < time.time():
        SESSIONS.pop(token,None); return None
    conn=db()
    row=conn.execute("SELECT id,username,name,is_admin FROM users WHERE id=?",(user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(PUBLIC),**kwargs)

    def log_message(self,format,*args):
        pass

    @property
    def cookies(self):
        raw=self.headers.get("Cookie","")
        out={}
        for part in raw.split(";"):
            if "=" in part:
                k,v=part.strip().split("=",1); out[k]=v
        return out

    def send_json(self,status,data,headers=None):
        body=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(body)))
        if headers:
            for k,v in headers.items(): self.send_header(k,v)
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length=int(self.headers.get("Content-Length","0"))
        raw=self.rfile.read(length)
        try: return json.loads(raw.decode("utf-8") or "{}")
        except Exception: return {}

    def require_user(self):
        u=current_user(self)
        if not u:
            self.send_json(401,{"error":"Sesión no válida."}); return None
        return u

    def do_GET(self):
        path=urlparse(self.path).path
        if path.startswith("/api/"):
            u=current_user(self)
            if path=="/api/me":
                return self.send_json(200,{"user":({**u,"isAdmin":bool(u["is_admin"])} if u else None)})
            if path=="/api/state":
                if not u: return self.send_json(401,{"error":"Sesión no válida."})
                conn=db(); row=conn.execute("SELECT data FROM user_data WHERE user_id=?",(u["id"],)).fetchone()
                conn.close()
                data=clean_data(json.loads(row["data"])) if row else default_data()
                return self.send_json(200,data)
            if path=="/api/users":
                if not u or not u["is_admin"]: return self.send_json(403,{"error":"Solo un administrador puede hacer esto."})
                conn=db(); rows=conn.execute("SELECT id,username,name,is_admin,created_at FROM users ORDER BY id").fetchall(); conn.close()
                return self.send_json(200,{"users":[{**dict(r),"isAdmin":bool(r["is_admin"])} for r in rows]})
            return self.send_json(404,{"error":"Ruta API no encontrada."})
        # Evita que Chrome/Firefox reutilicen un index.html antiguo durante el desarrollo.
        if path in ('/', '/index.html'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            body=(PUBLIC / 'index.html').read_bytes()
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()

    def do_POST(self):
        path=urlparse(self.path).path
        data=self.read_json()
        if path=="/api/login":
            username=str(data.get("username","")).strip()
            password=str(data.get("password",""))
            conn=db(); row=conn.execute("SELECT * FROM users WHERE username=?",(username,)).fetchone(); conn.close()
            if not row or not check_password(password,row["password_salt"],row["password_hash"]):
                return self.send_json(401,{"error":"Usuario o contraseña incorrectos."})
            token=secrets.token_urlsafe(32)
            import time
            SESSIONS[token]=(row["id"],time.time()+SESSION_TTL)
            cookie=f"bachaco_session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_TTL}"
            return self.send_json(200,{"ok":True,"user":{"id":row["id"],"username":row["username"],"name":row["name"],"isAdmin":bool(row["is_admin"])}},{"Set-Cookie":cookie})
        if path=="/api/logout":
            token=self.cookies.get("bachaco_session")
            if token: SESSIONS.pop(token,None)
            return self.send_json(200,{"ok":True},{"Set-Cookie":"bachaco_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"})
        if path=="/api/users":
            u=self.require_user()
            if not u or not u["is_admin"]: return
            username=str(data.get("username","")).strip()
            name=str(data.get("name","")).strip()
            password=str(data.get("password",""))
            import re
            if not re.fullmatch(r"[A-Za-z0-9._-]{2,32}",username):
                return self.send_json(400,{"error":"El usuario debe tener 2-32 caracteres válidos."})
            if not name or len(password)<6:
                return self.send_json(400,{"error":"Nombre obligatorio y contraseña de al menos 6 caracteres."})
            salt,digest=make_password(password)
            conn=db()
            try:
                cur=conn.execute("INSERT INTO users(username,name,password_salt,password_hash,is_admin) VALUES(?,?,?,?,0)",
                                  (username,name,salt,digest))
                conn.execute("INSERT INTO user_data(user_id,data) VALUES(?,?)",(cur.lastrowid,json.dumps(default_data(),ensure_ascii=False)))
                conn.commit()
            except sqlite3.IntegrityError:
                conn.close(); return self.send_json(409,{"error":"Ese usuario ya existe."})
            conn.close()
            return self.send_json(200,{"ok":True})
        return self.send_json(404,{"error":"Ruta API no encontrada."})

    def do_PUT(self):
        path=urlparse(self.path).path
        if path.startswith("/api/users/") and path.endswith("/password"):
            u=self.require_user()
            if not u: return
            try: target_id=int(path.split("/")[3])
            except Exception: return self.send_json(400,{"error":"Usuario no válido."})
            if target_id != u["id"] and not u["is_admin"]:
                return self.send_json(403,{"error":"Solo un administrador puede cambiar la contraseña de otro usuario."})
            new_password=str(self.read_json().get("password",""))
            if len(new_password)<6:
                return self.send_json(400,{"error":"La contraseña debe tener al menos 6 caracteres."})
            salt,digest=make_password(new_password)
            conn=db()
            row=conn.execute("SELECT id FROM users WHERE id=?",(target_id,)).fetchone()
            if not row:
                conn.close(); return self.send_json(404,{"error":"Usuario no encontrado."})
            conn.execute("UPDATE users SET password_salt=?,password_hash=? WHERE id=?",(salt,digest,target_id))
            conn.commit(); conn.close()
            return self.send_json(200,{"ok":True})
        if path!="/api/state": return self.send_json(404,{"error":"Ruta API no encontrada."})
        u=self.require_user()
        if not u: return
        data=clean_data(self.read_json())
        conn=db()
        conn.execute("""
          INSERT INTO user_data(user_id,data,updated_at) VALUES(?,?,CURRENT_TIMESTAMP)
          ON CONFLICT(user_id) DO UPDATE SET data=excluded.data,updated_at=CURRENT_TIMESTAMP
        """,(u["id"],json.dumps(data,ensure_ascii=False)))
        conn.commit(); conn.close()
        return self.send_json(200,{"ok":True})

if __name__=="__main__":
    init_db()
    print(f"El Bachaco Financiero en http://localhost:{PORT}")
    ThreadingHTTPServer(("0.0.0.0",PORT),Handler).serve_forever()
