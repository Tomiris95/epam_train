"""
🍽️ Meal Planner — Streamlit Frontend
Connects to the FastAPI backend at http://localhost:8000
"""
import os
import streamlit as st
import requests
from typing import Optional

API = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="🍽️ AI Meal Planner",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;500;600&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    h1, h2, h3 { font-family: 'Playfair Display', serif; }

    .meal-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #0f3460;
        border-radius: 16px;
        padding: 20px;
        margin: 10px 0;
        color: white;
    }
    .meal-card h3 { color: #e94560; margin: 0 0 8px 0; font-size: 1.1rem; }
    .meal-card .recipe-name { font-size: 1.3rem; font-weight: 600; color: #f5f5f5; }
    .meal-card .meta { color: #a0a0c0; font-size: 0.85rem; margin-top: 8px; }
    .tag { display: inline-block; background: #0f3460; color: #e94560;
           padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; margin: 2px; }
    .calorie-bar { background: #0f3460; border-radius: 8px; padding: 12px 16px; margin: 6px 0; }
    .approved-badge { background: #1a6b3a; color: #4ecca3;
                      padding: 4px 14px; border-radius: 20px; font-size: 0.8rem; }
    .section-header { border-left: 4px solid #e94560; padding-left: 12px; margin: 20px 0 10px 0; }
    .fridge-item { display: inline-block; background: #1e3a2f; color: #4ecca3;
                   padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; margin: 3px; }
    .shopping-item { display: flex; justify-content: space-between;
                     padding: 8px 12px; border-bottom: 1px solid #1a1a2e; }
    .stButton > button { border-radius: 10px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ─── Session State Init ──────────────────────────────────────────────────────
for key in ["family_id", "plan_id", "plan_data", "shopping_list", "token", "username"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ─── Tag constants & mutual-exclusivity callbacks ────────────────────────────
_PREFERRED_TAGS = ["vegetarian", "vegan", "gluten_free", "dairy_free", "no_red_meat",
                   "high_protein", "low_spice", "soft_food", "high_fiber", "toddler", "halal"]
_FORBIDDEN_TAGS = ["vegetarian", "vegan", "no_red_meat", "gluten_free", "dairy_free"]


def _on_stol5_checked():
    if st.session_state.get("a_stol5"):
        for t in _PREFERRED_TAGS:
            st.session_state[f"a_{t}"] = False
        for t in _FORBIDDEN_TAGS:
            st.session_state[f"f_{t}"] = False


def _on_other_tag_checked():
    any_other = any(st.session_state.get(f"a_{t}") for t in _PREFERRED_TAGS)
    any_forbidden = any(st.session_state.get(f"f_{t}") for t in _FORBIDDEN_TAGS)
    if any_other or any_forbidden:
        st.session_state["a_stol5"] = False


def _on_edit_stol5_checked(mid):
    if st.session_state.get(f"edit_a_{mid}_stol5"):
        for t in _PREFERRED_TAGS:
            st.session_state[f"edit_a_{mid}_{t}"] = False
        for t in _FORBIDDEN_TAGS:
            st.session_state[f"edit_f_{mid}_{t}"] = False


def _on_edit_other_checked(mid):
    any_other = any(st.session_state.get(f"edit_a_{mid}_{t}") for t in _PREFERRED_TAGS)
    any_forbidden = any(st.session_state.get(f"edit_f_{mid}_{t}") for t in _FORBIDDEN_TAGS)
    if any_other or any_forbidden:
        st.session_state[f"edit_a_{mid}_stol5"] = False


# ─── Helper Functions ────────────────────────────────────────────────────────
def _auth_headers() -> dict:
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _extract_error(r) -> str:
    try:
        detail = r.json().get("detail", r.text)
        if isinstance(detail, list):
            return "; ".join(item.get("msg", str(item)) for item in detail)
        return detail or f"HTTP {r.status_code}"
    except Exception:
        return r.text or f"HTTP {r.status_code}"


def api_get(path: str):
    try:
        r = requests.get(f"{API}{path}", headers=_auth_headers(), timeout=30)
        if r.status_code == 401:
            st.session_state.token = None
            st.error("Session expired. Please log in again.")
            st.rerun()
        if not r.ok:
            st.error(_extract_error(r))
            return None
        return r.json()
    except Exception as e:
        st.error(f"Connection error: {e}")
        return None


def api_post(path: str, data=None):
    try:
        r = requests.post(f"{API}{path}", json=data, headers=_auth_headers(), timeout=60)
        if r.status_code == 401:
            st.session_state.token = None
            st.error("Session expired. Please log in again.")
            st.rerun()
        if not r.ok:
            st.error(_extract_error(r))
            return None
        return r.json()
    except Exception as e:
        st.error(f"Connection error: {e}")
        return None


def api_put(path: str, data=None):
    try:
        r = requests.put(f"{API}{path}", json=data, headers=_auth_headers(), timeout=30)
        if r.status_code == 401:
            st.session_state.token = None
            st.error("Session expired. Please log in again.")
            st.rerun()
        if not r.ok:
            st.error(_extract_error(r))
            return None
        return r.json()
    except Exception as e:
        st.error(f"Connection error: {e}")
        return None


def api_delete(path: str):
    try:
        r = requests.delete(f"{API}{path}", headers=_auth_headers(), timeout=10)
        if r.status_code == 401:
            st.session_state.token = None
            st.error("Session expired. Please log in again.")
            st.rerun()
        if not r.ok:
            st.error(_extract_error(r))
            return None
        return r.json()
    except Exception as e:
        st.error(f"Connection error: {e}")
        return None


# ─── Auth Page ───────────────────────────────────────────────────────────────
def show_auth_page():
    st.markdown("# 🍽️ AI Meal Planner")
    st.markdown("*Please log in or create an account to continue.*")
    st.divider()

    tab_login, tab_register = st.tabs(["Log In", "Register"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log In", use_container_width=True)
        if submitted:
            if not username or not password:
                st.error("Please fill in all fields.")
            else:
                try:
                    r = requests.post(
                        f"{API}/auth/login",
                        data={"username": username, "password": password},
                        timeout=10,
                    )
                    if r.status_code == 200:
                        st.session_state.token = r.json()["access_token"]
                        st.session_state.username = username
                        st.rerun()
                    else:
                        st.error(_extract_error(r))
                except Exception as e:
                    st.error(f"Could not connect to server: {e}")

    with tab_register:
        with st.form("register_form"):
            new_username = st.text_input("Username (min 3 chars)")
            new_email = st.text_input("Email")
            new_password = st.text_input("Password (min 8 chars)", type="password")
            terms = st.checkbox(
                "I understand this app provides AI-assisted meal suggestions only "
                "and is not a substitute for professional dietary or medical advice."
            )
            submitted = st.form_submit_button("Create Account", use_container_width=True)
        if submitted:
            if not new_username or not new_email or not new_password:
                st.error("Please fill in all fields.")
            elif not terms:
                st.error("Please accept the terms to continue.")
            else:
                try:
                    r = requests.post(
                        f"{API}/auth/register",
                        json={"username": new_username, "email": new_email, "password": new_password},
                        timeout=10,
                    )
                    if r.status_code == 201:
                        st.success("Account created! Please log in.")
                    else:
                        st.error(_extract_error(r))
                except Exception as e:
                    st.error(f"Could not connect to server: {e}")


def render_tags(tags):
    return " ".join(f'<span class="tag">{t["tag"]}</span>' for t in tags)


def get_recipe_calories(recipe) -> float:
    return round((recipe["base_portion_grams"] / 100) * recipe["calories_per_100g"], 1)


# ─── Auth Gate ───────────────────────────────────────────────────────────────
if not st.session_state.token:
    show_auth_page()
    st.stop()


# ─── Sidebar Navigation ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🍽️ AI Meal Planner")
    st.markdown("*Multi-agent • RAG • Calorie-aware*")
    st.caption(f"👤 {st.session_state.username}")
    if st.button("Log Out", use_container_width=True):
        for key in ["token", "username", "family_id", "plan_id", "plan_data", "shopping_list"]:
            st.session_state[key] = None
        st.rerun()
    st.divider()

    page = st.radio(
        "Navigate",
        ["🏠 Setup Family", "🥦 Manage Fridge", "📅 Generate Plan", "🛒 Shopping List", "📆 Weekly Summary"],
        label_visibility="collapsed",
        key="nav_page",
    )

    st.divider()
    # Family selector
    families = api_get("/families/") or []
    if families:
        family_names = {f["name"]: f["id"] for f in families}
        selected_name = st.selectbox("Active Family", list(family_names.keys()))
        st.session_state.family_id = family_names[selected_name]
        st.caption(f"Family ID: {st.session_state.family_id}")
    else:
        st.info("No families yet — create one in Setup!")

    st.divider()
    st.markdown("**Agents:**")
    st.markdown("1️⃣ Preference Agent")
    st.markdown("2️⃣ Recipe Agent (MCP)")
    st.markdown("3️⃣ Planner Agent")
    st.markdown("4️⃣ Conversational Agent (GPT-4o)")
    st.divider()
    st.caption("⚠️ AI-assisted suggestions only. Not a substitute for professional dietary or medical advice.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1: Setup Family
# ═══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Setup Family":
    st.markdown("# 👨‍👩‍👧‍👦 Family Setup")
    st.markdown("Define your family members and their dietary needs.")

    ALLOWED_TAGS = ["vegetarian", "vegan", "gluten_free", "dairy_free", "no_red_meat",
                    "high_protein", "low_spice", "soft_food", "high_fiber", "toddler", "halal", "stol5"]
    FORBIDDEN_TAGS = ["vegetarian", "vegan", "no_red_meat", "gluten_free", "dairy_free"]
    PREFERRED_TAGS = [t for t in ALLOWED_TAGS if t != "stol5"]

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown('<div class="section-header"><h3>Create New Family</h3></div>', unsafe_allow_html=True)
        family_name = st.text_input("Family name", placeholder="e.g. The Johnsons")

        st.markdown("**Add Members**")
        if "members_draft" not in st.session_state:
            st.session_state.members_draft = []

        with st.expander("➕ Add a member", expanded=True):
            m_name = st.text_input("Name", key="m_name", placeholder="Alice")
            m_age = st.number_input("Age", 1, 100, 30, key="m_age")
            m_cal = st.number_input("Calorie target (kcal/day)", 800, 4000, 2000, step=100, key="m_cal")

            st.markdown("**Dietary tags** — check what applies:")
            st.info(
                "ℹ️ **stol5** activates a traditional local menu. "
                "It cannot be combined with other dietary preferences or restrictions — "
                "selecting it disables all other tag choices, and vice versa."
            )

            stol5_on = st.session_state.get("a_stol5", False)
            any_other_preferred = any(st.session_state.get(f"a_{t}", False) for t in PREFERRED_TAGS)
            any_forbidden_sel = any(st.session_state.get(f"f_{t}", False) for t in FORBIDDEN_TAGS)
            stol5_disabled = any_other_preferred or any_forbidden_sel

            col_a, col_b = st.columns(2)
            with col_a:
                st.caption("✅ Preferred")
                st.checkbox("stol5 (traditional menu)", key="a_stol5",
                            disabled=stol5_disabled, on_change=_on_stol5_checked)
                st.divider()
                for t in PREFERRED_TAGS:
                    st.checkbox(t, key=f"a_{t}", disabled=stol5_on,
                                on_change=_on_other_tag_checked)
            with col_b:
                st.caption("🚫 Forbidden")
                for t in FORBIDDEN_TAGS:
                    st.checkbox(t, key=f"f_{t}", disabled=stol5_on,
                                on_change=_on_other_tag_checked)

            if stol5_on:
                allowed_sel = ["stol5"]
                forbidden_sel = []
            else:
                allowed_sel = [t for t in ALLOWED_TAGS if st.session_state.get(f"a_{t}", False)]
                forbidden_sel = [t for t in FORBIDDEN_TAGS if st.session_state.get(f"f_{t}", False)]

            if st.button("Add Member", use_container_width=True):
                if m_name:
                    tags = [{"tag": t, "is_forbidden": False} for t in allowed_sel]
                    tags += [{"tag": t, "is_forbidden": True} for t in forbidden_sel]
                    st.session_state.members_draft.append({
                        "name": m_name, "age": m_age,
                        "calorie_target": m_cal, "diet_tags": tags,
                    })
                    st.success(f"Added {m_name}!")
                    st.rerun()

        # Show draft members
        if st.session_state.members_draft:
            st.markdown("**Members to add:**")
            for i, m in enumerate(st.session_state.members_draft):
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"👤 **{m['name']}** — {m['age']}y — {m['calorie_target']} kcal")
                with c2:
                    if st.button("✕", key=f"rm_{i}"):
                        st.session_state.members_draft.pop(i)
                        st.rerun()

        if st.button("🚀 Create Family", type="primary", use_container_width=True):
            if not family_name:
                st.error("Please enter a family name.")
            elif not st.session_state.members_draft:
                st.error("Add at least one member.")
            else:
                result = api_post("/families/", {
                    "name": family_name,
                    "members": st.session_state.members_draft,
                })
                if result:
                    st.success(f"✅ Family '{result['name']}' created with {len(result['members'])} members!")
                    st.session_state.family_id = result["id"]
                    st.session_state.members_draft = []
                    st.rerun()

    with col2:
        st.markdown('<div class="section-header"><h3>Existing Families</h3></div>', unsafe_allow_html=True)
        if not families:
            st.info("No families yet — create one on the left to get started.")
        for fam in (families or []):
            with st.expander(f"🏠 {fam['name']} ({len(fam['members'])} members)"):
                for member in fam["members"]:
                    mid = member["id"]
                    edit_key = f"editing_{mid}"

                    m_col1, m_col2 = st.columns([3, 1])
                    with m_col1:
                        st.markdown(f"**{member['name']}** — {member['age']}y — {member['calorie_target']} kcal/day")
                        forbidden = [t["tag"] for t in member["diet_tags"] if t["is_forbidden"]]
                        allowed = [t["tag"] for t in member["diet_tags"] if not t["is_forbidden"]]
                        if forbidden:
                            st.markdown(f"🚫 {', '.join(forbidden)}")
                        if allowed:
                            st.markdown(f"✅ {', '.join(allowed)}")
                    with m_col2:
                        if st.session_state.get(edit_key, False):
                            if st.button("✕ Cancel", key=f"cancel_{mid}"):
                                st.session_state[edit_key] = False
                                st.session_state.pop(f"edit_loaded_{mid}", None)
                                st.rerun()
                        else:
                            if st.button("✏️ Edit", key=f"btn_edit_{mid}"):
                                st.session_state[edit_key] = True
                                st.rerun()

                    if st.session_state.get(edit_key, False):
                        # Load current member data into session state on first open
                        if f"edit_loaded_{mid}" not in st.session_state:
                            st.session_state[f"edit_age_{mid}"] = member["age"]
                            st.session_state[f"edit_cal_{mid}"] = member["calorie_target"]
                            member_allowed = [t["tag"] for t in member["diet_tags"] if not t["is_forbidden"]]
                            if "stol5" in member_allowed:
                                st.session_state[f"edit_a_{mid}_stol5"] = True
                            else:
                                for tag_data in member["diet_tags"]:
                                    prefix = "f" if tag_data["is_forbidden"] else "a"
                                    st.session_state[f"edit_{prefix}_{mid}_{tag_data['tag']}"] = True
                            st.session_state[f"edit_loaded_{mid}"] = True

                        st.markdown(f"**Edit {member['name']}**")
                        st.number_input("Age", 1, 100, key=f"edit_age_{mid}")
                        st.number_input("Calorie target (kcal/day)", 800, 4000, step=100, key=f"edit_cal_{mid}")

                        stol5_on_e = st.session_state.get(f"edit_a_{mid}_stol5", False)
                        any_other_e = any(st.session_state.get(f"edit_a_{mid}_{t}", False) for t in PREFERRED_TAGS)
                        any_forbidden_e = any(st.session_state.get(f"edit_f_{mid}_{t}", False) for t in FORBIDDEN_TAGS)

                        ec1, ec2 = st.columns(2)
                        with ec1:
                            st.caption("✅ Preferred")
                            st.checkbox("stol5 (traditional menu)", key=f"edit_a_{mid}_stol5",
                                        disabled=any_other_e or any_forbidden_e,
                                        on_change=_on_edit_stol5_checked, args=(mid,))
                            st.divider()
                            for t in PREFERRED_TAGS:
                                st.checkbox(t, key=f"edit_a_{mid}_{t}", disabled=stol5_on_e,
                                            on_change=_on_edit_other_checked, args=(mid,))
                        with ec2:
                            st.caption("🚫 Forbidden")
                            for t in FORBIDDEN_TAGS:
                                st.checkbox(t, key=f"edit_f_{mid}_{t}", disabled=stol5_on_e,
                                            on_change=_on_edit_other_checked, args=(mid,))

                        if st.button("💾 Save Changes", key=f"save_{mid}", type="primary"):
                            if stol5_on_e:
                                edit_allowed = ["stol5"]
                                edit_forbidden = []
                            else:
                                edit_allowed = [t for t in ALLOWED_TAGS if st.session_state.get(f"edit_a_{mid}_{t}", False)]
                                edit_forbidden = [t for t in FORBIDDEN_TAGS if st.session_state.get(f"edit_f_{mid}_{t}", False)]

                            tags = [{"tag": t, "is_forbidden": False} for t in edit_allowed]
                            tags += [{"tag": t, "is_forbidden": True} for t in edit_forbidden]

                            result = api_put(f"/families/{fam['id']}/members/{mid}", {
                                "age": st.session_state[f"edit_age_{mid}"],
                                "calorie_target": st.session_state[f"edit_cal_{mid}"],
                                "diet_tags": tags,
                            })
                            if result:
                                st.success(f"✅ {member['name']}'s preferences saved!")
                                st.session_state[edit_key] = False
                                st.session_state.pop(f"edit_loaded_{mid}", None)
                                st.rerun()

                    st.divider()

                if st.button("🗑️ Delete Family", key=f"del_{fam['id']}"):
                    st.session_state[f"confirm_del_{fam['id']}"] = True
                if st.session_state.get(f"confirm_del_{fam['id']}"):
                    st.warning("Delete this family and all its data?")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Yes, delete", key=f"yes_del_{fam['id']}", type="primary"):
                            api_delete(f"/families/{fam['id']}")
                            st.session_state.pop(f"confirm_del_{fam['id']}", None)
                            st.rerun()
                    with c2:
                        if st.button("Cancel", key=f"no_del_{fam['id']}"):
                            st.session_state.pop(f"confirm_del_{fam['id']}", None)
                            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 2: Manage Fridge
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🥦 Manage Fridge":
    st.markdown("# 🥦 Fridge Manager")
    st.markdown("Add what's already available — those items won't appear on the shopping list.")

    if not st.session_state.family_id:
        st.warning("Please select or create a family first.")
        st.stop()

    fam_id = st.session_state.family_id

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown('<div class="section-header"><h3>Add Items</h3></div>', unsafe_allow_html=True)

        # Quick add presets
        COMMON = [
            "chicken", "rice", "eggs", "milk", "butter", "onion", "garlic",
            "carrot", "potato", "tomatoes", "olive_oil", "pasta", "cheese",
            "broccoli", "spinach", "bell_pepper", "lemon", "mushrooms",
            "salmon", "tuna", "yogurt", "oats", "banana", "avocado",
        ]
        st.markdown("**Quick add common items:**")
        selected_preset = st.multiselect("Select items", COMMON, label_visibility="collapsed")
        if st.button("Add Selected", use_container_width=True):
            if selected_preset:
                result = api_post(f"/fridge/{fam_id}/bulk", selected_preset)
                if result:
                    st.success(f"Added {result['count']} items!")
                    st.rerun()

        st.divider()
        custom = st.text_input("Or add custom item:", placeholder="e.g. coconut_milk")
        if st.button("Add Custom Item", use_container_width=True):
            if custom:
                api_post(f"/fridge/{fam_id}", {"ingredient": custom.lower().strip()})
                st.rerun()

        if st.button("🗑️ Clear Fridge", use_container_width=True):
            st.session_state["confirm_clear_fridge"] = True
        if st.session_state.get("confirm_clear_fridge"):
            st.warning("Remove all items from the fridge?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Yes, clear", key="yes_clear_fridge", type="primary"):
                    api_delete(f"/fridge/{fam_id}")
                    st.session_state.pop("confirm_clear_fridge", None)
                    st.rerun()
            with c2:
                if st.button("Cancel", key="no_clear_fridge"):
                    st.session_state.pop("confirm_clear_fridge", None)
                    st.rerun()

    with col2:
        st.markdown('<div class="section-header"><h3>Current Fridge Contents</h3></div>', unsafe_allow_html=True)
        items = api_get(f"/fridge/{fam_id}") or []
        if not items:
            st.info("Your fridge is empty! Add some ingredients.")
        else:
            st.markdown(f"**{len(items)} items in fridge:**")
            # Show as grid
            html = '<div style="margin-top:10px">'
            for item in items:
                html += f'<span class="fridge-item">🥬 {item["ingredient"]}</span>'
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)
            st.divider()
            st.markdown("**Remove items:**")
            for item in items:
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(item["ingredient"].replace("_", " ").title())
                with c2:
                    if st.button("✕", key=f"fi_{item['id']}"):
                        api_delete(f"/fridge/{fam_id}/{item['id']}")
                        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 3: Generate & Review Plan
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📅 Generate Plan":
    st.markdown("# 📅 Daily Meal Plan")

    if not st.session_state.family_id:
        st.warning("Please select or create a family first.")
        st.stop()

    fam_id = st.session_state.family_id
    family = api_get(f"/families/{fam_id}")

    col_gen, col_date = st.columns([2, 1])
    with col_date:
        plan_date = st.date_input("Plan date")
    with col_gen:
        if st.button("🤖 Generate Meal Plan", type="primary", use_container_width=True):
            with st.spinner("🧠 Agents working... Preference → Recipe (RAG) → Planner"):
                result = api_post("/meal-plans/generate", {
                    "family_id": fam_id,
                    "date": str(plan_date),
                })
                if result:
                    st.session_state.plan_data = result
                    st.session_state.plan_id = result["plan"]["id"]
                    st.session_state.shopping_list = None
                    st.session_state.chat_history = []
                    st.success("✅ Plan generated!")

    # ─── Display Plan ─────────────────────────────────────────────────────────
    if st.session_state.plan_data:
        plan_data = st.session_state.plan_data
        plan = plan_data["plan"]
        portions = plan_data.get("member_portions", [])

        # Approval badge
        if plan.get("approved"):
            st.markdown('<span class="approved-badge">✅ APPROVED</span>', unsafe_allow_html=True)

        st.divider()

        # Meal cards
        items_by_type = {item["meal_type"]: item for item in plan["items"]}
        MEAL_ICONS = {"breakfast": "🌅", "lunch": "☀️", "dinner": "🌙"}
        MEAL_LABELS = {"breakfast": "Breakfast (30% calories)", "lunch": "Lunch (40% calories)", "dinner": "Dinner (30% calories)"}

        # Fetch current user ratings once per plan (cached in session state)
        ratings_key = f"ratings_{plan['id']}"
        if ratings_key not in st.session_state:
            ratings_cache = {}
            for mt in ["breakfast", "lunch", "dinner"]:
                it = items_by_type.get(mt)
                if it:
                    rid = it["recipe"]["id"]
                    r = api_get(f"/recipes/{rid}/my-rating")
                    if r is not None:
                        ratings_cache[rid] = r.get("rating")
            st.session_state[ratings_key] = ratings_cache

        for meal_type in ["breakfast", "lunch", "dinner"]:
            item = items_by_type.get(meal_type)
            if not item:
                continue
            recipe = item["recipe"]
            cal = get_recipe_calories(recipe)
            portion = recipe["base_portion_grams"]
            protein = round((portion / 100) * recipe.get("protein_per_100g", 0), 1)
            fat     = round((portion / 100) * recipe.get("fat_per_100g", 0), 1)
            carbs   = round((portion / 100) * recipe.get("carbs_per_100g", 0), 1)
            tags_html = render_tags(recipe["tags"])
            ings = ", ".join(i["name"] for i in recipe["ingredients"][:5])
            source = recipe.get("source", "local")
            source_label = "📚 Local" if source == "local" else "🌐 Spoonacular"
            source_color = "#4ecca3" if source == "local" else "#f0a500"

            st.markdown(f"""
            <div class="meal-card">
                <h3>{MEAL_ICONS[meal_type]} {MEAL_LABELS[meal_type]}</h3>
                <div class="recipe-name">{recipe['name']}</div>
                <div class="meta">
                    📊 {cal:.1f} kcal/base portion &nbsp;|&nbsp;
                    ⚖️ {recipe['base_portion_grams']}g base &nbsp;|&nbsp;
                    🔥 {recipe['calories_per_100g']} kcal/100g
                </div>
                <div class="meta">🥩 {protein}g protein &nbsp;|&nbsp; 🧈 {fat}g fat &nbsp;|&nbsp; 🍞 {carbs}g carbs</div>
                <div class="meta">🧂 {ings}{'...' if len(recipe['ingredients']) > 5 else ''}</div>
                <div class="meta" style="margin-top:6px;">
                    <span style="color:{source_color}; font-size:0.8rem;">{source_label}</span>
                </div>
                <div style="margin-top:8px">{tags_html}</div>
            </div>
            """, unsafe_allow_html=True)

            # Cooking instructions
            if recipe.get("cooking_instructions"):
                with st.expander(f"👨‍🍳 Cooking Instructions"):
                    st.markdown(recipe["cooking_instructions"])

            # Rating buttons
            recipe_id = recipe["id"]
            current_rating = st.session_state.get(ratings_key, {}).get(recipe_id)
            r_col1, r_col2, _ = st.columns([1, 1, 6])
            with r_col1:
                liked = current_rating == 1
                if st.button("👍 Liked" if liked else "👍 Like",
                             key=f"like_{meal_type}", type="primary" if liked else "secondary"):
                    result = api_post(f"/recipes/{recipe_id}/rate", {"rating": None if liked else 1})
                    if result is not None:
                        cache = dict(st.session_state.get(ratings_key, {}))
                        cache[recipe_id] = None if liked else 1
                        st.session_state[ratings_key] = cache
                        st.rerun()
            with r_col2:
                disliked = current_rating == -1
                if st.button("👎 Disliked" if disliked else "👎 Dislike",
                             key=f"dislike_{meal_type}", type="primary" if disliked else "secondary"):
                    result = api_post(f"/recipes/{recipe_id}/rate", {"rating": None if disliked else -1})
                    if result is not None:
                        cache = dict(st.session_state.get(ratings_key, {}))
                        cache[recipe_id] = None if disliked else -1
                        st.session_state[ratings_key] = cache
                        st.rerun()


        st.divider()

        # ─── Member Portions Table ─────────────────────────────────────────────
        st.markdown('<div class="section-header"><h3>👤 Portions per Member</h3></div>', unsafe_allow_html=True)
        if portions:
            for p in portions:
                diff = p["total_calories"] - p["calorie_target"]
                cal_color  = "#4ecca3" if abs(diff) <= 100 else "#e94560"
                diff_label = f"+{diff:.0f}" if diff >= 0 else f"{diff:.0f}"
                st.markdown(f"""
                <div style="background:#0f3460; border-radius:12px; padding:16px; margin:10px 0;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                        <span style="font-size:1.1rem; font-weight:700; color:#ffffff;">👤 {p['member_name']}</span>
                        <span style="font-size:0.95rem; color:#cccccc;">
                            Target: <strong style="color:#ffffff;">{p['calorie_target']} kcal</strong>
                            &nbsp;|&nbsp;
                            Actual: <strong style="color:{cal_color};">{p['total_calories']:.0f} kcal</strong>
                            &nbsp;<span style="color:{cal_color};">({diff_label} kcal)</span>
                        </span>
                    </div>
                    <div style="display:flex; gap:12px; margin-bottom:10px;">
                        <div style="flex:1; background:#1a2a4a; border-radius:8px; padding:10px; text-align:center;">
                            <div style="color:#a0a0c0; font-size:0.72rem; letter-spacing:0.05em;">🌅 BREAKFAST</div>
                            <div style="color:#ffffff; font-size:1.2rem; font-weight:700; margin-top:4px;">{p['breakfast_grams']:.0f} g</div>
                        </div>
                        <div style="flex:1; background:#1a2a4a; border-radius:8px; padding:10px; text-align:center;">
                            <div style="color:#a0a0c0; font-size:0.72rem; letter-spacing:0.05em;">☀️ LUNCH</div>
                            <div style="color:#ffffff; font-size:1.2rem; font-weight:700; margin-top:4px;">{p['lunch_grams']:.0f} g</div>
                        </div>
                        <div style="flex:1; background:#1a2a4a; border-radius:8px; padding:10px; text-align:center;">
                            <div style="color:#a0a0c0; font-size:0.72rem; letter-spacing:0.05em;">🌙 DINNER</div>
                            <div style="color:#ffffff; font-size:1.2rem; font-weight:700; margin-top:4px;">{p['dinner_grams']:.0f} g</div>
                        </div>
                    </div>
                    <div style="display:flex; gap:12px;">
                        <div style="flex:1; background:#1a2a4a; border-radius:8px; padding:8px; text-align:center;">
                            <div style="color:#a0a0c0; font-size:0.7rem;">🥩 PROTEIN</div>
                            <div style="color:#4ecca3; font-size:1rem; font-weight:700;">{p.get('total_protein', 0):.1f} g</div>
                        </div>
                        <div style="flex:1; background:#1a2a4a; border-radius:8px; padding:8px; text-align:center;">
                            <div style="color:#a0a0c0; font-size:0.7rem;">🧈 FAT</div>
                            <div style="color:#f0a500; font-size:1rem; font-weight:700;">{p.get('total_fat', 0):.1f} g</div>
                        </div>
                        <div style="flex:1; background:#1a2a4a; border-radius:8px; padding:8px; text-align:center;">
                            <div style="color:#a0a0c0; font-size:0.7rem;">🍞 CARBS</div>
                            <div style="color:#e94560; font-size:1rem; font-weight:700;">{p.get('total_carbs', 0):.1f} g</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        # ─── AI Chat Assistant ─────────────────────────────────────────────────
        if not plan.get("approved"):
            st.markdown('<div class="section-header"><h3>💬 Ask the AI Assistant</h3></div>', unsafe_allow_html=True)
            st.caption("Ask to swap a meal, check ingredients, or get nutrition info. e.g. *\"Replace dinner with something lighter\"*")

            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []

            # Display chat history with rating buttons on assistant messages
            for idx, msg in enumerate(st.session_state.chat_history):
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    if msg["role"] == "assistant":
                        r1, r2, _ = st.columns([1, 1, 10])
                        with r1:
                            if st.button("👍", key=f"chat_up_{idx}", help="Helpful"):
                                api_post("/audit/rate-chat", {
                                    "rating": 1,
                                    "response_preview": msg["content"][:100],
                                })
                        with r2:
                            if st.button("👎", key=f"chat_down_{idx}", help="Not helpful"):
                                api_post("/audit/rate-chat", {
                                    "rating": -1,
                                    "response_preview": msg["content"][:100],
                                })

            user_input = st.chat_input("Ask about your meal plan...")
            if user_input:
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                with st.chat_message("user"):
                    st.markdown(user_input)

                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        chat_result = api_post(
                            f"/meal-plans/{plan['id']}/chat",
                            {
                                "message": user_input,
                                "history": st.session_state.chat_history[:-1],
                            },
                        )
                    if chat_result:
                        assistant_reply = chat_result["response"]
                        st.markdown(assistant_reply)
                        st.session_state.chat_history.append({"role": "assistant", "content": assistant_reply})

                        if chat_result.get("updated_plan"):
                            st.session_state.plan_data = chat_result["updated_plan"]
                            st.rerun()
                        else:
                            REPLACE_KEYWORDS = [
                                "replace", "swap", "change", "switch", "different",
                                "поменяй", "замени", "измени", "другой", "другое", "другую",
                                "смени", "перемени",
                            ]
                            msg_lower = user_input.lower()
                            if any(kw in msg_lower for kw in REPLACE_KEYWORDS):
                                st.warning(
                                    "⚠️ The meal plan was **not changed**. "
                                    "Try rephrasing, e.g. *\"Replace dinner with something with chicken\"*"
                                )

            if st.session_state.chat_history:
                if st.button("🗑️ Clear chat", key="clear_chat"):
                    st.session_state.chat_history = []
                    st.rerun()

        st.divider()

        # ─── Approve Button ────────────────────────────────────────────────────
        if not plan.get("approved"):
            col_app, col_del = st.columns(2)
            with col_app:
                if st.button("✅ Approve Plan & Get Shopping List", type="primary", use_container_width=True):
                    approved = api_post(f"/meal-plans/{plan['id']}/approve")
                    if approved:
                        st.session_state.plan_data["plan"]["approved"] = True
                        with st.spinner("Generating shopping list..."):
                            sl = api_post(f"/shopping/{plan['id']}/generate")
                            if sl:
                                st.session_state.shopping_list = sl
                        st.success("✅ Plan approved! Go to Shopping List tab.")
                        st.rerun()
            with col_del:
                if st.button("🗑️ Discard Plan", use_container_width=True):
                    st.session_state["confirm_discard_plan"] = True
            if st.session_state.get("confirm_discard_plan"):
                st.warning("Discard this plan? This cannot be undone.")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Yes, discard", key="yes_discard_plan", type="primary"):
                        api_delete(f"/meal-plans/{plan['id']}")
                        st.session_state.plan_data = None
                        st.session_state.plan_id = None
                        st.session_state.pop("confirm_discard_plan", None)
                        st.rerun()
                with c2:
                    if st.button("Cancel", key="no_discard_plan"):
                        st.session_state.pop("confirm_discard_plan", None)
                        st.rerun()
        else:
            if st.button("🔓 Reset & Edit Plan", use_container_width=True):
                result = api_post(f"/meal-plans/{plan['id']}/unapprove")
                if result:
                    st.session_state.plan_data["plan"]["approved"] = False
                    st.session_state.shopping_list = None
                    st.rerun()

    else:
        st.info("👆 Click **Generate Meal Plan** to start!")
        st.markdown("""
        **How it works:**
        1. **Preference Agent** reads all family members' dietary tags and merges constraints across the family
        2. **Recipe Agent (MCP)** queries the Recipe MCP Server — searches locally via FAISS vector search, falls back to Spoonacular online if nothing matches
        3. **Planner Agent** selects the best meal combination, scores by fridge overlap, and validates calories (±100 kcal)
        4. **Conversational Agent (GPT-4o)** lets you adjust the plan in natural language — use the chat below to swap meals, ask about ingredients, or check nutrition
        """)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 4: Shopping List
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🛒 Shopping List":
    st.markdown("# 🛒 Shopping List")

    if not st.session_state.plan_id:
        st.warning("Generate and approve a meal plan first.")
        st.stop()

    plan_id = st.session_state.plan_id

    # Try to load or generate
    sl = st.session_state.shopping_list
    if not sl:
        sl = api_get(f"/shopping/{plan_id}")
        if sl:
            st.session_state.shopping_list = sl

    if st.button("🔄 Regenerate Shopping List", use_container_width=False):
        sl = api_post(f"/shopping/{plan_id}/generate")
        if sl:
            st.session_state.shopping_list = sl
            st.rerun()

    if sl and sl.get("items"):
        items = sl["items"]

        # Load fridge contents for visual hint only (✅ = you may already have this)
        fridge_canonical = set()
        if st.session_state.family_id:
            fridge_data = api_get(f"/fridge/{st.session_state.family_id}") or []
            fridge_canonical = {
                "\x00".join(sorted(fi["ingredient"].lower().split()))
                for fi in fridge_data
            }

        in_fridge_count = sum(
            1 for item in items
            if "\x00".join(sorted(item["ingredient"].lower().split())) in fridge_canonical
        )

        st.markdown(f"**{len(items)} ingredients** for Meal Plan #{plan_id}")
        if in_fridge_count:
            st.caption(f"✅ {in_fridge_count} items may already be in your fridge — check before buying.")
        st.divider()

        # Group into columns
        col1, col2 = st.columns(2)
        for i, item in enumerate(sorted(items, key=lambda x: x["ingredient"])):
            col = col1 if i % 2 == 0 else col2
            with col:
                item_key = "\x00".join(sorted(item["ingredient"].lower().split()))
                in_fridge = item_key in fridge_canonical
                icon = "✅" if in_fridge else "🛒"
                name_style = "color:#4ecca3;" if in_fridge else ""
                st.markdown(f"""
                <div class="shopping-item">
                    <span style="{name_style}">{icon} <strong>{item['ingredient'].replace('_', ' ').title()}</strong></span>
                    <span style="color:#a0a0c0">{item['grams_needed']:.0f}g</span>
                </div>
                """, unsafe_allow_html=True)

        st.divider()
        total_items = len(items)
        total_grams = sum(i["grams_needed"] for i in items)
        st.markdown(f"**Total:** {total_items} ingredients · {total_grams:.0f}g estimated")
    elif sl:
        st.success("🎉 Nothing to buy — you have everything in the fridge!")
    else:
        st.info("Approve a meal plan to generate the shopping list.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 5: Weekly Summary
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📆 Weekly Summary":
    import pandas as pd
    from datetime import date as _date, timedelta

    st.markdown("# 📆 Weekly Summary")

    if not st.session_state.family_id:
        st.warning("Select a family first.")
        st.stop()

    fam_id = st.session_state.family_id
    family = api_get(f"/families/{fam_id}")
    if not family:
        st.error("Could not load family data.")
        st.stop()
    members = family.get("members", [])

    col_s, col_e = st.columns(2)
    with col_s:
        week_start = st.date_input("From", value=_date.today() - timedelta(days=6))
    with col_e:
        week_end = st.date_input("To", value=_date.today())

    if week_start > week_end:
        st.error("'From' date must be before 'To' date.")
        st.stop()

    all_plans = api_get(f"/meal-plans/family/{fam_id}") or []
    week_plans = {}
    for p in all_plans:
        if p["approved"] and week_start.isoformat() <= p["date"] <= week_end.isoformat():
            if p["date"] not in week_plans:
                week_plans[p["date"]] = p

    if not week_plans:
        st.info("No approved meal plans in this date range. Generate and approve plans on the Generate Plan page.")
        st.stop()

    sorted_dates = sorted(week_plans.keys())
    MEAL_ICONS   = {"breakfast": "🌅", "lunch": "☀️", "dinner": "🌙"}
    MEAL_SPLITS  = {"breakfast": 0.30, "lunch": 0.40, "dinner": 0.30}

    st.divider()

    # ─── Daily meal grid ──────────────────────────────────────────────────────
    st.markdown('<div class="section-header"><h3>📋 Daily Meals</h3></div>', unsafe_allow_html=True)

    for day in sorted_dates:
        plan = week_plans[day]
        items_by_type = {item["meal_type"]: item for item in plan["items"]}
        st.markdown(f"**{day}**")
        cols = st.columns(3)
        for col, meal_type in zip(cols, ["breakfast", "lunch", "dinner"]):
            with col:
                item = items_by_type.get(meal_type)
                if item:
                    r = item["recipe"]
                    cal = round((r["base_portion_grams"] / 100) * r["calories_per_100g"])
                    st.markdown(f"""
                    <div style="background:#16213e; border-radius:10px; padding:10px; min-height:80px;">
                        <div style="color:#e94560; font-size:0.75rem;">{MEAL_ICONS[meal_type]} {meal_type.upper()}</div>
                        <div style="color:#f5f5f5; font-size:0.9rem; font-weight:600; margin-top:4px;">{r['name']}</div>
                        <div style="color:#a0a0c0; font-size:0.75rem; margin-top:4px;">~{cal} kcal base</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="background:#16213e; border-radius:10px; padding:10px; min-height:80px; opacity:0.4;">
                        <div style="color:#e94560; font-size:0.75rem;">{MEAL_ICONS[meal_type]} {meal_type.upper()}</div>
                        <div style="color:#a0a0c0; font-size:0.85rem; margin-top:8px;">—</div>
                    </div>
                    """, unsafe_allow_html=True)
        st.markdown("")

    st.divider()

    # ─── Per-member nutrition summary ─────────────────────────────────────────
    st.markdown('<div class="section-header"><h3>👤 Nutrition per Member</h3></div>', unsafe_allow_html=True)
    st.caption("Portions are adjusted to each member's calorie target using the same engine as plan generation.")

    for member in members:
        member_name = member["name"]
        cal_target  = member["calorie_target"]

        rows = []
        for day in sorted_dates:
            plan = week_plans[day]
            items_by_type = {item["meal_type"]: item for item in plan["items"]}

            day_cal = day_protein = day_fat = day_carbs = 0.0
            for meal_type, split in MEAL_SPLITS.items():
                item = items_by_type.get(meal_type)
                if not item:
                    continue
                r = item["recipe"]
                base_g       = r["base_portion_grams"]
                cal_per_100g = r["calories_per_100g"]
                cal_per_base = (base_g / 100) * cal_per_100g
                coef  = (cal_target * split) / cal_per_base if cal_per_base > 0 else 1.0
                adj_g = base_g * coef

                day_cal     += (adj_g / 100) * cal_per_100g
                day_protein += (adj_g / 100) * r.get("protein_per_100g", 0)
                day_fat     += (adj_g / 100) * r.get("fat_per_100g", 0)
                day_carbs   += (adj_g / 100) * r.get("carbs_per_100g", 0)

            rows.append({
                "Date":        day,
                "Calories":    round(day_cal),
                "Protein (g)": round(day_protein, 1),
                "Fat (g)":     round(day_fat, 1),
                "Carbs (g)":   round(day_carbs, 1),
            })

        df = pd.DataFrame(rows).set_index("Date")

        st.markdown(f"#### 👤 {member_name} — {cal_target} kcal/day target")

        macro_chart = df[["Protein (g)", "Fat (g)", "Carbs (g)"]].copy()
        st.bar_chart(macro_chart, height=220, color=["#4ecca3", "#f0a500", "#e94560"])

        st.markdown("")
