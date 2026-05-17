"""
core/auth.py — Login gate for Agricultural Intelligence Portal.
"""
import hashlib
import streamlit as st
from supabase import create_client


def _get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def _hash(password: str) -> str:
    return hashlib.sha256(password.strip().encode()).hexdigest()

def _count_users() -> int:
    try:
        resp = _get_supabase().table("users").select("id", count="exact").execute()
        return resp.count or 0
    except Exception:
        return -1

def _verify(username: str, password: str) -> bool:
    try:
        resp = (
            _get_supabase().table("users")
            .select("password_hash")
            .eq("username", username.strip().lower())
            .single()
            .execute()
        )
        return bool(resp.data and resp.data["password_hash"] == _hash(password))
    except Exception:
        return False

def _create_user(username: str, password: str):
    try:
        _get_supabase().table("users").insert({
            "username":      username.strip().lower(),
            "password_hash": _hash(password),
        }).execute()
        return True, ""
    except Exception as e:
        msg = str(e)
        if "duplicate" in msg.lower() or "unique" in msg.lower():
            return False, "Username already exists."
        return False, msg

def _delete_user(username: str):
    try:
        _get_supabase().table("users").delete().eq("username", username).execute()
        return True, ""
    except Exception as e:
        return False, str(e)

def _list_users():
    try:
        resp = _get_supabase().table("users").select("username").order("username").execute()
        return [r["username"] for r in (resp.data or [])]
    except Exception:
        return []


_FORM_CSS = """
<style>
[data-testid="stSidebar"]      { display: none !important; }
header[data-testid="stHeader"] { display: none !important; }
.block-container { max-width: 420px; margin: 8vh auto 0; padding-top: 0; }
</style>
"""

_LOGO = """
<div style="text-align:center;margin-bottom:2rem;">
    <div style="font-size:40px;">🌱</div>
    <div style="font-size:22px;font-weight:700;margin-top:.4rem;">Agricultural Intelligence Portal</div>
</div>
"""


def _render_login_or_register() -> None:
    """Single screen with tab toggle between Sign in and Create account."""
    st.markdown(_FORM_CSS, unsafe_allow_html=True)
    st.markdown(_LOGO, unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["Sign in", "Create account"])

    # ── Sign in ───────────────────────────────────────────────────────────────
    with tab_login:
        with st.form("login_form"):
            username  = st.text_input("Username", key="li_user")
            password  = st.text_input("Password", type="password", key="li_pass")
            submitted = st.form_submit_button("Sign in",
                                              use_container_width=True, type="primary")
        if submitted:
            if not username or not password:
                st.error("Please enter both fields.")
            elif _verify(username, password):
                st.session_state["_auth_user"] = username.strip().lower()
                st.session_state["_auth_ok"]   = True
                st.rerun()
            else:
                st.error("Incorrect username or password.")

    # ── Create account ────────────────────────────────────────────────────────
    with tab_register:
        with st.form("register_form"):
            new_user  = st.text_input("Choose a username", key="reg_user")
            new_pass  = st.text_input("Choose a password", type="password", key="reg_pass")
            new_conf  = st.text_input("Confirm password",  type="password", key="reg_conf")
            submitted = st.form_submit_button("Create account & sign in",
                                              use_container_width=True, type="primary")
        if submitted:
            if not new_user or not new_pass:
                st.error("Username and password are required.")
            elif new_pass != new_conf:
                st.error("Passwords do not match.")
            elif len(new_pass) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                ok, err = _create_user(new_user, new_pass)
                if ok:
                    st.session_state["_auth_user"] = new_user.strip().lower()
                    st.session_state["_auth_ok"]   = True
                    st.rerun()
                else:
                    st.error(f"Could not create account: {err}")

    st.stop()


# ── Public API ────────────────────────────────────────────────────────────────

def require_login() -> None:
    """Call once per page after set_page_config(). Blocks if not logged in."""
    if st.session_state.get("_auth_ok"):
        return
    n = _count_users()
    if n == -1:
        st.error("⚠️ Cannot connect to user database. Check Supabase credentials.")
        st.stop()
    else:
        _render_login_or_register()   # same screen for first user and subsequent ones


def current_user() -> str:
    return st.session_state.get("_auth_user", "")


def logout() -> None:
    st.session_state.pop("_auth_ok",   None)
    st.session_state.pop("_auth_user", None)
    st.rerun()


def render_user_admin() -> None:
    """Optional admin panel — call from any page to manage users."""
    if not st.session_state.get("_auth_ok"):
        return

    st.subheader("👤 User Management")
    users = _list_users()
    if users:
        st.markdown("**Existing users**")
        for u in users:
            c1, c2 = st.columns([5, 1])
            c1.write(u)
            if u != current_user():
                if c2.button("Delete", key=f"del_{u}", use_container_width=True):
                    ok, err = _delete_user(u)
                    if ok:
                        st.success(f"Deleted '{u}'.")
                        st.rerun()
                    else:
                        st.error(f"Failed: {err}")
            else:
                c2.caption("(you)")
