import streamlit as st
import sqlite3
import json
import time
import uuid
from datetime import datetime, date
from google import genai
from google.genai import types

st.set_page_config(page_title="Yoldaş", page_icon="🤝", layout="wide")

st.markdown("""
</* YAZI GİRİŞ ALANI (CHAT INPUT) MOBİL & KOYU TEMA DÜZELTMESİ */
    [data-testid="stChatInput"] {
        background-color: #161b22 !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 12px !important;
    }
    [data-testid="stChatInput"] textarea {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        caret-color: #ffffff !important;
        font-size: 16px !important;
    }
    [data-testid="stChatInput"] textarea::placeholder {
        color: rgba(255, 255, 255, 0.6) !important;
        -webkit-text-fill-color: rgba(255, 255, 255, 0.6) !important;
    }>
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
    .badge-pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        margin-bottom: 8px;
    }
    .badge-namaz { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
    .badge-dil { background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4); }
    .badge-streak { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
    .stButton>button { border-radius: 8px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

DB_NAME = "yoldas_veritabani.db"

# ----------------- 1. VERİTABANI İŞLEMLERİ -----------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_token TEXT UNIQUE,
        nickname TEXT,
        real_name TEXT DEFAULT 'Henüz Tespit Edilmedi',
        hitap TEXT,
        focus TEXT,
        companion TEXT DEFAULT 'Yusuf',
        tone TEXT,
        streak INTEGER DEFAULT 1,
        last_active_date TEXT,
        daily_goal TEXT DEFAULT 'Bugün için bir hedef belirle.',
        goal_completed INTEGER DEFAULT 0,
        reward TEXT DEFAULT '1 Saat Mola / Birlikte Vakit',
        admin_guidance TEXT DEFAULT 'Disiplin ve karakter gelişimi',
        age_group TEXT DEFAULT '13-18 Yaş (Genç)',
        namaz_tracking INTEGER DEFAULT 0,
        target_language TEXT DEFAULT 'Yok',
        namaz_count INTEGER DEFAULT 0,
        discovered_interests TEXT DEFAULT 'Henüz keşfediliyor',
        safety_alert INTEGER DEFAULT 0,
        current_chat_id INTEGER DEFAULT 1,
        created_at TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        chat_id INTEGER DEFAULT 1,
        role TEXT,
        content TEXT,
        timestamp TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        stress_level INTEGER,
        motivation TEXT,
        mood TEXT,
        detected_themes TEXT,
        summary TEXT,
        safety_flag INTEGER DEFAULT 0,
        timestamp TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)
    conn.commit()
    conn.close()

init_db()

# ----------------- 2. GEMINI API ENTEGRASYONU (503 DİRENÇLİ) -----------------
GEMINI_API_KEY = "AQ.Ab8RN6LgeT-1IN9IXcSS9b-AqV-WyVHIcNsga-kUhFsXWUs16w"
client = genai.Client(api_key=GEMINI_API_KEY)
MODELS_TO_TRY = ["gemini-3.8-flash", "gemini-2.5-flash"]

def get_streaming_response(contents, system_instruction):
    """503 durumunda sırayla alternatif modellere düşer ve canlı yayın yapar."""
    last_err = None
    for model_name in MODELS_TO_TRY:
        try:
            return client.models.generate_content_stream(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7
                )
            )
        except Exception as e:
            last_err = e
            time.sleep(0.5)
            continue
    raise last_err

def quick_generate(contents):
    for model_name in MODELS_TO_TRY:
        try:
            res = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(temperature=0.2)
            )
            if res and res.text:
                return res.text
        except Exception:
            continue
    return None

# ----------------- 3. VERİTABANI YARDIMCILARI -----------------
def create_new_user(session_token, nickname, hitap, focus, companion, tone):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today_str = str(date.today())
    cursor.execute("""
    INSERT INTO users (session_token, nickname, real_name, hitap, focus, companion, tone, streak, last_active_date, daily_goal, goal_completed, reward, admin_guidance, age_group, namaz_tracking, target_language, namaz_count, discovered_interests, safety_alert, current_chat_id, created_at)
    VALUES (?, ?, 'Henüz Tespit Edilmedi', ?, ?, ?, ?, 1, ?, 'Bugün kendine mertçe bir hedef koy.', 0, 'Sohbetten belirlenecek', 'Doğal karakter gelişimi', '13-18 Yaş (Genç)', 0, 'Yok', 0, 'Henüz keşfediliyor', 0, 1, ?)
    """, (session_token, nickname, hitap, focus, companion, tone, today_str, now_str))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id

def get_user_by_session(session_token):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE session_token = ?", (session_token,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, nickname, real_name, age_group FROM users ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user_by_id(user_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_user_field(user_id, field, value):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {field} = ? WHERE id = ?", (value, user_id))
    conn.commit()
    conn.close()

def save_message(user_id, chat_id, role, content):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO messages (user_id, chat_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)", (user_id, chat_id, role, content, now))
    conn.commit()
    conn.close()

def get_messages(user_id, chat_id=None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if chat_id is not None:
        cursor.execute("SELECT role, content, chat_id, timestamp FROM messages WHERE user_id = ? AND chat_id = ? ORDER BY id ASC", (user_id, chat_id))
    else:
        cursor.execute("SELECT role, content, chat_id, timestamp FROM messages WHERE user_id = ? ORDER BY id ASC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1], "chat_id": r[2], "timestamp": r[3]} for r in rows]

def save_analysis(user_id, stress_level, motivation, mood, themes, summary, safety_flag):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO analysis (user_id, stress_level, motivation, mood, detected_themes, summary, safety_flag, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, stress_level, motivation, mood, themes, summary, safety_flag, now))
    conn.commit()
    conn.close()

def get_user_analysis(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT stress_level, motivation, mood, detected_themes, summary, safety_flag, timestamp FROM analysis WHERE user_id = ? ORDER BY id DESC LIMIT 15", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

# ----------------- 4. ARKA PLAN ANALİZİ -----------------
def analyze_and_evolve_user(user_id, message_text, current_real_name, current_interests, current_lang, current_namaz):
    prompt = f"""
    Kullanıcı mesajını analiz et ve SADECE JSON verisi üret:
    {{
      "stress_level": 1-10 tam sayı,
      "motivation": "Düşük", "Orta" veya "Yüksek",
      "mood": "Ruh hali tek kelime",
      "safety_flag": 0 veya 1 (intihar, kendine zarar, madde, şiddet riski varsa 1),
      "extracted_real_name": "Mesajda adını söylediyse yaz, yoksa null",
      "discovered_interests": "Yeni bahsedilen hobiler (marvel, satranç vb.)",
      "detected_language_interest": "İlgilendiği yabancı dil (yoksa null)",
      "talks_about_prayer": "Namaz/ibadet bahsetti mi (true/false)",
      "summary": "Kısa özet"
    }}
    Mevcut Durum: Gerçek Ad: "{current_real_name}", Hobiler: "{current_interests}"
    Mesaj: "{message_text}"
    """
    try:
        raw_text = quick_generate(prompt)
        if not raw_text:
            return
        clean = raw_text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean)
        
        save_analysis(
            user_id,
            int(data.get("stress_level", 5)),
            str(data.get("motivation", "Orta")),
            str(data.get("mood", "Nötr")),
            str(data.get("discovered_interests", "")),
            str(data.get("summary", "")),
            int(data.get("safety_flag", 0))
        )
        
        ex_name = data.get("extracted_real_name")
        if ex_name and ex_name != "null" and current_real_name == "Henüz Tespit Edilmedi":
            update_user_field(user_id, "real_name", ex_name)

        new_int = data.get("discovered_interests")
        if new_int and len(new_int) > 2:
            combined = new_int if current_interests == "Henüz keşfediliyor" else f"{current_interests}, {new_int}"
            update_user_field(user_id, "discovered_interests", combined)

        det_lang = data.get("detected_language_interest")
        if det_lang and det_lang != "null" and current_lang == "Yok":
            update_user_field(user_id, "target_language", det_lang)

        if data.get("talks_about_prayer") and not current_namaz:
            update_user_field(user_id, "namaz_tracking", 1)
    except Exception:
        pass

# ----------------- 5. KALICI KİMLİK -----------------
qp = st.query_params
if "u" in qp and qp["u"]:
    session_token = qp["u"]
else:
    if "session_token" not in st.session_state:
        st.session_state.session_token = str(uuid.uuid4())[:8]
    session_token = st.session_state.session_token
    st.query_params["u"] = session_token

# ----------------- 6. YAN PANEL & GİZLİ YÖNETİCİ GİRİŞİ -----------------
with st.sidebar:
    st.markdown("### 🤝 Yoldaş")
    with st.expander("⚙️ Ebeveyn / Yönetici Girişi"):
        pin_code = st.text_input("Yönetici PIN:", type="password", placeholder="PIN")
        admin_auth = (pin_code == "1453")
        if admin_auth:
            st.success("Yönetici Modu Açık 🛡️")

# ----------------- GÖRÜNÜM: YÖNETİCİ EKRANI -----------------
if admin_auth:
    st.title("🛡️ Ebeveyn & Yönetici Pedagoji Merkezi")
    all_users = get_all_users()
    
    if not all_users:
        st.info("Henüz bağlanan kullanıcı yok.")
    else:
        user_options = {u["id"]: f"#{u['id']} - {u['nickname']} (Gerçek Ad: {u['real_name']})" for u in all_users}
        selected_user_id = st.selectbox("Gözlemlenecek Kullanıcı:", options=list(user_options.keys()), format_func=lambda x: user_options[x])
        u_profile = get_user_by_id(selected_user_id)
        
        tab_baba_koc, tab_yonetim, tab_rapor, tab_kayit = st.tabs([
            "💡 Yapay Zeka Ebeveyn Stratejisi", "🎯 Görev & Kurallar", "📊 İlgi Alanları & Zihin Analizi", "📜 Sohbet Geçmişi"
        ])
        
        with tab_baba_koc:
            st.markdown("### 👨‍👦 Pedagojik Baba / Ebeveyn Masası")
            ebeveyn_derdini = st.text_area("Hedefin veya Yaşadığın Sorun:", placeholder="Örn: Çocuğumla aramda mesafe var...")
            if st.button("🚀 Özel Strateji Üret"):
                if ebeveyn_derdini.strip():
                    with st.spinner("Plan hazırlanıyor..."):
                        tavsiye_prompt = f"""
                        Sen bilge bir pedagog ve Türk aile yapısını iyi bilen bir ebeveyn koçusun.
                        Ebeveyn talebi: "{ebeveyn_derdini}"
                        Profil: Yaş: {u_profile.get('age_group')}, Hobiler: {u_profile.get('discovered_interests')}
                        Babaya 3 maddelik pratik strateji yaz:
                        1. Mert ve samimi konuşma taktiği.
                        2. Ekrandan uzak baba-çocuk etkinliği.
                        3. Yoldaş botuna gizli talimat taslağı.
                        """
                        res_text = quick_generate(tavsiye_prompt)
                        st.markdown(res_text or "Strateji üretilemedi, lütfen tekrar deneyin.")

        with tab_yonetim:
            with st.form("admin_form"):
                col1, col2 = st.columns(2)
                with col1:
                    age_list = ["7-12 Yaş (Çocuk)", "13-18 Yaş (Genç)", "19+ Yaş (Yetişkin)"]
                    c_age = u_profile.get('age_group', '13-18 Yaş (Genç)')
                    idx = age_list.index(c_age) if c_age in age_list else 1
                    a_age = st.selectbox("Yaş Grubu:", age_list, index=idx)
                    a_namaz = st.checkbox("🕌 Namaz Takibi Aktif", value=bool(u_profile.get('namaz_tracking', 0)))
                    a_dil = st.selectbox("Hedef Dil:", ["Yok", "İngilizce", "Arapça", "Almanca"], index=0)
                with col2:
                    a_target = st.text_input("Gizli Yönlendirme:", value=u_profile.get('admin_guidance', ''))
                    a_task = st.text_input("Günün Görevi:", value=u_profile.get('daily_goal', ''))
                    a_reward = st.text_input("Ekrandan Uzak Ödül:", value=u_profile.get('reward', ''))
                
                if st.form_submit_button("Kaydet 💾"):
                    conn = sqlite3.connect(DB_NAME)
                    cur = conn.cursor()
                    cur.execute("""
                    UPDATE users SET age_group=?, namaz_tracking=?, target_language=?, admin_guidance=?, daily_goal=?, reward=? WHERE id=?
                    """, (a_age, int(a_namaz), a_dil, a_target, a_task, a_reward, selected_user_id))
                    conn.commit()
                    conn.close()
                    st.success("Güncellendi!")
                    st.rerun()

        with tab_rapor:
            st.markdown(f"**🔍 Tespit Edilen Gerçek İsim:** `{u_profile.get('real_name')}`")
            st.markdown(f"**🎯 Hobileri:** `{u_profile.get('discovered_interests')}`")
            st.markdown(f"**🌐 Merak Ettiği Dil:** `{u_profile.get('target_language')}`")
            analyses = get_user_analysis(selected_user_id)
            if analyses:
                latest = analyses[0]
                m1, m2, m3 = st.columns(3)
                m1.metric("Stres Seviyesi", f"{latest[0]}/10")
                m2.metric("Motivasyon", latest[1])
                m3.metric("Ruh Hali", latest[2])
                st.info(f"**Zihin Özeti:** {latest[4]}")
                st.line_chart([r[0] for r in reversed(analyses)])

        with tab_kayit:
            all_m = get_messages(selected_user_id)
            for m in all_m:
                who = u_profile.get('nickname') if m['role'] == 'user' else u_profile.get('companion')
                st.markdown(f"**[Sohbet #{m['chat_id']} | {m['timestamp']}] {who}:** {m['content']}")

# ----------------- GÖRÜNÜM: KULLANICI EKRANI -----------------
else:
    u_dict = get_user_by_session(session_token)
    
    if not u_dict:
        st.title("🤝 Yoldaş'a Hoş Geldin")
        with st.form("onboarding_form"):
            u_name = st.text_input("Sana nasıl hitap edelim?", placeholder="Örn: Yiğit")
            u_hitap = st.selectbox("Sohbet tonu nasıl olsun?", ["Dostum / Kardeşim", "Hocam / Reis", "Sadece ismimle"])
            u_focus = st.multiselect("Zihnini ne meşgul ediyor?", ["🧠 Kişisel Gelişim", "💼 Hedefler", "🎯 Spor", "💬 Dertleşmek"], default=["🧠 Kişisel Gelişim"])
            u_companion = st.text_input("Yol arkadaşının adı:", value="Yusuf")
            u_tone = st.radio("Duruş beklentin:", ["☕ Şefkatli bir dinleyici", "⚡ Kararlı bir koç", "📜 Bilge bir yoldaş"])
            
            if st.form_submit_button("Yola Çıkalım 🚀"):
                if u_name.strip():
                    new_uid = create_new_user(session_token, u_name.strip(), u_hitap, ", ".join(u_focus), u_companion.strip() or "Yusuf", u_tone)
                    ilk_mesaj = f"Selam {u_name}! Ben {u_companion}. Seninle tanıştığıma sevindim. Seni buraya getiren ne, bugün aklından neler geçiyor?"
                    save_message(new_uid, 1, "assistant", ilk_mesaj)
                    st.rerun()
    else:
        current_chat = u_dict.get('current_chat_id', 1)
        
        with st.sidebar:
            if st.button("➕ Yeni Sohbet Başlat", use_container_width=True):
                new_chat_num = current_chat + 1
                update_user_field(u_dict['id'], "current_chat_id", new_chat_num)
                u_dict['current_chat_id'] = new_chat_num
                taze_mesaj = f"Yeni bir sayfa açtık {u_dict.get('nickname')}! Bugün nereden başlamak istersin?"
                save_message(u_dict['id'], new_chat_num, "assistant", taze_mesaj)
                st.rerun()

            st.markdown('<span class="badge-pill badge-streak">🔥 Günlük Seri</span>', unsafe_allow_html=True)
            st.metric(label="Aktif Gün", value=f"{u_dict.get('streak', 1)} Gün")
            
            if u_dict.get('namaz_tracking', 0):
                st.markdown('<span class="badge-pill badge-namaz">🕌 Namaz Takibi</span>', unsafe_allow_html=True)
                n_count = u_dict.get('namaz_count', 0)
                st.caption(f"Bugün eda edilen: **{n_count}/5 Vakit**")
                col_n1, col_n2 = st.columns(2)
                with col_n1:
                    if st.button("➕ Kıldım"):
                        if n_count < 5:
                            update_user_field(u_dict['id'], "namaz_count", n_count + 1)
                            st.balloons()
                            st.rerun()
                with col_n2:
                    if st.button("Sıfırla"):
                        update_user_field(u_dict['id'], "namaz_count", 0)
                        st.rerun()

            user_lang = u_dict.get('target_language', 'Yok')
            if user_lang != 'Yok':
                st.markdown(f'<span class="badge-pill badge-dil">🌐 {user_lang} Pratik</span>', unsafe_allow_html=True)

            st.divider()
            st.markdown("🎯 **Günün Hedefi**")
            st.info(f"{u_dict.get('daily_goal')}")
            
            st.markdown("🎁 **Hak Edilecek Ödül**")
            st.success(f"{u_dict.get('reward')}")
            
            is_done = st.checkbox("Bugün hedefimi başardım!", value=bool(u_dict.get('goal_completed', 0)))
            if is_done != bool(u_dict.get('goal_completed', 0)):
                update_user_field(u_dict['id'], "goal_completed", int(is_done))
                if is_done:
                    st.balloons()
                    st.success("Tebrikler!")
                st.rerun()

        comp_name = str(u_dict.get('companion') or 'Yusuf')
        nick_name = str(u_dict.get('nickname') or 'Yolcu')
        tone_str = str(u_dict.get('tone') or 'Samimi')
        
        st.subheader(f"🤝 Yoldaş: {comp_name}")
        st.caption(f"Yolcu: {nick_name} | Tarz: {tone_str.split('(')[0]}")

        active_chat_history = get_messages(u_dict['id'], chat_id=current_chat)
        for m in active_chat_history:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

        if prompt := st.chat_input("İçini dök veya anlat..."):
            save_message(u_dict['id'], current_chat, "user", prompt)
            with st.chat_message("user"):
                st.markdown(prompt)

            name_instruction = ""
            if u_dict.get('real_name') == "Henüz Tespit Edilmedi":
                name_instruction = "Kullanıcı takma ad kullanıyor olabilir. Sohbet arasında doğal bir merakla 'Peki dışarıda sana ne derler? Nüfustaki adın ne?' diye nazikçe sor."

            sistem_talimati = f"""
            Sen 'Yoldaş' rehberisin. Adın: {comp_name}.
            Kullanıcı: {nick_name}, Hitap: {u_dict.get('hitap', 'Dostum')}.
            Yaş Grubu: {u_dict.get('age_group', '13-18 Yaş (Genç)')}.
            Günün Görevi: {u_dict.get('daily_goal')}.
            Ödül: {u_dict.get('reward')}.
            Hedeflenen Dil: {u_dict.get('target_language')}.
            GİZLİ YÖNLENDİRME: {u_dict.get('admin_guidance')}.

            GERÇEK AD SORMA: {name_instruction}
            İLGİ ALANI: Bilgisayar dışında nelerden keyif aldığını (sinema, marvel, satranç, doğa vb.) doğal sohbette keşfet.
            
            KURALLAR:
            1. Samimi, mert, bilge Türk diliyle konuş. Asla robotik olma.
            2. Çocuk 'hemen ders mi az sohbet edelim' derse: Kesinlikle hak ver! 'Haklısın dostum, hemen ders diye boğazına yapışacak halimiz yok, önce iki çift laf edelim' diyerek samimiyet kur. Marvel'dan, sevdiği karakterlerden veya filmlerden muhabbeti aç.
            3. Cevaplar 2 paragrafı aşmasın.
            """

            with st.chat_message("assistant"):
                try:
                    stream_obj = get_streaming_response(
                        contents=prompt,
                        system_instruction=sistem_talimati
                    )
                    
                    def stream_generator():
                        for chunk in stream_obj:
                            if chunk.text:
                                yield chunk.text

                    full_response = st.write_stream(stream_generator())
                    save_message(u_dict['id'], current_chat, "assistant", full_response)
                except Exception as e:
                    fallback_reply = "Dostum haklısın, hemen derse girmeyelim! Gel önce Marvel'dan konuşalım; en sevdiğin karakter hangisi?"
                    st.markdown(fallback_reply)
                    save_message(u_dict['id'], current_chat, "assistant", fallback_reply)

            # Analiz çağrısı ana yanıt tamamlandıktan sonra arka planda sessizce yürütülür
            analyze_and_evolve_user(
                u_dict['id'],
                prompt,
                u_dict.get('real_name', 'Henüz Tespit Edilmedi'),
                u_dict.get('discovered_interests', 'Henüz keşfediliyor'),
                u_dict.get('target_language', 'Yok'),
                bool(u_dict.get('namaz_tracking', 0))
            )
