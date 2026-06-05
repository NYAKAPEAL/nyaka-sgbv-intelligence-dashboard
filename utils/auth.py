"""utils/auth.py — Authentication, RBAC, session management, audit logging."""
import streamlit as st, time, datetime, hashlib, os
from config import DEMO_USERS, ROLES, SESSION_TIMEOUT, C

_AUDIT: list[dict] = []

def log(user, action, detail=""):
    _AUDIT.append({"ts": datetime.datetime.utcnow().isoformat(), "user": user,
                   "action": action, "detail": detail, "session": id(st.session_state)})

def _hash(pw): return hashlib.sha256(pw.encode()).hexdigest()

def _shared_password():
    """The single shared leadership password, read from Streamlit secrets
    (set in the cloud secret manager). Falls back to an env var, then to a
    local-dev default that should never be used in production."""
    try:
        pw = st.secrets.get("app_password")
        if pw:
            return str(pw)
    except Exception:
        pass
    return os.environ.get("APP_PASSWORD") or "nyaka-local-dev"


def login(username, password):
    # Single shared leadership login: any username + the shared password.
    if password and password == _shared_password():
        name = username.strip().title() if username.strip() else "Nyaka Leadership"
        st.session_state.update({
            "auth": True, "user": username.strip().lower() or "leadership",
            "role": "admin", "name": name,
            "login_t": time.time(), "last_t": time.time()
        })
        log(username, "LOGIN", "shared-admin")
        return True
    # Fallback to named accounts if explicitly configured (local/dev only)
    u = DEMO_USERS.get(username.strip().lower())
    if u and u["password"] == password:
        st.session_state.update({
            "auth": True, "user": username, "role": u["role"],
            "name": u["name"], "login_t": time.time(), "last_t": time.time()
        })
        log(username, "LOGIN", f"role={u['role']}")
        return True
    log(username, "FAIL_LOGIN")
    return False

def logout():
    log(st.session_state.get("user","?"), "LOGOUT")
    for k in ["auth","user","role","name","login_t","last_t"]:
        st.session_state.pop(k, None)

def check():
    if not st.session_state.get("auth"): return False
    if time.time() - st.session_state.get("last_t", 0) > SESSION_TIMEOUT * 60:
        st.warning("⏱ Session expired. Please sign in again.")
        logout(); return False
    st.session_state["last_t"] = time.time()
    return True

def role():      return st.session_state.get("role", "")
def role_cfg():  return ROLES.get(role(), {})
def can_export():return role_cfg().get("can_export", False)
def can_access(page): return page in role_cfg().get("pages", [])
def gis_precision(): return role_cfg().get("gis_precision", "district")

def show_login():
    import os as _os, base64 as _b64
    c1, c2, c3 = st.columns([1, 1.8, 1])
    with c2:
        _logo = _os.path.join(_os.path.dirname(__file__), "..", "assets", "logo",
                              "nyaka_horizontal_purple.png")
        if _os.path.exists(_logo):
            try:
                with open(_logo, "rb") as _f:
                    _b64logo = _b64.b64encode(_f.read()).decode()
                st.markdown(f"""
                <div style='background:#FFFFFF;border-radius:12px;padding:22px 26px;
                            margin:10px 0 6px;box-shadow:0 2px 10px rgba(0,0,0,0.08);
                            text-align:center;'>
                  <img src='data:image/png;base64,{_b64logo}'
                       style='width:100%;max-width:300px;height:auto;'/>
                </div>""", unsafe_allow_html=True)
            except Exception:
                st.image(_logo, use_container_width=True)
        st.markdown(f"""
        <div style='text-align:center;margin:6px 0 24px;'>
          <div style='font-size:22px;font-weight:700;color:{C["purple"]};margin:8px 0 4px;'>
            Nyaka SGBV Intelligence Platform
          </div>
          <div style='font-size:13px;color:{C["grey"]};'>
            Nyaka AIDS Orphans Project · Kanungu · Rukungiri · Rubanda · Uganda
          </div>
          <div style='background:{C["red_lt"]};border-left:4px solid {C["red"]};
                      padding:10px 14px;border-radius:6px;margin:16px 0;
                      font-size:12px;color:{C["red"]};text-align:left;'>
            🔒 Confidential system. Unauthorised access is prohibited.
            All sessions are logged and audited.
          </div>
        </div>""", unsafe_allow_html=True)
        with st.form("login"):
            user  = st.text_input("Username", placeholder="your.username")
            pw    = st.text_input("Password", type="password")
            sub   = st.form_submit_button("🔐  Sign In", use_container_width=True)
            if sub:
                if login(user, pw):
                    st.success(f"Welcome, {st.session_state['name']}!")
                    st.rerun()
                else:
                    st.error("Invalid credentials.")