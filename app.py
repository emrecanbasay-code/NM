import streamlit as st
import json
from datetime import datetime

st.set_page_config(
    page_title="Akut İnme ve Vertigo Karar Destek Sistemi",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - Airtable/Replicate Design System
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --primary-dark: #181d26;
        --primary-active: #0d1218;
        --canvas: #ffffff;
        --surface-soft: #f8fafc;
        --surface-strong: #e0e2e6;
        --signature-coral: #ea2804;
        --signature-forest: #0a2e0e;
        --signature-cream: #f5e9d4;
        --status-green: #2b9a66;
        --status-red: #dc2626;
        --border-strong: #9297a0;
        --hairline: #dddddd;
    }

    * {
        box-sizing: border-box;
    }

    html, body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
        background-color: var(--canvas);
        color: var(--primary-dark);
    }

    .stApp {
        background-color: var(--canvas);
    }

    .stSidebar {
        background-color: var(--canvas) !important;
        border-right: 1px solid var(--hairline) !important;
    }

    .stSidebar .stRadio label div:first-child {
        font-size: 18px;
        font-weight: 600;
        color: var(--primary-dark);
    }

    .stRadio label {
        display: flex;
        align-items: center;
        padding: 12px 16px;
        margin: 4px 0;
        border-radius: 12px;
        background-color: var(--surface-soft);
        border: 2px solid transparent;
        transition: all 0.2s ease;
        cursor: pointer;
    }

    .stRadio label:hover {
        background-color: var(--surface-strong);
        border-color: var(--border-strong);
    }

    .stRadio label:has(input:checked) {
        background-color: var(--primary-dark);
        color: var(--canvas);
        border-color: var(--primary-dark);
    }

    .stRadio label:has(input:checked) div {
        color: var(--canvas) !important;
    }

    h1 {
        font-size: 40px !important;
        font-weight: 700 !important;
        color: var(--primary-dark) !important;
        margin-bottom: 24px !important;
        letter-spacing: -1px;
    }

    h2 {
        font-size: 32px !important;
        font-weight: 600 !important;
        color: var(--primary-dark) !important;
        margin-top: 32px !important;
        margin-bottom: 16px !important;
        letter-spacing: -0.5px;
    }

    h3 {
        font-size: 24px !important;
        font-weight: 600 !important;
        color: var(--primary-dark) !important;
        margin-top: 24px !important;
        margin-bottom: 12px !important;
    }

    .section-card {
        background-color: var(--canvas);
        border: 1px solid var(--hairline);
        border-radius: 12px;
        padding: 32px;
        margin-bottom: 24px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }

    .signature-card {
        background-color: var(--signature-cream);
        border-radius: 12px;
        padding: 32px;
        margin-bottom: 24px;
        border: 2px solid var(--signature-forest);
    }

    .alert-danger {
        background-color: #fef2f2 !important;
        border: 2px solid var(--status-red) !important;
        border-radius: 12px !important;
        padding: 24px !important;
    }

    .alert-danger h2, .alert-danger h3 {
        color: var(--status-red) !important;
    }

    .alert-success {
        background-color: #f0fdf4 !important;
        border: 2px solid var(--status-green) !important;
        border-radius: 12px !important;
        padding: 24px !important;
    }

    .alert-success h2, .alert-success h3 {
        color: var(--status-green) !important;
    }

    .stButton > button {
        background-color: var(--primary-dark) !important;
        color: var(--canvas) !important;
        border: 2px solid var(--primary-dark) !important;
        border-radius: 12px !important;
        padding: 12px 24px !important;
        font-size: 16px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button:hover {
        background-color: var(--primary-active) !important;
        border-color: var(--primary-active) !important;
    }

    .stButton[kind="secondary"] > button {
        background-color: var(--canvas) !important;
        color: var(--primary-dark) !important;
        border: 2px solid var(--hairline) !important;
    }

    .stButton[kind="secondary"] > button:hover {
        background-color: var(--surface-soft) !important;
        border-color: var(--border-strong) !important;
    }

    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select {
        border: 2px solid var(--hairline) !important;
        border-radius: 6px !important;
        padding: 12px 16px !important;
        font-size: 14px !important;
        background-color: var(--canvas) !important;
        color: var(--primary-dark) !important;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus {
        border-color: var(--signature-coral) !important;
        outline: none !important;
    }

    .stCheckbox label {
        display: flex;
        align-items: center;
        padding: 8px 0;
        color: var(--primary-dark);
        font-size: 14px;
    }

    .info-box {
        background-color: #eff6ff;
        border-left: 4px solid var(--signature-coral);
        border-radius: 6px;
        padding: 16px;
        margin: 12px 0;
    }

    .info-box p {
        margin: 0;
        font-size: 14px;
        color: var(--primary-dark);
        line-height: 1.5;
    }

    .whatsapp-output {
        background-color: #f8fafc;
        border: 2px solid var(--hairline);
        border-radius: 12px;
        padding: 24px;
        margin-top: 24px;
        font-family: 'JetBrains Mono', 'Consolas', monospace;
        font-size: 13px;
        line-height: 1.6;
        white-space: pre-wrap;
        word-wrap: break-word;
    }

    .divider {
        border: none;
        border-top: 2px solid var(--hairline);
        margin: 32px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'nihss_score' not in st.session_state:
    st.session_state.nihss_score = 0
if 'aspects_score' not in st.session_state:
    st.session_state.aspects_score = 10
if 'current_time' not in st.session_state:
    st.session_state.current_time = datetime.now()

# Sidebar navigation
with st.sidebar:
    st.markdown("""
    <div style="padding: 32px 16px; border-bottom: 2px solid var(--hairline); margin-bottom: 24px;">
        <h1 style="font-size: 24px !important; margin: 0 !important;">🏥</h1>
        <p style="font-size: 14px; color: var(--primary-active); margin: 8px 0 0 0;">Karar Destek Sistemi</p>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Sayfa Seçimi",
        ["🧠 Akut İnme", "🌀 Vertigo (HINTS)", "📊 NIHSS Hesaplayıcı", "🧫 ASPECTS Hesaplayıcı"],
        label_visibility="collapsed"
    )

# ==================== NIHSS HESAPLAYICI SAYFASI ====================
if page == "📊 NIHSS Hesaplayıcı":
    st.markdown("# 📊 Detaylı NIHSS Hesaplayıcı")
    st.markdown("---")

    st.markdown("""
    <div class='info-box'>
        <p><strong>ℹ️ NIHSS (National Institutes of Health Stroke Scale):</strong><br>
        İnme şiddetini değerlendirmek için kullanılan 11 parametrelik puanlama sistemi. Maksimum puan 42.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 1. Bilinç Durumu")
    with st.expander("ℹ️ Nasıl Değerlendirilir?"):
        st.markdown("""
        **1a - Bilinç Seviyesi:** Hastanın uyanıklık durumu değerlendirilir.
        
        **Değerlendirme Yöntemi:**
        - Hasta normal ses tonuyla seslenir
        - Yanıt yoksa daha yüksek sesle seslenir
        - Hala yanıt yoksa ağrılı uyaranlar (göğüs çınlaması) uygulanır
        
        **Skorlama:**
        - **0 (Alert):** Hasta tamamen uyanık, sorulara anında yanıt veriyor
        - **1 (Drowsy):** Hasta uykulu ama sesli uyaranlarla kolayca uyanabiliyor
        - **2 (Stupor):** Sadece ağrılı uyaranlarla uyanıyor, sorulara yavaş yanıt veriyor
        - **3 (Coma):** Ağrılı uyaranlara bile anlamlı yanıt vermiyor
        """)

    col1, col2 = st.columns([3, 1])
    with col1:
        consciousness_1a = st.radio(
            "1a - Bilinç Seviyesi",
            ["Alert (0)", "Drowsy (1)", "Stupor (2)", "Coma (3)"],
            horizontal=True,
            index=0,
            key="nihss_1a"
        )
    with col2:
        st.markdown(f"**Puan:** {consciousness_1a.split('(')[1].split(')')[0]}")

    st.markdown("### 2. Bilinç Soruları (1b)")
    with st.expander("ℹ️ Nasıl Değerlendirilir?"):
        st.markdown("""
        **1b - Bilinç Soruları:** Hasta iki soruya yanıt verir, oryantasyon düzeyi değerlendirilir.
        
        **Sorular:**
        - **Ay:** Hangi ayda olduğunuzu biliyor musunuz?
        - **Yaş:** Kaç yaşındasınız?
        
        **Skorlama:**
        - **0:** İkisi de doğru cevaplandı
        - **1:** Sadece biri doğru cevaplandı
        - **2:** Hiçbiri doğru cevaplanmadı
        
        **Önemli:** Sorulara yanıt veremeyen komalı hastalarda 0 puan verilir.
        """)

    col1, col2 = st.columns(2)
    with col1:
        q1 = st.radio(
            "Ay - Yaş",
            ["İkisi de doğru (0)", "Bir doğru (1)", "Hiçbiri doğru (2)"],
            horizontal=True,
            index=0,
            key="nihss_1b_q1"
        )
    with col2:
        q2 = st.radio(
            "Ay - Yer",
            ["İkisi de doğru (0)", "Bir doğru (1)", "Hiçbiri doğru (2)"],
            horizontal=True,
            index=0,
            key="nihss_1b_q2"
        )

    st.markdown("### 3. Bilinç Emirleri (1c)")
    with st.expander("ℹ️ Nasıl Değerlendirilir?"):
        st.markdown("""
        **1c - Bilinç Emirleri:** Hasta basit motor komutlarını yerine getirip getiremediği değerlendirilir.
        
        **Komutlar:**
        - Gözlerini aç/kapat
        - Tutuk kapatıp aç (gözlerini kapat)
        
        **Skorlama:**
        - **0:** İki komutu da doğru yapar
        - **1:** Sadece bir komutu yapar
        - **2:** Hiçbirini yapmaz
        
        **Önemli:** Hasta traube veya etkili cevap veremiyorsa 0 puan verilir.
        """)

    commands = st.radio(
        "Aç/Kapat gözleri",
        ["İkisi de yapar (0)", "Bir yapar (1)", "Hiçbiri yapmaz (2)"],
        horizontal=True,
        index=0,
        key="nihss_1c"
    )

    st.markdown("### 4. En İyi Gaze (2)")
    with st.expander("ℹ️ Nasıl Değerlendirilir?"):
        st.markdown("""
        **2 - En İyi Gaze:** Göz hareketleri ve deviasyon değerlendirilir.
        
        **Değerlendirme Yöntemi:**
        - Hastanın gözlerini önce sağa, sonra sola bakması istenir
        - Gözlerin takip edip etmediği ve ortada sabit kalıp kalmadığına bakılır
        
        **Skorlama:**
        - **0:** Normal - Gözler ortada sabit, hareket serbest
        - **1:** Paralizi var - Gözler bir yana deviye olmuş, tam kısıtlılık yok
        - **2:** Deviasyon var - Gözler tamamen bir tarafa sabitlenmiş
        
        **Önemli:** Komanın nedeni (beyin sapı vs. hemisferik) değerlendirmesinde kritik.
        """)

    gaze = st.radio(
        "Göz Bakışları",
        ["Normal (0)", "Paralizi var (1)", "Deviasyon var (2)"],
        horizontal=True,
        index=0,
        key="nihss_2"
    )

    st.markdown("### 5. Görme Alanı (3)")
    with st.expander("ℹ️ Nasıl Değerlendirilir?"):
        st.markdown("""
        **3 - Görme Alanı:** Her iki gözün görme alanı değerlendirilir.
        
        **Değerlendirme Yöntemi:**
        - Konfrontasyon testi (parmağı hareket ettirerek)
        - Hasta gördüğünü söyleyince yanıt verir
        - Her quadranta ayrı ayrı bakılır
        
        **Skorlama:**
        - **0:** Normal - Tüm quadrantal görme mevcut
        - **1:** Hemianopsi - Yarım kör (tek taraf)
        - **2:** Hemianopsi+ - Ciddi yarım körlük, tanımlanabilir quadrant yok
        - **3:** Kör - Hiçbir quadrant görülmüyor
        
        **Önemli:** Hasta görmediğini söyleyemezse test yapılamaz, 0 puan verilir.
        """)

    visual = st.radio(
        "Görme Alanı",
        ["Normal (0)", "Hemianopsi (1)", "Hemianopsi+ (2)", "Kör (3)"],
        horizontal=True,
        index=0,
        key="nihss_3"
    )

    st.markdown("### 6. Fasiyal Felç (4)")
    with st.expander("ℹ️ Nasıl Değerlendirilir?"):
        st.markdown("""
        **4 - Fasiyal Felç:** Yüz asimetrisi değerlendirilir (7. Kraniyal Sinir).
        
        **Değerlendirme Yöntemi:**
        - Hasta dişlerini göstermesi istenir
        - Gülümsemesi istenir
        - Kaşlarını kaldırması istenir
        - Gözlerini sıkıca kapatması istenir
        
        **Skorlama:**
        - **0:** Normal - Tamamen simetrik
        - **1:** Hafif - Hafif asimetri, aktiviteyle düzeliyor
        - **2:** Paralizi - Yüz alt yarısında belirgin felç
        - **3:** Tam - Yüzde tam veya neredeyse tam felç
        
        **Önemli:** Santral (üzerinde) ve periferik (altında) ayrımı önemlidir.
        """)

    facial = st.radio(
        "Fasiyal Paresi",
        ["Normal (0)", "Hafif (1)", "Paralizi (2)", "Tam (3)"],
        horizontal=True,
        index=0,
        key="nihss_4"
    )

    st.markdown("### 7. Motor - Sol Üst Ekstremite (5a)")
    with st.expander("ℹ️ Nasıl Değerlendirilir?"):
        st.markdown("""
        **5a - Motor Sol Üst Ekstremite:** Sol kolun motor gücü değerlendirilir.
        
        **Değerlendirme Yöntemi:**
        - Kolu 90 derece kaldırıp 5 saniye tutması istenir
        - Eğer tutamıyorsa yatak üzerinde kaldırması istenir
        - Dirence karşı test edilir
        
        **Skorlama:**
        - **0:** Normal - 90°yi 5 saniye tutar, dirence karşı dayanır
        - **1:** Hafif - Tutuyor ama dirence karşı yenilebilir
        - **2:** Orta - Yere düşüyor ama yataktan kaldırabiliyor
        - **3:** Ağır - Yataktan kaldırabiliyor ama havaya kaldıramıyor
        - **4:** Tam - Hareketsiz veya minimal hareket
        
        **Önemli:** Ağrılı uyaranlara yanıtta bile değerlendirilir.
        """)

    left_arm = st.radio(
        "Sol Kol",
        ["Normal (0)", "Hafif (1)", "Orta (2)", "Ağır (3)", "Tam (4)"],
        horizontal=True,
        index=0,
        key="nihss_5a"
    )

    st.markdown("### 8. Motor - Sağ Üst Ekstremite (5b)")
    with st.expander("ℹ️ Nasıl Değerlendirilir?"):
        st.markdown("""
        **5b - Motor Sağ Üst Ekstremite:** Sağ kolun motor gücü değerlendirilir.
        
        **Değerlendirme Yöntemi:**
        - Kolu 90 derece kaldırıp 5 saniye tutması istenir
        - Eğer tutamıyorsa yatak üzerinde kaldırması istenir
        - Dirence karşı test edilir
        
        **Skorlama:**
        - **0:** Normal - 90°yi 5 saniye tutar, dirence karşı dayanır
        - **1:** Hafif - Tutuyor ama dirence karşı yenilebilir
        - **2:** Orta - Yere düşüyor ama yataktan kaldırabiliyor
        - **3:** Ağır - Yataktan kaldırabiliyor ama havaya kaldıramıyor
        - **4:** Tam - Hareketsiz veya minimal hareket
        
        **Önemli:** Ağrılı uyaranlara yanıtta bile değerlendirilir.
        """)

    right_arm = st.radio(
        "Sağ Kol",
        ["Normal (0)", "Hafif (1)", "Orta (2)", "Ağır (3)", "Tam (4)"],
        horizontal=True,
        index=0,
        key="nihss_5b"
    )

    st.markdown("### 9. Motor - Sol Alt Ekstremite (6a)")
    with st.expander("ℹ️ Nasıl Değerlendirilir?"):
        st.markdown("""
        **6a - Motor Sol Alt Ekstremite:** Sol bacağın motor gücü değerlendirilir.
        
        **Değerlendirme Yöntemi:**
        - Bacak 30 derece kaldırıp 5 saniye tutması istenir
        - Eğer tutamıyorsa yatak üzerinde kaldırması istenir
        - Dirence karşı test edilir
        
        **Skorlama:**
        - **0:** Normal - 30°yi 5 saniye tutar, dirence karşı dayanır
        - **1:** Hafif - Tutuyor ama dirence karşı yenilebilir
        - **2:** Orta - Yere düşüyor ama yataktan kaldırabiliyor
        - **3:** Ağır - Yataktan kaldırabiliyor ama havaya kaldıramıyor
        - **4:** Tam - Hareketsiz veya minimal hareket
        
        **Önemli:** Ağrılı uyaranlara yanıtta bile değerlendirilir.
        """)

    left_leg = st.radio(
        "Sol Bacak",
        ["Normal (0)", "Hafif (1)", "Orta (2)", "Ağır (3)", "Tam (4)"],
        horizontal=True,
        index=0,
        key="nihss_6a"
    )

    st.markdown("### 10. Motor - Sağ Alt Ekstremite (6b)")
    with st.expander("ℹ️ Nasıl Değerlendirilir?"):
        st.markdown("""
        **6b - Motor Sağ Alt Ekstremite:** Sağ bacağın motor gücü değerlendirilir.
        
        **Değerlendirme Yöntemi:**
        - Bacak 30 derece kaldırıp 5 saniye tutması istenir
        - Eğer tutamıyorsa yatak üzerinde kaldırması istenir
        - Dirence karşı test edilir
        
        **Skorlama:**
        - **0:** Normal - 30°yi 5 saniye tutar, dirence karşı dayanır
        - **1:** Hafif - Tutuyor ama dirence karşı yenilebilir
        - **2:** Orta - Yere düşüyor ama yataktan kaldırabiliyor
        - **3:** Ağır - Yataktan kaldırabiliyor ama havaya kaldıramıyor
        - **4:** Tam - Hareketsiz veya minimal hareket
        
        **Önemli:** Ağrılı uyaranlara yanıtta bile değerlendirilir.
        """)

    right_leg = st.radio(
        "Sağ Bacak",
        ["Normal (0)", "Hafif (1)", "Orta (2)", "Ağır (3)", "Tam (4)"],
        horizontal=True,
        index=0,
        key="nihss_6b"
    )

    st.markdown("### 11. Ataksi (7)")
    with st.expander("ℹ️ Nasıl Değerlendirilir?"):
        st.markdown("""
        **7 - Ataksi:** Serebellar fonksiyonlar değerlendirilir.
        
        **Testler:**
        - **Parmak-Burun Testi:** Hasta parmağıyla burnuna, sonra doktorun parmağına dokunur
        - **Ardışık Hareketler:** Elleri dizlerine hızla ters-yüz şeklinde vurması istenir
        - **Ayağını Kaldır-İndir:** Ayağını yataktan kaldırıp indirmesi istenir
        
        **Skorlama:**
        - **0:** Yok - Tüm testler normal
        - **1:** Bir ekstremite - Bir kolda veya bir bacakta ataksi var
        - **2:** İki ekstremite - İki veya daha fazla ekstremitede ataksi var
        
        **Önemli:** Yeterli motor güç yoksa test yapılamaz, 0 puan verilir.
        """)

    ataxia = st.radio(
        "Ataksi",
        ["Yok (0)", "Bir ekstremite (1)", "İki ekstremite (2)"],
        horizontal=True,
        index=0,
        key="nihss_7"
    )

    st.markdown("### 12. Duyu (8)")
    with st.expander("ℹ️ Nasıl Değerlendirilir?"):
        st.markdown("""
        **8 - Duyu:** Ağrı, sıcaklık ve dokunma duyusu değerlendirilir.
        
        **Değerlendirme Yöntemi:**
        - Pense veya iğne ile hafif uyarılar uygulanır
        - Hastanın uyarıyı hissedip hissetmediği sorulur
        - Her iki taraf karşılaştırılır (yanıp sönme)
        
        **Skorlama:**
        - **0:** Normal - Uyarıları hissediyor ve doğru yanıt veriyor
        - **1:** Hafif/Moderat - Uyarıları az hissediyor veya yanıtı yavaş
        - **2:** Şiddetli - Uyarıları hissetmiyor veya tamamen kayıp
        
        **Önemli:** Hasta cevap veremiyorsa 0 puan verilir.
        """)

    sensory = st.radio(
        "Duyu",
        ["Normal (0)", "Hafif/moderat (1)", "Şiddetli (2)"],
        horizontal=True,
        index=0,
        key="nihss_8"
    )

    st.markdown("### 13. Dil (9)")
    with st.expander("ℹ️ Nasıl Değerlendirilir?"):
        st.markdown("""
        **9 - Dil/Afazi:** Dil ve konuşma fonksiyonları değerlendirilir.
        
        **Testler:**
        - Adlandırma testi (kalem, saat vb. nesneleri isimlendirme)
        - Komutları anlama (gözünü kapat, dişlerini göster vb.)
        - Spontan konuşmayı dinleme
        
        **Skorlama:**
        - **0:** Normal - Tamamen anlama ve ifade
        - **1:** Hafif - Hafif afazi, akıcı konuşma ama bazı hatalar
        - **2:** Ağır - Ciddi afazi, sınırlı anlama ve ifade
        - **3:** Mute/Total - Konuşma yok veya tam anlamama
        
        **Önemli:** Hasta yanıt veremiyorsa 0 puan verilir.
        """)

    language = st.radio(
        "Dil/Afazi",
        ["Normal (0)", "Hafif (1)", "Ağır (2)", "Mute/Total (3)"],
        horizontal=True,
        index=0,
        key="nihss_9"
    )

    st.markdown("### 14. Dizartri (10)")
    with st.expander("ℹ️ Nasıl Değerlendirilir?"):
        st.markdown("""
        **10 - Dizartri:** Artikülasyon ve konuşma netliği değerlendirilir.
        
        **Değerlendirme Yöntemi:**
        - Hasta bir cümleyi sesli okuması veya tekrar etmesi istenir
        - Kelimelerin telaffuz edilme şekline bakılır
        - "Mama, tip-top, fifty-fifty" gibi kelimeler kullanılabilir
        
        **Skorlama:**
        - **0:** Normal - Tamamen net ve akıcı
        - **1:** Hafif - Hafif pelteklik veya yavaşlama, anlaşılabilir
        - **2:** Ağır - Çok peltek veya yavaş, anlaşılması zor
        
        **Önemli:** Hasta konuşamıyorsa 0 puan verilir.
        """)

    dysarthria = st.radio(
        "Dizartri",
        ["Normal (0)", "Hafif (1)", "Ağır (2)"],
        horizontal=True,
        index=0,
        key="nihss_10"
    )

    st.markdown("### 15. İhmal/Dikkat (11)")
    with st.expander("ℹ️ Nasıl Değerlendirilir?"):
        st.markdown("""
        **11 - İhmal/Dikkat:** Hastanın dikkat dağıtma testleri değerlendirilir.
        
        **Testler:**
        - **Görsel İhmal:** Hasta iki elini kaldırıp, hekim istenmiyorsa birini indirmesi istenir
        - **Duysal İhmal:** Hasta iki tarafına dokunulup, dokunulan tarafı söylemesi istenir
        - **Görsel-Sözel Hatalar:** Hasta gösterilen nesneleri isimlendirirken bir tarafı atlıyor mu
        
        **Skorlama:**
        - **0:** Yok - Tüm testler normal, dikkat tam
        - **1:** Bir duyuda - Görsel veya duysal, sadece birinde ihmal
        - **2:** İki duyuda - Hem görsel hem duysal ihmal var
        
        **Önemli:** Hasta testleri yapamıyorsa 0 puan verilir.
        """)

    neglect = st.radio(
        "İhmal",
        ["Yok (0)", "Bir duyuda (1)", "İki duyuda (2)"],
        horizontal=True,
        index=0,
        key="nihss_11"
    )

    st.markdown("---")

    # Calculate NIHSS
    nihss_map = {
        'nihss_1a': {'Alert (0)': 0, 'Drowsy (1)': 1, 'Stupor (2)': 2, 'Coma (3)': 3},
        'nihss_1b_q1': {'İkisi de doğru (0)': 0, 'Bir doğru (1)': 1, 'Hiçbiri doğru (2)': 2},
        'nihss_1b_q2': {'İkisi de doğru (0)': 0, 'Bir doğru (1)': 1, 'Hiçbiri doğru (2)': 2},
        'nihss_1c': {'İkisi de yapar (0)': 0, 'Bir yapar (1)': 1, 'Hiçbiri yapmaz (2)': 2},
        'nihss_2': {'Normal (0)': 0, 'Paralizi var (1)': 1, 'Deviasyon var (2)': 2},
        'nihss_3': {'Normal (0)': 0, 'Hemianopsi (1)': 1, 'Hemianopsi+ (2)': 2, 'Kör (3)': 3},
        'nihss_4': {'Normal (0)': 0, 'Hafif (1)': 1, 'Paralizi (2)': 2, 'Tam (3)': 3},
        'nihss_5a': {'Normal (0)': 0, 'Hafif (1)': 1, 'Orta (2)': 2, 'Ağır (3)': 3, 'Tam (4)': 4},
        'nihss_5b': {'Normal (0)': 0, 'Hafif (1)': 1, 'Orta (2)': 2, 'Ağır (3)': 3, 'Tam (4)': 4},
        'nihss_6a': {'Normal (0)': 0, 'Hafif (1)': 1, 'Orta (2)': 2, 'Ağır (3)': 3, 'Tam (4)': 4},
        'nihss_6b': {'Normal (0)': 0, 'Hafif (1)': 1, 'Orta (2)': 2, 'Ağır (3)': 3, 'Tam (4)': 4},
        'nihss_7': {'Yok (0)': 0, 'Bir ekstremite (1)': 1, 'İki ekstremite (2)': 2},
        'nihss_8': {'Normal (0)': 0, 'Hafif/moderat (1)': 1, 'Şiddetli (2)': 2},
        'nihss_9': {'Normal (0)': 0, 'Hafif (1)': 1, 'Ağır (2)': 2, 'Mute/Total (3)': 3},
        'nihss_10': {'Normal (0)': 0, 'Hafif (1)': 1, 'Ağır (2)': 2},
        'nihss_11': {'Yok (0)': 0, 'Bir duyuda (1)': 1, 'İki duyuda (2)': 2}
    }

    total_nihss = 0
    for key, mapping in nihss_map.items():
        if key in st.session_state:
            total_nihss += mapping.get(st.session_state[key], 0)

    st.session_state.nihss_score = total_nihss

    st.markdown(f"""
    <div class='signature-card'>
        <h3>📊 NIHSS Toplam Skor: **{total_nihss}/42**</h3>
    </div>
    """, unsafe_allow_html=True)

    if total_nihss >= 6:
        st.error("⚠️ Yüksek NIHSS skoru! Acil değerlendirme gerekli.")
    elif total_nihss >= 4:
        st.warning("⚡ Orta NIHSS skoru. Takip gerekli.")
    else:
        st.success("✅ Düşük NIHSS skoru")

    st.info("💡 Bu skor otomatik olarak 'Akut İnme' sayfasına aktarılacaktır.")

# ==================== ASPECTS HESAPLAYICI SAYFASI ====================
elif page == "🧫 ASPECTS Hesaplayıcı":
    st.markdown("# 🧫 Detaylı ASPECTS Hesaplayıcı")
    st.markdown("---")

    st.markdown("""
    <div class='info-box'>
        <p><strong>ℹ️ ASPECTS (Alberta Stroke Program Early CT Score):</strong><br>
        BT'de erken iskemi bulgularını değerlendirmek için kullanılan puanlama sistemi. Maksimum puan 10. Hipodens (koyu) görünen bölgeleri işaretleyin.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### MCA Bölgesi (Hemisphere - Derin Yapılar)")

    col1, col2 = st.columns(2)
    with col1:
        c = st.checkbox("Caudate nucleus (Hipodens var)", key="aspects_c")
        l = st.checkbox("Lentiform nucleus (Hipodens var)", key="aspects_l")
        ic = st.checkbox("Internal capsule (Hipodens var)", key="aspects_ic")
    with col2:
        ins = st.checkbox("Insular ribbon (Hipodens var)", key="aspects_ins")

    st.markdown("### MCA Bölgesi (Cortex - Korteks)")

    col1, col2 = st.columns(2)
    with col1:
        m1 = st.checkbox("M1 - Anterior (Hipodens var)", key="aspects_m1")
        m2 = st.checkbox("M2 - Anterior (Hipodens var)", key="aspects_m2")
        m3 = st.checkbox("M3 - Posterior (Hipodens var)", key="aspects_m3")
    with col2:
        m4 = st.checkbox("M4 - Posterior (Hipodens var)", key="aspects_m4")
        m5 = st.checkbox("M5 - Lateral (Hipodens var)", key="aspects_m5")
        m6 = st.checkbox("M6 - Lateral (Hipodens var)", key="aspects_m6")

    st.markdown("---")

    # Calculate ASPECTS
    aspects_regions = [c, l, ic, ins, m1, m2, m3, m4, m5, m6]
    total_aspects = 10 - sum(aspects_regions)
    st.session_state.aspects_score = total_aspects

    st.markdown(f"""
    <div class='signature-card'>
        <h3>📊 ASPECTS Toplam Skor: **{total_aspects}/10**</h3>
        <p>Hipodens Bölge Sayısı: {sum(aspects_regions)}/10</p>
    </div>
    """, unsafe_allow_html=True)

    if total_aspects <= 7:
        st.error("⚠️ Düşük ASPECTS skoru! Büyük infarkt riski. TPA kontrendike olabilir.")
    elif total_aspects <= 8:
        st.warning("⚡ Orta ASPECTS skoru. Klinik korelasyon gerekli.")
    else:
        st.success("✅ İyi ASPECTS skoru")

    st.info("💡 Bu skor otomatik olarak 'Akut İnme' sayfasına aktarılacaktır.")

# ==================== AKUT İNME SAYFASI ====================
elif page == "🧠 Akut İnme":
    st.markdown("# 🧠 Akut İnme Karar Destek ve Hızlı Muayene Sistemi")
    st.markdown("---")

    # Hasta Kimliği ve Zamanlama
    with st.expander("👤 Hastanın Kimliği ve Zamanlama", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            name = st.text_input("Ad Soyad", "", key="patient_name")
        with col2:
            age = st.number_input("Yaş", 0, 120, 0, key="patient_age")
        with col3:
            gender = st.selectbox("Cinsiyet", ["", "Kadın", "Erkek"], key="patient_gender")
        with col4:
            weight = st.number_input("Kilo (kg)", 1, 250, 70, key="patient_weight")

        col1, col2, col3 = st.columns(3)
        with col1:
            last_well_time_text = st.text_input("Son İyi Görülme (dün, 2 gün önce vb.)", "", key="last_well_time_text", help="Örn: dün, 2 gün önce, 3 gün önce")
            last_well_time = st.time_input("Son İyi Görülme Saati", datetime.now().time(), key="last_well_time")
        with col2:
            if st.button("🕐 Şu Anki Saati Al", key="get_current_time"):
                st.session_state.current_time = datetime.now()
            st.info(f"Kayıt Saati: {st.session_state.current_time.strftime('%H:%M')}")
        with col3:
            symptom_duration = st.text_input("Süre (dakika/saat)", "", key="symptom_duration")

        col1, col2 = st.columns(2)
        with col1:
            complaint = st.text_area("Şikayet", "", key="complaint")
        with col2:
            history = st.text_area("Hikaye", "", key="history")

        st.markdown("---")

        # Kullanılan İlaçlar
        st.markdown("### 💊 Kullanılan İlaçlar")
        medications = st.text_area("Kullanılan İlaçlar", "", key="medications", help="Hastanın düzenli kullandığı tüm ilaçları yazınız")

        # Kronik Hastalıklar
        st.markdown("### 🏥 Kronik Hastalıklar")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            ht_check = st.checkbox("Hipertansiyon (HT)", key="ht_check")
            if ht_check:
                col1a, col1b = st.columns(2)
                with col1a:
                    ht_duration = st.number_input("Süre (sayı)", 0, 100, 0, key="ht_duration")
                with col1b:
                    ht_unit = st.selectbox("Birim", ["Ay", "Yıl"], key="ht_unit")
            if ht_check:
                ht_note = st.text_input("Açıklama", "", key="ht_note", help="Ek bilgileri buraya yazınız")
        
        with col2:
            dm_check = st.checkbox("Diabetes Mellitus (DM)", key="dm_check")
            if dm_check:
                col2a, col2b = st.columns(2)
                with col2a:
                    dm_duration = st.number_input("Süre (sayı)", 0, 100, 0, key="dm_duration")
                with col2b:
                    dm_unit = st.selectbox("Birim", ["Ay", "Yıl"], key="dm_unit")
            if dm_check:
                dm_note = st.text_input("Açıklama", "", key="dm_note", help="Ek bilgileri buraya yazınız")
        
        with col3:
            svo_check = st.checkbox("SVO (İnme Öyküsü)", key="svo_check")
            if svo_check:
                col3a, col3b = st.columns(2)
                with col3a:
                    svo_duration = st.number_input("Süre (sayı)", 0, 100, 0, key="svo_duration")
                with col3b:
                    svo_unit = st.selectbox("Birim", ["Ay", "Yıl"], key="svo_unit")
            if svo_check:
                svo_note = st.text_input("Açıklama", "", key="svo_note", help="Ek bilgileri buraya yazınız")
        
        col1, col2 = st.columns(2)
        with col1:
            malignancy_check = st.checkbox("Malignite", key="malignancy_check")
            if malignancy_check:
                col1a, col1b = st.columns(2)
                with col1a:
                    malignancy_duration = st.number_input("Süre (sayı)", 0, 100, 0, key="malignancy_duration")
                with col1b:
                    malignancy_unit = st.selectbox("Birim", ["Ay", "Yıl"], key="malignancy_unit")
            if malignancy_check:
                malignancy_note = st.text_input("Açıklama", "", key="malignancy_note", help="Ek bilgileri buraya yazınız")
        
        with col2:
            ckd_check = st.checkbox("Kronik Böbrek Yetmezliği (KBY)", key="ckd_check")
            if ckd_check:
                col2a, col2b = st.columns(2)
                with col2a:
                    ckd_duration = st.number_input("Süre (sayı)", 0, 100, 0, key="ckd_duration")
                with col2b:
                    ckd_unit = st.selectbox("Birim", ["Ay", "Yıl"], key="ckd_unit")
            if ckd_check:
                ckd_note = st.text_input("Açıklama", "", key="ckd_note", help="Ek bilgileri buraya yazınız")
        
        col1, col2 = st.columns(2)
        with col1:
            cad_check = st.checkbox("Koroner Arter Hastalığı (KAH)", key="cad_check")
            if cad_check:
                col1a, col1b = st.columns(2)
                with col1a:
                    cad_duration = st.number_input("Süre (sayı)", 0, 100, 0, key="cad_duration")
                with col1b:
                    cad_unit = st.selectbox("Birim", ["Ay", "Yıl"], key="cad_unit")
            if cad_check:
                cad_note = st.text_input("Açıklama", "", key="cad_note", help="Ek bilgileri buraya yazınız")
        
        with col2:
            cabg_check = st.checkbox("CABG (Kalp Bypass)", key="cabg_check")
            if cabg_check:
                col2a, col2b = st.columns(2)
                with col2a:
                    cabg_duration = st.number_input("Süre (sayı)", 0, 100, 0, key="cabg_duration")
                with col2b:
                    cabg_unit = st.selectbox("Birim", ["Ay", "Yıl"], key="cabg_unit")
            if cabg_check:
                cabg_note = st.text_input("Açıklama", "", key="cabg_note", help="Ek bilgileri buraya yazınız")
        
        col1, col2 = st.columns(2)
        with col1:
            other_chronic_check = st.checkbox("Diğer Kronik Hastalık", key="other_chronic_check")
            if other_chronic_check:
                other_chronic = st.text_input("Hastalık Adı", "", key="other_chronic")
                col1a, col1b = st.columns(2)
                with col1a:
                    other_chronic_duration = st.number_input("Süre (sayı)", 0, 100, 0, key="other_chronic_duration")
                with col1b:
                    other_chronic_unit = st.selectbox("Birim", ["Ay", "Yıl"], key="other_chronic_unit")
            if other_chronic_check:
                other_chronic_note = st.text_input("Açıklama", "", key="other_chronic_note", help="Ek bilgileri buraya yazınız")
        
        # Özgeçmiş
        st.markdown("---")
        st.markdown("### 📋 Özgeçmiş")
        medical_history = st.text_area("Detaylı Özgeçmiş", "", key="medical_history", help="Ameliyatlar, alerjiler, aile öyküsü vb. tüm bilgileri yazınız")

    st.markdown("---")

    # VİTAL BULGULAR VE GÜVENLİK
    st.markdown("## 💓 VİTAL BULGULAR VE GÜVENLİK")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        sbp = st.number_input("Sistolik Tansiyon (mmHg)", 0, 300, 120, key="sbp")
    with col2:
        dbp = st.number_input("Diyastolik Tansiyon (mmHg)", 0, 200, 80, key="dbp")
    with col3:
        bg = st.number_input("Kan Şekeri (mg/dL)", 0, 600, 100, key="bg")
    with col4:
        ecg_rhythm = st.selectbox("EKG Ritmi", ["Sinüs", "Atriyal Fibrilasyon", "Diğer"], index=0, key="ecg_rhythm")

    # Tansiyon uyarısı
    if sbp > 185 or dbp > 110:
        st.error("🚨 KAN BASINCI YÜKSEK! SBP > 185 veya DBP > 110 ise TPA KONTRENDİKEDİR!")

    st.markdown("### Kontrendikasyonlar")

    contraindications = []
    if st.checkbox("Tedaviye semptom başlamasından sonraki 4,5 saat içinde başlanamayacak", key="contra_time_window"):
        contraindications.append("4,5 saat zaman penceresi dışında")
    if st.checkbox("Görüntülemede akut kanama (intraserebral, subaraknoid, subdural)", key="contra_imaging_bleeding"):
        contraindications.append("BT'de akut kanama")
    if st.checkbox("BT'de demarke ve geniş hipodansite", key="contra_hypodensity"):
        contraindications.append("BT'de geniş hipodansite")
    if st.checkbox("Son 24 saatte NOAK kullanımı", key="contra_noak"):
        contraindications.append("Son 24s NOAK kullanımı")
    if st.checkbox("Son 3 ay kafa travması/cerrahi", key="contra_trauma"):
        contraindications.append("Son 3 ay kafa travması/cerrahi")
    if st.checkbox("Aktif kanama", key="contra_bleeding"):
        contraindications.append("Aktif kanama")
    if st.checkbox("Trombositopeni (<100 bin/mm³)", key="contra_thrombocytopenia"):
        contraindications.append("Trombositopeni <100 bin")
    if st.checkbox("INR > 1.7", key="contra_inr"):
        contraindications.append("INR > 1.7")
    if st.checkbox("aPTT > 40 sn", key="contra_aptt"):
        contraindications.append("aPTT > 40 sn")

    if contraindications:
        st.error(f"🚨 KONTRENDİKASYON MEVCUT: {', '.join(contraindications)}")

    st.markdown("---")

    # SKOR GİRİŞLERİ VE TPA HESAPLAYICI
    st.markdown("## 📊 SKOR GİRİŞLERİ VE TPA HESAPLAYICI")

    col1, col2 = st.columns(2)
    with col1:
        nihss_input = st.number_input(
            "NIHSS Skoru (0-42)",
            0, 42,
            int(st.session_state.nihss_score),
            key="nihss_input"
        )
        st.info(f"💡 NIHSS Hesaplayıcı'dan gelen skor: {st.session_state.nihss_score}")
    with col2:
        aspects_input = st.number_input(
            "ASPECTS Skoru (0-10)",
            0, 10,
            int(st.session_state.aspects_score),
            key="aspects_input"
        )
        st.info(f"💡 ASPECTS Hesaplayıcı'dan gelen skor: {st.session_state.aspects_score}")

    if aspects_input < 7:
        st.error("🚨 ASPECTS < 7! Büyük infarkt riski. TPA kontrendike olabilir!")

    st.markdown("### Difüzyon/FLAIR Mismatch")
    mismatch = st.radio(
        "Difüzyon/FLAIR Mismatch",
        ["Hayır", "Evet"],
        horizontal=True,
        index=0,
        key="mismatch",
        label_visibility="collapsed",
        help="Uyanma inmeleri için rehberlik sağlar. Evet ise uyanma inmesi düşünülmelidir."
    )

    st.markdown("### 💉 TPA Doz Hesaplayıcı")

    if weight > 0:
        # Standard TPA dosing: 0.9 mg/kg (max 90 mg)
        # 10% bolus, 90% infusion over 60 minutes
        total_dose = min(0.9 * weight, 90)
        bolus = total_dose * 0.1
        infusion = total_dose * 0.9

        st.markdown(f"""
        <div class='signature-card'>
            <h3>💉 TPA Doz Planı</h3>
            <p><strong>Toplam Doz:</strong> {total_dose:.1f} mg</p>
            <p><strong>Bolus (%10 - 1 dakikada IV):</strong> {bolus:.1f} mg</p>
            <p><strong>İnfüzyon (%90 - 1 saatte IV):</strong> {infusion:.1f} mg</p>
            <p><strong>İnfüzyon Hızı:</strong> {infusion:.1f} mg/saat = {(infusion/60):.2f} mg/dk</p>
        </div>
        """, unsafe_allow_html=True)

        # TPA uygunluk kararı
        tpa_contraindicated = False
        reasons = []

        if contraindications:
            tpa_contraindicated = True
            reasons.append("Kontrendikasyon mevcut")
        if sbp > 185 or dbp > 110:
            tpa_contraindicated = True
            reasons.append("Kan basıncı yüksek")
        if bg < 50:
            tpa_contraindicated = True
            reasons.append("Hipoglisemi")
        if aspects_input < 7:
            tpa_contraindicated = True
            reasons.append("Düşük ASPECTS skoru")

        if tpa_contraindicated:
            st.error(f"🚨 TPA VERİLEMEZ! Sebepler: {', '.join(reasons)}")
        else:
            st.success("✅ TPA verilebilir")

    st.markdown("---")

    # AÇIKLAMALI NÖROLOJİK MUAYENE
    st.markdown("## 🔬 AÇIKLAMALI NÖROLOJİK MUAYENE")

    # Bilinç/Oryantasyon
    st.markdown("### 🧠 Bilinç ve Oryantasyon")
    with st.expander("ℹ️ Açıklama"):
        st.markdown("""
        **Bilinç değerlendirmesi:** Hastanın uyanıklık durumunu ve çevresinin farkında olup olmadığını ölçer.
        
        **Bilinç Seviyeleri:**
        - **Açık:** Tamamen uyanık, sorulara anında ve mantıklı yanıt verir.
        - **Uykuya Meyilli:** Uykuludur, sesli uyaranlarla kolayca uyanır, uyaran kesilince tekrar uykuya dalar.
        - **Koma:** Bilinç tamamen kapalı, ağrılı uyaranlara bile anlamlı yanıt vermez.
        
        **Oryantasyon:** Hastanın zaman, mekan ve kişi bilgisini değerlendirir.
        - **Zaman:** Hangi ayda/yılda olduğunu biliyor mu?
        - **Yer:** Nerede olduğunu biliyor mu?
        - **Kişi:** Kendini tanıyor mu?
        """)
    
    col1, col2 = st.columns([3, 2])
    with col1:
        consciousness = st.radio(
            "Bilinç Durumu",
            ["Açık", "Uykuya Meyilli", "Koma"],
            horizontal=True,
            index=0,
            key="consciousness",
            label_visibility="collapsed"
        )
    with col2:
        consciousness_note = st.text_input("Ek Açıklama", "", key="consciousness_note")
    
    # Oryantasyon Soruları
    st.markdown("#### 📍 Oryantasyon Soruları")
    col1, col2, col3 = st.columns(3)
    with col1:
        orientation_time = st.radio(
            "Zaman (Ay/Yıl)",
            ["Doğru", "Yanlış", "Bilmiyor"],
            horizontal=True,
            index=0,
            key="orientation_time"
        )
    with col2:
        orientation_place = st.radio(
            "Yer (Neresi)",
            ["Doğru", "Yanlış", "Bilmiyor"],
            horizontal=True,
            index=0,
            key="orientation_place"
        )
    with col3:
        orientation_person = st.radio(
            "Kişi (Kendini tanıyor mu)",
            ["Evet", "Hayır", "Kısmen"],
            horizontal=True,
            index=0,
            key="orientation_person"
        )
    
    # Kooperasyon/Emirleri
    st.markdown("#### 🤝 Kooperasyon ve Emirlere Uygunluk")
    col1, col2 = st.columns([3, 2])
    with col1:
        cooperation = st.radio(
            "Kooperasyon/Emirler",
            ["Tam Kooperatif (Her emri yapıyor)", "Kısmen Kooperatif (Bazılarını yapıyor)", "Kooperatif Değil (Yapamıyor)"],
            horizontal=True,
            index=0,
            key="cooperation",
            label_visibility="collapsed"
        )
    with col2:
        cooperation_note = st.text_input("Ek Açıklama", "", key="cooperation_note", help="Örn: Gözlerini aç/kapat, dişlerini göster vb.")

    # Konuşma
    st.markdown("### 💬 Konuşma")
    with st.expander("ℹ️ Açıklama"):
        st.markdown("""
        **Konuşma muayenesi:** Hastanın kendini ifade etme (motor/ekspresif) ve söyleneni anlama (sensöryel/reseptif) yetenekleri değerlendirilir. Spontan konuşma dinlenir, nesneler isimlendirilir, komutlara uyup uymadığına bakılır.
        
        **Konuşma Durumları:**
        - **Doğal:** Kelime telaffuzu, cümle kurma ve anlama tamamen normal.
        - **Dizartri:** Artikülasyon (ses çıkarma) problemi. Dil, dudak veya damak kaslarındaki güçsüzlük nedeniyle konuşma 'sarhoşvari', peltek veya yavaşlamıştır.
        - **Afazi:** Dil ve beyin problemi (genellikle sol hemisfer). Konuşmayı anlama, kelime üretme veya her ikisi birden bozulmuştur.
        """)
    
    col1, col2 = st.columns([3, 2])
    with col1:
        speech = st.radio(
            "Konuşma Durumu",
            ["Doğal", "Dizartri", "Afazi"],
            horizontal=True,
            index=0,
            key="speech",
            label_visibility="collapsed"
        )
    with col2:
        speech_note = st.text_input("Ek Açıklama", "", key="speech_note")

    # Kraniyal/Fasiyal
    st.markdown("### 👁️ Kraniyal ve Fasiyal Muayene")
    with st.expander("ℹ️ Açıklama"):
        st.markdown("""
        **Fasiyal muayene:** 7. Kraniyal Sinir (Fasiyal) ve göz hareket kasları (3., 4., 6. Kraniyal Sinirler) değerlendirilir. Hastadan dişlerini göstermesi, gülümsemesi, gözlerini sıkıca kapatması ve kaşlarını kaldırması istenir. Göz hareketleri için parmak 'H' harfi çizecek şekilde takip ettirilir.
        
        **Fasiyal Muayene Bulguları:**
        - **Doğal:** Yüz istirahatte ve mimik yaparken tamamen simetriktir. Gözler her yöne kısıtlamasız hareket eder.
        - **Santral Asimetri:** Beyin hasarı (örn: inme) nedeniyle sadece yüz alt yarısında felç vardır. Dudak köşesi sağlam tarafa kayar. Alın kasları normaldir.
        - **Periferik Asimetri:** Fasiyal sinir hasarı (örn: Bell Palsisi). Yüzün o tarafında hem alt hem üst yarısı felçlidir. Kaş kaldırılamaz, göz kapatılamaz.
        - **Göz Hareket Kısıtlılığı:** Göz belirli yöne bakamaz, çift görme olabilir.
        """)
    
    col1, col2 = st.columns([3, 2])
    with col1:
        facial_exam = st.radio(
            "Fasiyal Muayene",
            ["Doğal", "Santral Asimetri", "Periferik Asimetri", "Göz Hareket Kısıtlı"],
            horizontal=True,
            index=0,
            key="facial_exam",
            label_visibility="collapsed"
        )
    with col2:
        facial_exam_note = st.text_input("Ek Açıklama", "", key="facial_exam_note")

    # Pupiller
    st.markdown("### 👁️ Pupiller")
    with st.expander("ℹ️ Açıklama"):
        st.markdown("""
        **Pupiller muayenesi:** 3. Kraniyal Sinir (Okülomotor) değerlendirmesinin bir parçasıdır. Pupillerin boyutu ve ışık refleksi incelenir.
        
        **Pupiller Bulguları:**
        - **İzokorik:** İki pupilla eşit boyutta.
        - **Anizokorik:** İki pupilla farklı boyutta (bir diğeri daha büyük veya küçük).
        
        **Işık Refleksi (IR):**
        - **+/+:** İki pupilla da ışığa tepki veriyor.
        - **+/-:** Sağ tepki veriyor, sol vermiyor.
        - **-/+:** Sağ tepki vermiyor, sol veriyor.
        - **-/-:** İkisi de tepki vermiyor.
        """)
    
    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        pupils = st.radio(
            "Pupiller",
            ["İzokorik", "Anizokorik"],
            horizontal=True,
            index=0,
            key="pupils",
            label_visibility="collapsed"
        )
        light_reflex = st.radio(
            "Işık Refleksi (IR)",
            ["+/+", "+/-", "-/+", "-/-"],
            horizontal=True,
            index=0,
            key="light_reflex",
            label_visibility="collapsed"
        )
    with col2:
        pupils_note = st.text_input("Ek Açıklama", "", key="pupils_note")

    # Göz Hareketleri (Gaze)
    st.markdown("### 👀 Göz Hareketleri (Gaze)")
    with st.expander("ℹ️ Açıklama"):
        st.markdown("""
        **Göz hareketleri:** 3., 4., 6. Kraniyal Sinirlerin işlevini değerlendirir. Hastanın gözleri her yöne hareket ettirilir, çift görme olup olmadığına bakılır.
        
        **Göz Hareketleri Bulguları:**
        - **Serbest:** Gözler tüm yönlerde serbestçe hareket eder.
        - **Kısıtlı:** Bir veya daha fazla yönde hareket kısıtlılığı var.
        """)
    
    col1, col2 = st.columns([3, 2])
    with col1:
        gaze_movement = st.radio(
            "Göz Hareketleri (GH)",
            ["Serbest", "Kısıtlı"],
            horizontal=True,
            index=0,
            key="gaze_movement",
            label_visibility="collapsed"
        )
    with col2:
        gaze_note = st.text_input("Ek Açıklama", "", key="gaze_note")

    # Görme Alanı (Visual Field)
    st.markdown("### 👁️ Görme Alanı")
    with st.expander("ℹ️ Açıklama"):
        st.markdown("""
        **Görme alanı muayenesi:** Her iki gözün birlikte ve tek tek görme alanları değerlendirilir. Genellikle parmakla konfrontasyon testi yapılır.
        
        **Görme Alanı Bulguları:**
        - **Normal:** Her iki gözde tam görme alanı.
        - **Hemianopsi:** Yarım kör (sağ/sol/yukarı/aşağı).
        - **Hemianopsi+:** Daha ciddi yarım körlük.
        - **Kör:** Görme yok.
        """)
    
    col1, col2 = st.columns([3, 2])
    with col1:
        visual_field = st.radio(
            "Görme Alanı",
            ["Normal", "Hemianopsi", "Hemianopsi+", "Kör"],
            horizontal=True,
            index=0,
            key="visual_field",
            label_visibility="collapsed"
        )
    with col2:
        visual_field_note = st.text_input("Ek Açıklama", "", key="visual_field_note")

    # Motor Güç
    st.markdown("### 💪 Motor Güç")
    with st.expander("ℹ️ Açıklama"):
        st.markdown("""
        **Motor güç muayenesi:** Kollar ve bacaklardaki kas kuvvetinin dirence karşı test edilmesi. MRC (Medical Research Council) skalasına göre 0-5 arası puanlanır.
        
        **MRC Skalası:**
        - **5/5:** Normal - Yerçekimi ve tam dirence karşı tam güç.
        - **4/5:** Dirence karşı koyar ama yenilebilir.
        - **3/5:** Yerçekimine karşı kaldırabilir ama dirence dayanamaz.
        - **2/5:** Yatakta hareket ettirir, havaya kaldıramaz.
        - **1/5:** Hareket yok ama kasılma hissedilir.
        - **0/5:** Tam paralizi.
        """)
    
    col1, col2 = st.columns(2)
    with col1:
        col1a, col1b = st.columns([3, 2])
        with col1a:
            motor_right = st.radio(
                "Sağ Üst Ekstremite",
                [5, 4, 3, 2, 1, 0],
                horizontal=True,
                index=0,
                key="motor_right",
                label_visibility="collapsed"
            )
        with col1b:
            motor_right_note = st.text_input("Ek Açıklama", "", key="motor_right_note")
        
        col1a, col1b = st.columns([3, 2])
        with col1a:
            motor_left = st.radio(
                "Sol Üst Ekstremite",
                [5, 4, 3, 2, 1, 0],
                horizontal=True,
                index=0,
                key="motor_left",
                label_visibility="collapsed"
            )
        with col1b:
            motor_left_note = st.text_input("Ek Açıklama", "", key="motor_left_note")
    
    with col2:
        col2a, col2b = st.columns([3, 2])
        with col2a:
            motor_right_leg = st.radio(
                "Sağ Alt Ekstremite",
                [5, 4, 3, 2, 1, 0],
                horizontal=True,
                index=0,
                key="motor_right_leg",
                label_visibility="collapsed"
            )
        with col2b:
            motor_right_leg_note = st.text_input("Ek Açıklama", "", key="motor_right_leg_note")
        
        col2a, col2b = st.columns([3, 2])
        with col2a:
            motor_left_leg = st.radio(
                "Sol Alt Ekstremite",
                [5, 4, 3, 2, 1, 0],
                horizontal=True,
                index=0,
                key="motor_left_leg",
                label_visibility="collapsed"
            )
        with col2b:
            motor_left_leg_note = st.text_input("Ek Açıklama", "", key="motor_left_leg_note")

    # Serebellar
    st.markdown("### 🏃 Serebellar Muayene")
    with st.expander("ℹ️ Açıklama"):
        st.markdown("""
        **Serebellar muayene:** Beyinciğin kontrol ettiği denge, koordinasyon ve hareket ölçülülüğünü test eder.
        
        **Testler:**
        - **Parmak-Burun Testi:** Hasta işaret parmağıyla önce kendi burnuna, sonra hekimin parmağına dokunur.
        - **Ardışık Hareketler:** Ellerini dizlerine hızlıca ters-yüz şeklinde vurması istenir.
        
        **Serebellar Muayene Bulguları:**
        - **Normal:** Hareketler akıcı, isabetli ve ritmiktir.
        - **Dismetri:** Hedefi tutturamama. Parmağını burnuna götürürken ıskalar (hedefin ilerisine geçer veya gerisinde kalır).
        - **Disdiadokokinezi:** Hızlı, ardışık ve zıt hareketleri ritmik ve koordineli yapamama. Hareketler düzensiz ve sakardır.
        - **Hepsi Normal:** Her iki test de normaldir.
        """)
    
    col1, col2 = st.columns([3, 2])
    with col1:
        cerebellar = st.radio(
            "Serebellar Muayene",
            ["Normal", "Dismetri", "Disdiadokokinezi", "Hepsi Normal"],
            horizontal=True,
            index=0,
            key="cerebellar",
            label_visibility="collapsed"
        )
    with col2:
        cerebellar_note = st.text_input("Ek Açıklama", "", key="cerebellar_note")

    # Taban Cilt Refleksi
    st.markdown("### 🦶 Taban Cilt Refleksi (TCR)")
    with st.expander("ℹ️ Açıklama"):
        st.markdown("""
        **Plantar Refleks:** Nörolojik muayenenin en kritik refleks testlerinden biri. Ayak tabanının dış kısmı, topuktan serçe parmağına doğru ucu küt bir cisimle (refleks çekicinin arkası veya anahtar) çizilir ve ayak başparmağının tepkisi gözlemlenir.
        
        **TCR Bulguları:**
        - **Bilateral Fleksör (Normal):** Ayak başparmağı ve diğer parmaklar içe doğru (aşağıya) kıvrılır. Sağlıklı erişkinlerde beklenen yanıt.
        - **Ekstansör (+) - Babinski:** Ayak başparmağı geriye (yukarı) kalkar ve diğer parmaklar yelpaze gibi açılır. Üst Motor Nöron hasarının en önemli bulgusu.
        - **Lakayt:** Ayak tabanı çizildiğinde parmaklarda hiçbir hareket olmaz. Şiddetli nöropatilerde veya ayağın çok soğuk olmasında görülebilir.
        """)
    
    col1, col2 = st.columns([3, 2])
    with col1:
        tcr = st.radio(
            "Taban Cilt Refleksi",
            ["Bilateral Fleksör (Normal)", "Sağ Ekstansör (+)", "Sol Ekstansör (+)", "Lakayt"],
            horizontal=True,
            index=0,
            key="tcr",
            label_visibility="collapsed"
        )
    with col2:
        tcr_note = st.text_input("Ek Açıklama", "", key="tcr_note")

    st.markdown("---")

    # WHATSAPP HANDOVER
    st.markdown("## 📱 WhatsApp Handover")

    if st.button("💾 Kaydet ve WhatsApp Özeti Oluştur", key="whatsapp_button"):
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")

        # TPA uygunluk kararı
        tpa_contraindicated = False
        reasons = []
        if contraindications:
            tpa_contraindicated = True
            reasons.append("Kontrendikasyon")
        if sbp > 185 or dbp > 110:
            tpa_contraindicated = True
            reasons.append("KB Yüksek")
        if bg < 50:
            tpa_contraindicated = True
            reasons.append("Hipoglisemi")
        if aspects_input < 7:
            tpa_contraindicated = True
            reasons.append("ASPECTS<7")

        tpa_decision = "❌ VERİLEMEZ" if tpa_contraindicated else "✅ VERİLEBİLİR"
        tpa_reasons = f" ({', '.join(reasons)})" if reasons else ""

        # Kronik hastalıkları birleştir
        chronic_diseases = []
        if ht_check:
            note_str = f" - {ht_note}" if ht_note else ""
            chronic_diseases.append(f"HT ({ht_duration} {ht_unit}){note_str}")
        if dm_check:
            note_str = f" - {dm_note}" if dm_note else ""
            chronic_diseases.append(f"DM ({dm_duration} {dm_unit}){note_str}")
        if svo_check:
            note_str = f" - {svo_note}" if svo_note else ""
            chronic_diseases.append(f"SVO ({svo_duration} {svo_unit}){note_str}")
        if malignancy_check:
            note_str = f" - {malignancy_note}" if malignancy_note else ""
            chronic_diseases.append(f"Malignite ({malignancy_duration} {malignancy_unit}){note_str}")
        if ckd_check:
            note_str = f" - {ckd_note}" if ckd_note else ""
            chronic_diseases.append(f"KBY ({ckd_duration} {ckd_unit}){note_str}")
        if cad_check:
            note_str = f" - {cad_note}" if cad_note else ""
            chronic_diseases.append(f"KAH ({cad_duration} {cad_unit}){note_str}")
        if cabg_check:
            note_str = f" - {cabg_note}" if cabg_note else ""
            chronic_diseases.append(f"CABG ({cabg_duration} {cabg_unit}){note_str}")
        if other_chronic_check:
            note_str = f" - {other_chronic_note}" if other_chronic_note else ""
            chronic_diseases.append(f"{other_chronic} ({other_chronic_duration} {other_chronic_unit}){note_str}")

        whatsapp_summary = f"""
🏥 *AKUT İNME HANDOVER*
📅 {timestamp}

👤 *HASTA BİLGİLERİ:*
• Ad: {name if name else '-'}
• Yaş: {age} ({gender})
• Kilo: {weight} kg
• Son İyi Görülme: {last_well_time_text if last_well_time_text else '-'} ({last_well_time})
• Kayıt Saati: {st.session_state.current_time.strftime('%H:%M')}
• Süre: {symptom_duration if symptom_duration else '-'}

📋 *ŞİKAYET/HİKAYE:*
• Şikayet: {complaint if complaint else '-'}
• Hikaye: {history if history else '-'}

💊 *KULLANILAN İLAÇLAR:*
• {medications if medications else '-'}

🏥 *KRONİK HASTALIKLAR:*
{chr(10).join(['• ' + d for d in chronic_diseases]) if chronic_diseases else '• Yok'}

📋 *ÖZGEÇMİŞ:*
• {medical_history if medical_history else '-'}

💓 *VİTLER:*
• SBP/DBP: {sbp}/{dbp} mmHg
• Kan Şekeri: {bg} mg/dL
• EKG Ritmi: {ecg_rhythm}

⚠️ *KONTRENDİKASYONLAR:*
{chr(10).join(['• ' + c for c in contraindications]) if contraindications else '• Yok'}

📊 *SKORLAR:*
• NIHSS: {nihss_input}/42

🔬 *NÖROLOJİK MUAYENE:*
• Bilinç: {consciousness}{f' - {consciousness_note}' if consciousness_note else ''}
• Oryantasyon: Zaman {orientation_time}, Yer {orientation_place}, Kişi {orientation_person}
• Kooperasyon: {cooperation}{f' - {cooperation_note}' if cooperation_note else ''}
• Konuşma: {speech}{f' - {speech_note}' if speech_note else ''}
• Kraniyal/Fasiyal: {facial_exam}{f' - {facial_exam_note}' if facial_exam_note else ''}
• Pupiller: {pupils}, IR: {light_reflex}{f' - {pupils_note}' if pupils_note else ''}
• Göz Hareketleri (GH): {gaze_movement}{f' - {gaze_note}' if gaze_note else ''}
• Görme Alanı: {visual_field}{f' - {visual_field_note}' if visual_field_note else ''}
• Motor: Sağ Üst {motor_right}{f' - {motor_right_note}' if motor_right_note else ''}, Sol Üst {motor_left}{f' - {motor_left_note}' if motor_left_note else ''}, Sağ Alt {motor_right_leg}{f' - {motor_right_leg_note}' if motor_right_leg_note else ''}, Sol Alt {motor_left_leg}{f' - {motor_left_leg_note}' if motor_left_leg_note else ''}
• Serebellar: {cerebellar}{f' - {cerebellar_note}' if cerebellar_note else ''}
• TCR: {tcr}{f' - {tcr_note}' if tcr_note else ''}
        """.strip()

        st.markdown(f"""
        <div class='whatsapp-output'>
        {whatsapp_summary}
        </div>
        """, unsafe_allow_html=True)

        st.code(whatsapp_summary, language=None)

# ==================== VERTIGO SAYFASI ====================
elif page == "🌀 Vertigo (HINTS)":

    st.markdown("# 🌀 Vertigo ve Baş Dönmesi (HINTS Muayenesi)")
    st.markdown("---")

    # Vertigo History and Vitals
    st.markdown("## 📋 Vertigo Öyküsü ve Vitaller")

    col1, col2, col3 = st.columns(3)
    with col1:
        vertigo_onset = st.selectbox(
            "Şikayet Başlangıcı",
            ["Ani (Saniyeler)", "Dakikalar/Saatler", "Günler"],
            key="vertigo_onset"
        )
    with col2:
        vertigo_trigger = st.selectbox(
            "Tetikleyici",
            ["Baş hareketiyle artıyor", "Sürekli/Spontan"],
            key="vertigo_trigger"
        )
    with col3:
        vertigo_duration = st.text_input("Süre", "", key="vertigo_duration")

    st.markdown("### Eşlik Eden Bulgular")
    accompanying_symptoms = st.multiselect(
        "Eşlik Eden Bulgular",
        [
            "Bulantı/Kusma",
            "İşitme Kaybı / Tinnitus",
            "Şiddetli Baş/Ense Ağrısı (Kırmızı Bayrak!)",
            "Görme Bozukluğu/Çift Görme (Kırmızı Bayrak!)"
        ],
        key="accompanying_symptoms",
        label_visibility="collapsed"
    )

    st.markdown("---")

    # HINTS + Plus Examination
    st.markdown("## 🔬 HINTS + Plus Muayenesi")

    st.markdown("""
    <div class='info-box'>
        <p><strong>ℹ️ HINTS Muayenesi Hakkında:</strong><br>
        Santral (İnme) ve Periferik (İç Kulak) vertigo ayrımında kullanılır. HINTS = Head Impulse, Nystagmus, Test of Skew. "Plus" = Yeni İşitme Kaybı.</p>
    </div>
    """, unsafe_allow_html=True)

    # Head Impulse Test
    st.markdown("### 1. Head Impulse Test (vHIT)")
    head_impulse = st.radio(
        "Head Impulse Testi",
        ["Anormal / Gözden Kaçırma Var (Periferik Lehine)", "Normal (Santral İnme Lehine!)"],
        horizontal=True,
        key="head_impulse",
        label_visibility="collapsed"
    )
    st.info("ℹ️ Hastanın başını hızla sağa/sola çevirirken burnuna bakmasını iste. Göz hedefi kaçırıp geri yakalıyorsa anormaldir (İç kulak). Tam sabit kalıyorsa ve hasta şiddetli vertigoluyken bu test normalse İNME şüphesi!")

    # Nystagmus
    st.markdown("### 2. Nystagmus")
    nystagmus = st.radio(
        "Nistagmus",
        ["Tek Yönlü Yatay (Periferik)", "Yön Değiştiren / Vertikal (Santral İnme!)", "Yok"],
        horizontal=True,
        key="nystagmus",
        label_visibility="collapsed"
    )
    st.info("ℹ️ Sağa bakarken sağa, sola bakarken sola vuruyorsa veya yukarı/aşağı vuruyorsa santraldir.")

    # Test of Skew
    st.markdown("### 3. Test of Skew (Göz Kayması)")
    test_skew = st.radio(
        "Test of Skew",
        ["Yok (Normal)", "Var / Vertikal Kayma (Santral İnme!)"],
        horizontal=True,
        key="test_skew",
        label_visibility="collapsed"
    )
    st.info("ℹ️ Bir gözü kapat, sonra diğerini kapat. Gözlerde yukarı/aşağı dikey bir düzeltme hareketi varsa santraldir.")

    # Plus: Hearing Loss
    st.markdown("### 4. Yeni İşitme Kaybı (Plus)")
    hearing_loss = st.radio(
        "İşitme Kaybı",
        ["Yok", "Var (AICA İnmesi şüphesi)"],
        horizontal=True,
        key="hearing_loss",
        label_visibility="collapsed"
    )
    st.info("ℹ️ Parmak sürtme testi ile değerlendir.")

    st.markdown("---")

    # Positional Test (BPPV)
    st.markdown("## 🔄 Pozisyonel Test (BPPV için)")

    dix_hallpike = st.selectbox(
        "Dix-Hallpike Testi",
        ["Yapılmadı", "Negatif", "Sağ BPPV (Nistagmus +)", "Sol BPPV (Nistagmus +)"],
        key="dix_hallpike"
    )
    st.info("ℹ️ Hastayı sedyede hızla geriye yatırıp başını 45 derece sağa/sola çevirerek nistagmus ara.")

    st.markdown("---")

    # Decision Support
    st.markdown("## 🎯 Karar Destek ve Çıktı")

    # Decision Algorithm
    has_severe_headache = "Şiddetli Baş/Ense Ağrısı (Kırmızı Bayrak!)" in accompanying_symptoms
    has_visual_disturbance = "Görme Bozukluğu/Çift Görme (Kırmızı Bayrak!)" in accompanying_symptoms
    has_central_nystagmus = "Yön Değiştiren / Vertikal (Santral İnme!)" in nystagmus
    has_central_skew = "Var / Vertikal Kayma (Santral İnme!)" in test_skew
    has_normal_head_impulse = "Normal (Santral İnme Lehine!)" in head_impulse
    has_hearing_loss = "Var (AICA İnmesi şüphesi)" in hearing_loss

    # Central Vertigo Risk Assessment
    central_risk = (
        has_severe_headache or
        has_visual_disturbance or
        has_central_nystagmus or
        has_central_skew or
        has_normal_head_impulse or
        has_hearing_loss
    )

    if central_risk:
        st.markdown("""
        <div class='alert-danger'>
            <h2>🚨 DİKKAT: SANTRAL VERTİGO / İNME ŞÜPHESİ!</h2>
            <p><strong>Arka sistem (Posterior Sirkülasyon) inmesi olabilir.</strong></p>
            <p>MR ve Nöroloji Konsültasyonu planlayın!</p>
        </div>
        """, unsafe_allow_html=True)

        # Risk Factors Display
        risk_factors = []
        if has_severe_headache:
            risk_factors.append("✓ Şiddetli Baş/Ense Ağrısı (Kırmızı Bayrak)")
        if has_visual_disturbance:
            risk_factors.append("✓ Görme Bozukluğu/Çift Görme (Kırmızı Bayrak)")
        if has_central_nystagmus:
            risk_factors.append("✓ Santral Nistagmus")
        if has_central_skew:
            risk_factors.append("✓ Pozitif Test of Skew")
        if has_normal_head_impulse:
            risk_factors.append("✓ Normal Head Impulse (ile şiddetli vertigo!)")
        if has_hearing_loss:
            risk_factors.append("✓ Yeni İşitme Kaybı (AICA)")

        st.markdown("**Risk Faktörleri:**")
        for factor in risk_factors:
            st.markdown(f"- {factor}")
    else:
        st.markdown("""
        <div class='alert-success'>
            <h2>✅ Periferik Vertigo ile Uyumlu Bulgular</h2>
            <p>Santral inme bulgusu yok. İç kulak kaynaklı vertigo düşünülmeli.</p>
        </div>
        """, unsafe_allow_html=True)

    # BPPV Assessment
    if "BPPV" in dix_hallpike:
        st.info(f"🔄 {dix_hallpike} - BPPV tanısı ile uyumlu. Epley manevrası düşünülmeli.")

    st.markdown("---")

    # WhatsApp Summary
    st.markdown("## 📱 Vertigo WhatsApp Özeti")

    if st.button("💾 Vertigo WhatsApp Özeti Oluştur", key="vertigo_whatsapp"):
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")

        risk_status = "🚨 SANTRAL VERTİGO / İNME ŞÜPHESİ" if central_risk else "✅ Periferik Vertigo"

        vertigo_whatsapp_summary = f"""
🌀 *VERTIGO HANDOVER (HINTS)*
📅 {timestamp}

📋 *ÖYKÜ:*
• Başlangıç: {vertigo_onset}
• Tetikleyici: {vertigo_trigger}
• Süre: {vertigo_duration}

💓 *EŞLİK EDEN BULGULAR:*
{chr(10).join(['• ' + s for s in accompanying_symptoms]) if accompanying_symptoms else '• Yok'}

🔬 *HINTS MUAYENESİ:*
• Head Impulse: {head_impulse}
• Nystagmus: {nystagmus}
• Test of Skew: {test_skew}
• İşitme Kaybı: {hearing_loss}

🔄 *POZİSYONEL TEST:*
• Dix-Hallpike: {dix_hallpike}

🎯 *KARAR:*
{risk_status}

⚠️ *RİSK FAKTÖRLERİ:*
{chr(10).join(['• ' + f for f in risk_factors]) if central_risk else '• Yok'}

📝 *TAVSİYE:*
{'MR ve Nöroloji Konsültasyonu gereklidir!' if central_risk else 'İç kulak kaynaklı vertigo. BPPV varsa Epley manevrası düşünün.'}
        """.strip()

        st.markdown(f"""
        <div class='whatsapp-output'>
        {vertigo_whatsapp_summary}
        </div>
        """, unsafe_allow_html=True)

        st.code(vertigo_whatsapp_summary, language=None)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; padding: 32px; color: var(--primary-active);'>
    <p><strong>⚠️ YASAL UYARI:</strong> Bu uygulama tıbbi kararı desteklemek için tasarlanmıştır, hekim klinik değerlendirmesinin yerini tutmaz.</p>
    <p style='font-size: 12px; margin-top: 8px;'>Akut İnme ve Vertigo Karar Destek Sistemi v2.0</p>
</div>
""", unsafe_allow_html=True)
