import streamlit as st
import sqlite3
import uuid
import datetime
import os
import google.generativeai as genai

# ----------------- SAYFA AYARLARI -----------------
st.set_page_config(
    page_title="Yoldaş - Kişisel Rehber",
    page_icon="🤝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- ÖZEL CSS (KOYU TEMA & MOBİL GİRİŞ DÜZELTMESİ) -----------------
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0b0e14 0%, #161b22 100%);
        color: #e6edf3;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    section[data-testid="stSidebar"] {
        background-color: rgba(13, 17, 23, 0.95) !important;
        backdrop-filter: blur(15px);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
    
    /* YAZI GİRİŞ KUTUSU MOBİL VE OKUNURLUK DÜZELTMESİ */
    [data-testid="stChatInput"] {
        background-color: #161b22 !important;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        border-radius: 12px !important;
    }
    [data-testid="stChatInput"] textarea {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        caret-color: #ffffff !important;
        background-color: transparent !important;
        font-size: 16px !important;
    }
    [data-testid="stChatInput"] textarea::placeholder {
        color: rgba(255, 255, 255, 0.6) !important;
        -webkit-text-fill-color: rgba(255, 255, 255, 0.6) !important;
    }
    [data-testid="stChatInput"] button {
        color: #ffffff !important;
    }
    .stButton>button { border-radius: 8px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ----------------- GEMINI API BAĞLANTISI -----------------
def get_api_key():
    if "GEMINI_API_KEY" in st.secrets:
        return str(st.secrets["GEMINI_API_KEY"]).strip().strip("'").strip('"')
    elif "gemini_api_key" in st.secrets:
        return str(st.secrets["gemini_api_key"]).strip().strip("'").strip('"')
    elif os.environ.get("GEMINI_API_KEY"):
        return os.environ.get("GEMINI_API_KEY").strip().strip("'").strip('"')
    return None

api_key = get_api_key()
if api_key:
    genai.configure(api_key=api_key)

# ----------------- VERİTABANI YÖNETİMİ -----------------
DB_FILE = "yoldas_veritabani.db"

def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            nick_name TEXT,
            real_name TEXT,
            age_group TEXT,
            hitap TEXT,
            companion_name TEXT,
            companion_stance TEXT,
            daily_goal TEXT,
            reward TEXT,
            namaz_tracking INTEGER,
            namaz_streak INTEGER,
            target_language TEXT,
            language_level TEXT,
            discovered_interests TEXT,
            admin_guidance TEXT,
            created_at TIMESTAMP
        )
    ''')
    existing_cols = [col[1] for col in c.execute("PRAGMA table_info(users)").fetchall()]
    needed_cols = {
        "nick_name": "TEXT", "real_name": "TEXT", "age_group": "TEXT", "hitap": "TEXT",
        "companion_name": "TEXT", "companion_stance": "TEXT", "daily_goal": "TEXT",
        "reward": "TEXT", "namaz_tracking": "INTEGER", "namaz_streak": "INTEGER",
        "target_language": "TEXT", "language_level": "TEXT", "discovered_interests": "TEXT",
        "admin_guidance": "TEXT", "created_at": "TIMESTAMP"
    }
    for col_name, col_type in needed_cols.items():
        if col_name not in existing_cols:
            try:
                c.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass

    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            chat_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_user(user_id):
    if not user_id:
        return None
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def save_user(u):
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO users (
            id, nick_name, real_name, age_group, hitap, companion_name, companion_stance,
            daily_goal, reward, namaz_tracking, namaz_streak, target_language, language_level,
            discovered_interests, admin_guidance, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        u['id'], u.get('nick_name', ''), u.get('real_name', ''), u.get('age_group', ''), u.get('hitap', ''),
        u.get('companion_name', ''), u.get('companion_stance', ''), u.get('daily_goal', ''), u.get('reward', ''),
        u.get('namaz_tracking', 0), u.get('namaz_streak', 0), u.get('target_language', ''), u.get('language_level', ''),
        u.get('discovered_interests', ''), u.get('admin_guidance', ''), u.get('created_at', datetime.datetime.now().isoformat())
    ))
    conn.commit()
    conn.close()

def get_messages(user_id, chat_id="default"):
    if not user_id:
        return []
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages WHERE user_id = ? AND chat_id = ? ORDER BY id ASC", (user_id, chat_id))
    rows = c.fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in rows]

def save_message(user_id, chat_id, role, content):
    if not user_id or not content:
        return
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT INTO messages (user_id, chat_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)",
              (user_id, chat_id, role, content, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ----------------- KULLANICI AYRIŞTIRMA (İZOLASYON) -----------------
params = st.query_params
if "u" not in params:
    new_uid = str(uuid.uuid4())[:8]
    st.query_params["u"] = new_uid
    current_user_id = new_uid
else:
    current_user_id = params["u"]

current_user = get_user(current_user_id)

# ----------------- YÖNETİCİ PANELİ (SOL MENÜ) -----------------
with st.sidebar:
    st.markdown("### 🤝 Yoldaş Menüsü")
    admin_expander = st.expander("⚙️ Ebeveyn / Yönetici Girişi", expanded=False)
    with admin_expander:
        pin = st.text_input("Giriş PIN Kodu", type="password", key="admin_pin")
        if pin == "1453":
            st.success("Yönetici Yetkisi Doğrulandı")
            all_users = get_all_users()
            user_options = {u.get('nick_name', 'İsimsiz') + f" ({u['id']})": u['id'] for u in all_users}
            if user_options:
                selected_user_label = st.selectbox("İncelenecek Kullanıcı", list(user_options.keys()))
                sel_id = user_options[selected_user_label]
                sel_u = get_user(sel_id)

                st.markdown(f"**Gerçek Adı:** {sel_u.get('real_name', 'Bilinmiyor')}")
                st.markdown(f"**İlgi Alanları:** {sel_u.get('discovered_interests', '-')}")
                st.markdown(f"**Hedef Dil:** {sel_u.get('target_language', '-')}")

                new_guidance = st.text_area("Yoldaş'a Gizli Yönlendirme", sel_u.get('admin_guidance', ''))
                if st.button("Talimatı Kaydet"):
                    sel_u['admin_guidance'] = new_guidance
                    save_user(sel_u)
                    st.toast("Yönlendirme güncellendi!")

                st.markdown("---")
                st.markdown("#### Sohbet Geçmişi")
                admin_msgs = get_messages(sel_id, "default")
                for m in admin_msgs:
                    st.caption(f"**{m['role'].upper()}:** {m['content']}")
            else:
                st.info("Kayıtlı kullanıcı bulunamadı.")
        elif pin:
            st.error("Hatalı PIN Kodu.")

    if current_user:
        st.markdown("---")
        st.markdown(f"**👤 Kullanıcı:** {current_user.get('nick_name')}")
        st.markdown(f"**🎯 Hedef Dil:** {current_user.get('target_language', 'Belirtilmedi')}")
        if current_user.get('namaz_tracking'):
            st.markdown(f"**🕌 Namaz Serisi:** {current_user.get('namaz_streak', 0)} Gün 🔥")
        if st.button("Çıkış Yap / Yeni Profil"):
            st.query_params.clear()
            st.rerun()

# ----------------- ANA EKRAN -----------------
if not current_user:
    st.markdown("## 🤝 Yoldaş'a Hoş Geldin")
    st.caption("Kendine samimi bir yol arkadaşı seç, birlikte hedeflere yürüyün.")

    with st.form("onboarding_form"):
        col1, col2 = st.columns(2)
        with col1:
            nick = st.text_input("Sana nasıl hitap edelim?", placeholder="Örn: Yiğit")
            hitap = st.selectbox("Sohbet tonu nasıl olsun?", ["Dostum / Kardeşim", "Hocam", "Kıymetli Arkadaşım", "Samimi & Doğal"])
            interests = st.text_input("Zihnini ne meşgul ediyor? / İlgi Alanların", placeholder="Örn: Kodlama, Kitap, Spor, Gelecek Planları")
        with col2:
            companion = st.text_input("Yol arkadaşının adı ne olsun?", value="Bilge")
            stance = st.radio("Duruş beklentin:", ["Şefkatli bir dinleyici", "Kararlı bir koç", "Bilge bir yoldaş"])

        col3, col4 = st.columns(2)
        with col3:
            daily_goal = st.text_input("Günün odak hedefi nedir?", placeholder="Örn: 20 sayfa kitap okumak")
        with col4:
            target_lang = st.selectbox("Geliştirmek istediğin dil var mı?", ["Yok", "İngilizce", "Arapça", "Almanca"])

        submitted = st.form_submit_button("Yola Çıkalım 🚀", use_container_width=True)

        if submitted:
            if not nick:
                st.warning("Lütfen sana nasıl hitap edeceğimizi belirt.")
            else:
                new_u = {
                    "id": current_user_id,
                    "nick_name": nick,
                    "real_name": "Henüz Tespit Edilmedi",
                    "age_group": "Genç",
                    "hitap": hitap,
                    "companion_name": companion if companion else "Yoldaş",
                    "companion_stance": stance,
                    "daily_goal": daily_goal if daily_goal else "Günü verimli geçirmek",
                    "reward": "Huzurlu bir zihin",
                    "namaz_tracking": 0,
                    "namaz_streak": 0,
                    "target_language": target_lang,
                    "language_level": "Orta",
                    "discovered_interests": interests if interests else "Keşfediliyor",
                    "admin_guidance": "",
                    "created_at": datetime.datetime.now().isoformat()
                }
                save_user(new_u)
                welcome_msg = f"Selam {nick}! Ben {new_u['companion_name']}. Yol arkadaşın olarak buradayım. Bugün aklında ne var, nereden başlamak istersin?"
                save_message(current_user_id, "default", "assistant", welcome_msg)
                st.rerun()

else:
    comp_name = current_user.get('companion_name', 'Yoldaş')
    user_nick = current_user.get('nick_name', 'Dostum')
    
    st.markdown(f"### 🤝 {comp_name} ile Yolculuk")
    st.caption(f"Yol arkadaşın seni dinliyor, {user_nick}.")

    messages = get_messages(current_user_id, "default")
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("İçini dök veya bir soru sor..."):
        save_message(current_user_id, "default", "user", prompt)
        with st.chat_message("user"):
            st.markdown(prompt)

        sys_prompt = f"""
        Sen 'Yoldaş' platformundaki kişisel rehbersin. Adın: {comp_name}.
        Kullanıcı: {user_nick}, Hitap Şekli: {current_user.get('hitap', 'Dostum')}.
        Duruşun: {current_user.get('companion_stance', 'Şefkatli bir dinleyici')}.
        Günün Odak Hedefi: {current_user.get('daily_goal')}.
        Hedef Dil: {current_user.get('target_language')}.
        Gizli Yönetici Yönlendirmesi: {current_user.get('admin_guidance', 'Yok')}.

        KURALLAR:
        1. Robotik ve kalıp cümleler kurma. Mert, içten, samimi ve doğal bir Türkçe ile konuş.
        2. Kullanıcının az önce yazdığı mesaja odaklan ve doğrudan onu cevapla.
        3. Yanıtların çok uzun olmasın (1-2 paragraf), akıcı sohbet havasında kal.
        """

        gecmis_diyalog = ""
        for m in get_messages(current_user_id, "default"):
            kim = "Kullanıcı" if m["role"] == "user" else comp_name
            gecmis_diyalog += f"{kim}: {m['content']}\n"

        with st.chat_message("assistant"):
            if not api_key:
                err_msg = "⚠️ API Anahtarı eksik! Lütfen Streamlit Secrets alanına GEMINI_API_KEY ekleyin."
                st.error(err_msg)
                save_message(current_user_id, "default", "assistant", err_msg)
            else:
                bot_reply = None
                last_err = None

                target_models = [
                    "models/gemini-3.8-flash",
                    "gemini-3.8-flash",
                    "models/gemini-2.0-flash",
                    "models/gemini-1.5-flash"
                ]

                for mod_name in target_models:
                    try:
                        model = genai.GenerativeModel(
                            model_name=mod_name,
                            system_instruction=sys_prompt
                        )
                        response = model.generate_content(f"{gecmis_diyalog}\n{comp_name}:")
                        if response and response.text:
                            bot_reply = response.text
                            break
                    except Exception as e:
                        last_err = e
                        continue

                if bot_reply:
                    st.markdown(bot_reply)
                    save_message(current_user_id, "default", "assistant", bot_reply)
                else:
                    err_msg = f"Dostum seni dinliyorum, mesajını tam alamadım. Tekrar söyler misin? ({last_err})"
                    st.markdown(err_msg)
                    save_message(current_user_id, "default", "assistant", err_msg)
