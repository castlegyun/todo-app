import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv
from flask import Flask, g, jsonify, request

BASE = Path(__file__).parent
load_dotenv(BASE / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise SystemExit(".env에 SUPABASE_URL과 SUPABASE_ANON_KEY를 설정해 주세요.")

PORT = int(os.environ.get("PORT", "5000"))
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
TIMEZONE = ZoneInfo(os.environ.get("APP_TIMEZONE", "Asia/Seoul"))

ACCESS_COOKIE = "todo_at"
REFRESH_COOKIE = "todo_rt"
REFRESH_MAX_AGE = 60 * 60 * 24 * 30
TIMEOUT = 10
COLUMNS = "id,title,is_done,due_date,created_at,completed_at"

app = Flask(__name__, static_folder="static", static_url_path="")


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


@app.errorhandler(ApiError)
def handle_api_error(err):
    return jsonify({"error": err.message}), err.status


@app.errorhandler(requests.RequestException)
def handle_network_error(_err):
    return jsonify({"error": "데이터베이스 서버에 연결하지 못했습니다."}), 502


def error(message, status=400):
    return jsonify({"error": message}), status


# ---------- Supabase 호출 (키는 이 파일 안에서만 사용) ----------

def headers(token=None):
    h = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def auth_call(path, payload=None, token=None, method="POST", params=None):
    return requests.request(
        method, f"{SUPABASE_URL}/auth/v1/{path}",
        headers=headers(token), json=payload, params=params, timeout=TIMEOUT,
    )


def to_session(data):
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "expires_in": int(data.get("expires_in", 3600)),
    }


def renew():
    """refresh 쿠키로 새 세션을 받아 오고, 응답에 새 쿠키를 싣도록 표시한다."""
    refresh = request.cookies.get(REFRESH_COOKIE)
    if not refresh:
        return None
    r = auth_call("token", {"refresh_token": refresh}, params={"grant_type": "refresh_token"})
    if r.status_code != 200:
        return None
    g.new_session = to_session(r.json())
    g.token = g.new_session["access_token"]
    g.renewed = True
    return g.token


def authed(call):
    """로그인 토큰으로 call(token)을 실행. 만료됐으면 한 번 갱신해서 재시도."""
    token = g.get("token") or request.cookies.get(ACCESS_COOKIE) or renew()
    if not token:
        raise ApiError("로그인이 필요합니다.", 401)
    r = call(token)
    if r.status_code == 401 and not g.get("renewed"):
        token = renew()
        if token:
            r = call(token)
    if r.status_code == 401:
        raise ApiError("로그인이 필요합니다.", 401)
    return r


def rest(method, params=None, body=None):
    def call(token):
        h = headers(token)
        h["Prefer"] = "return=representation"
        return requests.request(
            method, f"{SUPABASE_URL}/rest/v1/todo",
            headers=h, params=params, json=body, timeout=TIMEOUT,
        )

    r = authed(call)
    if r.status_code >= 400:
        app.logger.warning("Supabase REST %s -> %s %s", method, r.status_code, r.text[:300])
        raise ApiError("요청을 처리하지 못했습니다.", 400)
    return r.json() if r.content else []


# ---------- 쿠키 ----------

def set_session_cookies(resp, s):
    opts = {"httponly": True, "samesite": "Lax", "secure": COOKIE_SECURE, "path": "/"}
    resp.set_cookie(ACCESS_COOKIE, s["access_token"], max_age=s["expires_in"], **opts)
    resp.set_cookie(REFRESH_COOKIE, s["refresh_token"], max_age=REFRESH_MAX_AGE, **opts)


@app.after_request
def apply_cookies(resp):
    if g.get("clear_session"):
        resp.delete_cookie(ACCESS_COOKIE, path="/")
        resp.delete_cookie(REFRESH_COOKIE, path="/")
    elif g.get("new_session"):
        set_session_cookies(resp, g.new_session)
    return resp


# ---------- 로그인 ----------

AUTH_MESSAGES = {
    "invalid_credentials": "이메일 또는 비밀번호가 올바르지 않습니다.",
    "email_not_confirmed": "이메일 인증이 필요합니다. 받은 메일의 링크를 눌러 주세요.",
    "user_already_exists": "이미 가입된 이메일입니다.",
    "weak_password": "비밀번호가 너무 약합니다. 더 길게 만들어 주세요.",
    "over_email_send_rate_limit": "메일을 너무 자주 보냈습니다. 잠시 후 다시 시도해 주세요.",
    "validation_failed": "이메일 형식을 확인해 주세요.",
}


def auth_error(r):
    try:
        data = r.json()
    except ValueError:
        data = {}
    return error(AUTH_MESSAGES.get(data.get("error_code"), "로그인 처리에 실패했습니다."), 400)


def credentials():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    if "@" not in email:
        raise ApiError("이메일 형식을 확인해 주세요.")
    if len(password) < 6:
        raise ApiError("비밀번호는 6자 이상이어야 합니다.")
    return email, password


@app.post("/api/auth/signup")
def signup():
    email, password = credentials()
    r = auth_call("signup", {"email": email, "password": password})
    if r.status_code >= 400:
        return auth_error(r)
    data = r.json()
    if data.get("access_token"):
        g.new_session = to_session(data)
        return jsonify({"logged_in": True, "email": email}), 201
    return jsonify({
        "logged_in": False,
        "message": "확인 메일을 보냈습니다. 메일의 링크를 누른 뒤 로그인해 주세요.",
    }), 201


@app.post("/api/auth/login")
def login():
    email, password = credentials()
    r = auth_call("token", {"email": email, "password": password}, params={"grant_type": "password"})
    if r.status_code >= 400:
        return auth_error(r)
    data = r.json()
    g.new_session = to_session(data)
    return jsonify({"logged_in": True, "email": (data.get("user") or {}).get("email", email)})


@app.post("/api/auth/logout")
def logout():
    token = request.cookies.get(ACCESS_COOKIE)
    if token:
        try:
            auth_call("logout", token=token, params={"scope": "local"})
        except requests.RequestException:
            pass
    g.clear_session = True
    return "", 204


@app.get("/api/me")
def me():
    r = authed(lambda token: auth_call("user", token=token, method="GET"))
    if r.status_code >= 400:
        raise ApiError("로그인이 필요합니다.", 401)
    return jsonify({"email": r.json().get("email")})


# ---------- 할 일 ----------

def today():
    return datetime.now(TIMEZONE).date().isoformat()


def valid_date(value):
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except (TypeError, ValueError):
        return False


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/api/todos")
def list_todos():
    params = {"select": COLUMNS, "order": "is_done.asc,due_date.asc.nullslast,id.asc"}
    if request.args.get("filter") == "today":
        params["due_date"] = f"eq.{today()}"
        params["is_done"] = "eq.false"
    return jsonify(rest("GET", params))


@app.post("/api/todos")
def add_todo():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    due_date = data.get("due_date") or None
    if not title:
        return error("할 일 내용을 입력해 주세요.")
    if len(title) > 200:
        return error("할 일 내용은 200자 이하로 입력해 주세요.")
    if due_date is not None and not valid_date(due_date):
        return error("마감일은 YYYY-MM-DD 형식이어야 합니다.")

    # user_id는 보내지 않는다. DB가 로그인한 사용자 id(auth.uid())를 기록한다.
    rows = rest("POST", body={"title": title, "due_date": due_date})
    return jsonify(rows[0]), 201


@app.patch("/api/todos/<int:todo_id>")
def update_todo(todo_id):
    data = request.get_json(silent=True) or {}
    if not isinstance(data.get("is_done"), bool):
        return error("is_done 값(true/false)이 필요합니다.")

    completed_at = datetime.now(timezone.utc).isoformat() if data["is_done"] else None
    rows = rest(
        "PATCH", params={"id": f"eq.{todo_id}"},
        body={"is_done": data["is_done"], "completed_at": completed_at},
    )
    if not rows:
        return error("해당 할 일이 없습니다.", 404)
    return jsonify(rows[0])


@app.delete("/api/todos/<int:todo_id>")
def delete_todo(todo_id):
    rows = rest("DELETE", params={"id": f"eq.{todo_id}"})
    if not rows:
        return error("해당 할 일이 없습니다.", 404)
    return "", 204


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=PORT)
