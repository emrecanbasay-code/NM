import streamlit as st
import json
import io
import random
import string
from datetime import datetime, timedelta

# ==================== FIREBASE FIRESTORE ENTEGRASYONU ====================
import firebase_admin
from firebase_admin import credentials, firestore

def init_firebase():
    """
    Firebase'i st.secrets üzerinden başlatır.
    Streamlit Cloud'da Settings > Secrets bölümüne Firebase service account JSON'u eklenir.
    """
    if not firebase_admin._apps:
        # st.secrets["firebase"] altındaki tüm alanları dict olarak al
        firebase_creds = dict(st.secrets["firebase"])
        cred = credentials.Certificate(firebase_creds)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def generate_transfer_code(db) -> str:
    """
    Benzersiz 4 haneli transfer kodu üretir.
    Mevcut kodlarla çakışmadığından emin olur.
    """
    while True:
        code = ''.join(random.choices(string.digits, k=4))
        # Aynı kodun zaten var olup olmadığını kontrol et
        existing = db.collection("handovers").where("transfer_code", "==", code).limit(1).get()
        if not existing:
            return code


def save_handover(db, summary_text: str) -> str:
    """
    WhatsApp handover metnini Firestore'a kaydeder.
    Returns: 4 haneli transfer kodu
    """
    code = generate_transfer_code(db)
    now = datetime.utcnow()
    expiration = now + timedelta(hours=72)

    doc_data = {
        "transfer_code": code,
        "summary_text": summary_text,
        "created_at": now,
        "access_count": 0,
        "expiration_date": expiration,  # Firestore TTL bu alanı kullanacak
    }

    db.collection("handovers").add(doc_data)
    return code


def get_handover(db, code: str) -> dict | None:
    """
    Transfer kodu ile handover verisini getirir.
    Erişim sayacını 1 artırır.
    Süresi dolmuş kayıtları döndürmez.
    """
    docs = db.collection("handovers").where("transfer_code", "==", code).limit(1).get()

    if not docs:
        return None

    doc = docs[0]
    data = doc.to_dict()

    # Süre kontrolü (client-side ek güvenlik)
    expiration = data.get("expiration_date")
    if expiration:
        # Firestore Timestamp'ı datetime'a çevir
        if hasattr(expiration, 'timestamp'):
            exp_dt = expiration
        else:
            exp_dt = expiration

        now = datetime.utcnow()
        # Firestore timestamp karşılaştırması
        try:
            if hasattr(exp_dt, 'seconds'):
                exp_datetime = datetime.utcfromtimestamp(exp_dt.seconds)
            else:
                exp_datetime = exp_dt
            
            if now > exp_datetime:
                return {"expired": True}
        except Exception:
            pass

    # Erişim sayacını artır
    doc.reference.update({"access_count": firestore.Increment(1)})

    return data


# ==================== AI ASISTAN FONKSİYONLARI ====================

# Sabit System Prompt - Halüsinasyonu engellemek için kesin kurallar
SYSTEM_PROMPT = """Sen uzman bir nöroloji asistanı ve klinik veri çıkarma motorusun. 
Görevin, hekimin hasta muayenesi sırasında dikte ettiği metni veya ses kaydını analiz ederek "Akut İnme (Stroke)" değerlendirme formunu doldurmaktır.

KESİN KURALLAR:
1. SADECE VE SADECE sana verilen kayıt/metin içinde AÇIKÇA belirtilen bilgileri çıkar.
2. Hekim bir bulguyu, vital değeri veya muayene adımını SÖYLEMEDİYSE, o alanı KESİNLİKLE uydurma, tahmin etme veya varsayma. Karşılığına doğrudan null değerini ata.
3. Çıktın SADECE VE SADECE geçerli bir JSON objesi olmalıdır. ```json gibi markdown işaretleri EKLEME.

BEKLENEN JSON ŞABLONU VE KABUL EDİLEN DEĞERLER:
{
  "hasta_ad_soyad": (Belirtildiyse yaz, yoksa null),
  "hasta_yas": (Sayısal değer veya null),
  "hasta_cinsiyet": ("Erkek", "Kadın" veya null),
  "hasta_kilo": (Sayısal değer kg cinsinden veya null),
  "son_iyi_gorulme_zamani": (Belirtildiyse yaz, örn: "dün", "2 saat önce", yoksa null),
  "semptom_baslangic_suresi": (Saat veya süre belirtildiyse yaz, yoksa null),
  "sikayet": (Hastanın ana şikayeti belirtildiyse yaz, yoksa null),
  "hikaye": (Hastanın hikayesi belirtildiyse yaz, yoksa null),
  "kullanilan_ilaclar": (Belirtildiyse yaz, yoksa null),
  "ozgecmis": (Belirtildiyse yaz, yoksa null),
  "kronik_hastaliklar": {
    "hipertansiyon": {"var_mi": (true, false veya null), "sure": (Belirtildiyse yaz, yoksa null), "aciklama": (Belirtildiyse yaz, yoksa null)},
    "diyabet": {"var_mi": (true, false veya null), "sure": (Belirtildiyse yaz, yoksa null), "aciklama": (Belirtildiyse yaz, yoksa null)},
    "svo_oykusu": {"var_mi": (true, false veya null), "sure": (Belirtildiyse yaz, yoksa null), "aciklama": (Belirtildiyse yaz, yoksa null)},
    "malignite": {"var_mi": (true, false veya null), "sure": (Belirtildiyse yaz, yoksa null), "aciklama": (Belirtildiyse yaz, yoksa null)},
    "kby": {"var_mi": (true, false veya null), "sure": (Belirtildiyse yaz, yoksa null), "aciklama": (Belirtildiyse yaz, yoksa null)},
    "kah": {"var_mi": (true, false veya null), "sure": (Belirtildiyse yaz, yoksa null), "aciklama": (Belirtildiyse yaz, yoksa null)},
    "cabg": {"var_mi": (true, false veya null), "sure": (Belirtildiyse yaz, yoksa null), "aciklama": (Belirtildiyse yaz, yoksa null)},
    "diger": {"var_mi": (true, false veya null), "hastalik_adi": (Belirtildiyse yaz, yoksa null), "sure": (Belirtildiyse yaz, yoksa null), "aciklama": (Belirtildiyse yaz, yoksa null)}
  },
  "sistolik_tansiyon": (Sadece sayı veya null),
  "diastolik_tansiyon": (Sadece sayı veya null),
  "kan_sekeri": (Sadece sayı veya null),
  "ekg_ritmi": ("Sinüs", "Atriyal Fibrilasyon", "Diğer" veya null),
  "bilinc_durumu": ("Açık", "Uykuya Meyilli", "Koma" veya null),
  "oryantasyon": {
    "zaman": ("Doğru", "Yanlış", "Bilmiyor" veya null),
    "yer": ("Doğru", "Yanlış", "Bilmiyor" veya null),
    "kisi": ("Evet", "Hayır", "Kısmen" veya null)
  },
  "kooperasyon": ("Tam Kooperatif (Her emri yapıyor)", "Kısmen Kooperatif (Bazılarını yapıyor)", "Kooperatif Değil (Yapamıyor)" veya null),
  "konusma": ("Doğal", "Dizartri", "Afazi" veya null),
  "fasiyal_muayene": ("Doğal", "Santral Asimetri", "Periferik Asimetri", "Göz Hareket Kısıtlı" veya null),
  "fasiyal_muayene_aciklama": (Belirtildiyse yaz, örn: "Sağda santral fasyal paralizi", yoksa null),
  "pupiller": ("İzokorik", "Anizokorik" veya null),
  "isik_refleksi": ("+/+", "+/-", "-/+", "-/-" veya null),
  "goz_hareketleri": ("Serbest", "Kısıtlı" veya null),
  "goz_hareketleri_aciklama": (Belirtildiyse yaz, yoksa null),
  "gorme_alani": ("Normal", "Hemianopsi", "Hemianopsi+", "Kör" veya null),
  "gorme_alani_aciklama": (Belirtildiyse yaz, yoksa null),
  "motor_sag_kol": (0'dan 5'e kadar sayı veya null),
  "motor_sol_kol": (0'dan 5'e kadar sayı veya null),
  "motor_sag_bacak": (0'dan 5'e kadar sayı veya null),
  "motor_sol_bacak": (0'dan 5'e kadar sayı veya null),
  "motor_sag_kol_aciklama": (Belirtildiyse yaz, yoksa null),
  "motor_sol_kol_aciklama": (Belirtildiyse yaz, yoksa null),
  "motor_sag_bacak_aciklama": (Belirtildiyse yaz, yoksa null),
  "motor_sol_bacak_aciklama": (Belirtildiyse yaz, yoksa null),
  "serebellar_muayene": ("Normal", "Dismetri", "Disdiadokokinezi", "Hepsi Normal" veya null),
  "serebellar_aciklama": (Belirtildiyse yaz, yoksa null),
  "tcr": ("Bilateral Fleksör (Normal)", "Sağ Ekstansör (+)", "Sol Ekstansör (+)", "Lakayt" veya null),
  "tcr_aciklama": (Belirtildiyse yaz, yoksa null),
  "duyu_kaybi": (Belirtildiyse yaz, yoksa null),
  "kontrendikasyonlar": (Belirtildiyse liste olarak yaz, örn: ["Aktif kanama", "INR > 1.7"], yoksa []),
  "ek_bulgular": (Şablona uymayan ama hekimin belirttiği diğer önemli bulgular, yoksa null)
}

ÖNEMLİ NOTLAR:
- Motor güç değerleri 0-5 arası sayısal olmalıdır (örn: "3/5" denmişse 3 yaz).
- Tansiyon "180/100" denmişse sistolik=180, diastolik=100 olarak ayır.
- Kronik hastalıklar için hekim "HT'si var, 10 yıldır" derse hipertansiyon.var_mi=true, hipertansiyon.sure="10 yıl" yaz.
- Kontrendikasyonlar listesi boş olabilir [].
- Oryantasyon bilgileri ayrı ayrı belirtilmemişse null bırak.
"""


# Whisper için medikal terim ipuçları
WHISPER_MEDICAL_PROMPT = (
    "Tıbbi terimler: Hemianopsi, Dizartri, Afazi, Disdiadokokinezi, İzokorik, Anizokorik, "
    "Babinski, Ekstansör, Fleksör, Serebellar, Dismetri, ASPECTS, NIHSS, TPA, Alteplaz, "
    "Hipertansiyon, Diabetes Mellitus, Atriyal Fibrilasyon, Sinüs ritmi, Plejik, "
    "Hemiparezi, Hemipleji, Stupor, Koma, Kooperatif, Oryantasyon, Fasyal paralizi, "
    "Santral, Periferik, Pupil, Midriyatik, Miyotik, Işık refleksi, Taban cilt refleksi, "
    "Koroner arter, CABG, Malignite, Kronik böbrek yetmezliği, SVO, İnme, Vertigo, "
    "Sistolik, Diastolik, EKG, Antikoagülan, NOAK, INR, aPTT, Trombositopeni."
)


def get_groq_response_from_text(clinical_text: str) -> dict:
    """
    Groq API'ye serbest klinik metni gönderir ve yapılandırılmış JSON döndürür.
    llama-3.3-70b-versatile modelini kullanır.
    """
    from groq import Groq

    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)

    user_prompt = f"""Aşağıdaki klinik metni analiz et ve hasta bilgilerini JSON formatında çıkar:

---
{clinical_text}
---

Sadece JSON döndür, başka hiçbir şey yazma."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    
    try:
        result = json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        result = {}
    
    return result


def get_groq_response_from_audio(audio_bytes: bytes) -> dict:
    """
    Groq API'ye ses kaydını gönderir ve yapılandırılmış JSON döndürür.
    İki aşamalı işlem: Önce whisper-large-v3-turbo ile sesi metne çevirir (STT),
    sonra elde edilen metni get_groq_response_from_text fonksiyonuna gönderir.
    """
    from groq import Groq

    api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=api_key)

    # Aşama 1: Ses kaydını metne çevir (STT) - Medikal terim ipuçları ile
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "audio.wav"
    
    transcription_response = client.audio.transcriptions.create(
        file=audio_file,
        model="whisper-large-v3-turbo",
        language="tr",
        prompt=WHISPER_MEDICAL_PROMPT,
        response_format="text"
    )
    transcribed_text = transcription_response

    # Aşama 2: Elde edilen metni JSON formatına dönüştür
    result = get_groq_response_from_text(transcribed_text)
    return result


def apply_ai_data_to_session(ai_result: dict):
    """
    AI'dan dönen JSON verisini session_state'e uygular.
    Sadece null olmayan (None olmayan) değerleri günceller.
    """
    # ===== HASTA KİMLİĞİ VE ZAMANLAMA =====
    
    # Ad Soyad
    if ai_result.get("hasta_ad_soyad") is not None:
        st.session_state.patient_name = str(ai_result["hasta_ad_soyad"])

    # Yaş
    if ai_result.get("hasta_yas") is not None:
        try:
            val = int(ai_result["hasta_yas"])
            st.session_state.patient_age = max(0, min(val, 120))
        except (ValueError, TypeError):
            pass

    # Cinsiyet
    if ai_result.get("hasta_cinsiyet") is not None:
        cinsiyet = ai_result["hasta_cinsiyet"]
        if cinsiyet in ["Kadın", "Erkek"]:
            st.session_state.patient_gender = cinsiyet

    # Kilo
    if ai_result.get("hasta_kilo") is not None:
        try:
            val = int(ai_result["hasta_kilo"])
            st.session_state.patient_weight = max(1, min(val, 250))
        except (ValueError, TypeError):
            pass

    # Son iyi görülme zamanı
    if ai_result.get("son_iyi_gorulme_zamani") is not None:
        st.session_state.last_well_time_text = str(ai_result["son_iyi_gorulme_zamani"])

    # Semptom başlangıç süresi
    if ai_result.get("semptom_baslangic_suresi") is not None:
        st.session_state.symptom_duration = str(ai_result["semptom_baslangic_suresi"])

    # Şikayet
    if ai_result.get("sikayet") is not None:
        st.session_state.complaint = str(ai_result["sikayet"])

    # Hikaye
    if ai_result.get("hikaye") is not None:
        st.session_state.history = str(ai_result["hikaye"])

    # Kullanılan ilaçlar
    if ai_result.get("kullanilan_ilaclar") is not None:
        st.session_state.medications = str(ai_result["kullanilan_ilaclar"])

    # Özgeçmiş
    if ai_result.get("ozgecmis") is not None:
        st.session_state.medical_history = str(ai_result["ozgecmis"])

    # ===== KRONİK HASTALIKLAR =====
    kronik = ai_result.get("kronik_hastaliklar")
    if kronik and isinstance(kronik, dict):
        # Hipertansiyon
        ht = kronik.get("hipertansiyon")
        if ht and isinstance(ht, dict):
            if ht.get("var_mi") is True:
                st.session_state.ht_check = True
                if ht.get("aciklama"):
                    st.session_state.ht_note = str(ht["aciklama"])
            elif ht.get("var_mi") is False:
                st.session_state.ht_check = False

        # Diyabet
        dm = kronik.get("diyabet")
        if dm and isinstance(dm, dict):
            if dm.get("var_mi") is True:
                st.session_state.dm_check = True
                if dm.get("aciklama"):
                    st.session_state.dm_note = str(dm["aciklama"])
            elif dm.get("var_mi") is False:
                st.session_state.dm_check = False

        # SVO Öyküsü
        svo = kronik.get("svo_oykusu")
        if svo and isinstance(svo, dict):
            if svo.get("var_mi") is True:
                st.session_state.svo_check = True
                if svo.get("aciklama"):
                    st.session_state.svo_note = str(svo["aciklama"])
            elif svo.get("var_mi") is False:
                st.session_state.svo_check = False

        # Malignite
        mal = kronik.get("malignite")
        if mal and isinstance(mal, dict):
            if mal.get("var_mi") is True:
                st.session_state.malignancy_check = True
                if mal.get("aciklama"):
                    st.session_state.malignancy_note = str(mal["aciklama"])
            elif mal.get("var_mi") is False:
                st.session_state.malignancy_check = False

        # KBY
        kby = kronik.get("kby")
        if kby and isinstance(kby, dict):
            if kby.get("var_mi") is True:
                st.session_state.ckd_check = True
                if kby.get("aciklama"):
                    st.session_state.ckd_note = str(kby["aciklama"])
            elif kby.get("var_mi") is False:
                st.session_state.ckd_check = False

        # KAH
        kah = kronik.get("kah")
        if kah and isinstance(kah, dict):
            if kah.get("var_mi") is True:
                st.session_state.cad_check = True
                if kah.get("aciklama"):
                    st.session_state.cad_note = str(kah["aciklama"])
            elif kah.get("var_mi") is False:
                st.session_state.cad_check = False

        # CABG
        cabg = kronik.get("cabg")
        if cabg and isinstance(cabg, dict):
            if cabg.get("var_mi") is True:
                st.session_state.cabg_check = True
                if cabg.get("aciklama"):
                    st.session_state.cabg_note = str(cabg["aciklama"])
            elif cabg.get("var_mi") is False:
                st.session_state.cabg_check = False

        # Diğer
        diger = kronik.get("diger")
        if diger and isinstance(diger, dict):
            if diger.get("var_mi") is True:
                st.session_state.other_chronic_check = True
                if diger.get("hastalik_adi"):
                    st.session_state.other_chronic = str(diger["hastalik_adi"])
                if diger.get("aciklama"):
                    st.session_state.other_chronic_note = str(diger["aciklama"])
            elif diger.get("var_mi") is False:
                st.session_state.other_chronic_check = False

    # ===== VİTAL BULGULAR =====
    
    # Sistolik tansiyon
    if ai_result.get("sistolik_tansiyon") is not None:
        try:
            val = int(ai_result["sistolik_tansiyon"])
            st.session_state.sbp = max(0, min(val, 300))
        except (ValueError, TypeError):
            pass

    # Diyastolik tansiyon
    if ai_result.get("diastolik_tansiyon") is not None:
        try:
            val = int(ai_result["diastolik_tansiyon"])
            st.session_state.dbp = max(0, min(val, 200))
        except (ValueError, TypeError):
            pass

    # Kan şekeri
    if ai_result.get("kan_sekeri") is not None:
        try:
            val = int(ai_result["kan_sekeri"])
            st.session_state.bg = max(0, min(val, 600))
        except (ValueError, TypeError):
            pass

    # EKG Ritmi
    if ai_result.get("ekg_ritmi") is not None:
        ekg = ai_result["ekg_ritmi"]
        ekg_options = ["Sinüs", "Atriyal Fibrilasyon", "Diğer"]
        if ekg in ekg_options:
            st.session_state.ecg_rhythm = ekg

    # ===== NÖROLOJİK MUAYENE =====
    
    # Bilinç durumu
    if ai_result.get("bilinc_durumu") is not None:
        bilinc = ai_result["bilinc_durumu"]
        bilinc_options = ["Açık", "Uykuya Meyilli", "Koma"]
        if bilinc in bilinc_options:
            st.session_state.consciousness = bilinc

    # Oryantasyon
    oryantasyon = ai_result.get("oryantasyon")
    if oryantasyon and isinstance(oryantasyon, dict):
        if oryantasyon.get("zaman") is not None:
            zaman = oryantasyon["zaman"]
            if zaman in ["Doğru", "Yanlış", "Bilmiyor"]:
                st.session_state.orientation_time = zaman
        if oryantasyon.get("yer") is not None:
            yer = oryantasyon["yer"]
            if yer in ["Doğru", "Yanlış", "Bilmiyor"]:
                st.session_state.orientation_place = yer
        if oryantasyon.get("kisi") is not None:
            kisi = oryantasyon["kisi"]
            if kisi in ["Evet", "Hayır", "Kısmen"]:
                st.session_state.orientation_person = kisi

    # Kooperasyon
    if ai_result.get("kooperasyon") is not None:
        koop = ai_result["kooperasyon"]
        koop_options = ["Tam Kooperatif (Her emri yapıyor)", "Kısmen Kooperatif (Bazılarını yapıyor)", "Kooperatif Değil (Yapamıyor)"]
        if koop in koop_options:
            st.session_state.cooperation = koop

    # Konuşma
    if ai_result.get("konusma") is not None:
        konusma = ai_result["konusma"]
        konusma_options = ["Doğal", "Dizartri", "Afazi"]
        if konusma in konusma_options:
            st.session_state.speech = konusma

    # Fasiyal muayene
    if ai_result.get("fasiyal_muayene") is not None:
        fasiyal = ai_result["fasiyal_muayene"]
        fasiyal_options = ["Doğal", "Santral Asimetri", "Periferik Asimetri", "Göz Hareket Kısıtlı"]
        if fasiyal in fasiyal_options:
            st.session_state.facial_exam = fasiyal
    
    if ai_result.get("fasiyal_muayene_aciklama") is not None:
        st.session_state.facial_exam_note = str(ai_result["fasiyal_muayene_aciklama"])

    # Pupiller
    if ai_result.get("pupiller") is not None:
        pupil = ai_result["pupiller"]
        pupil_options = ["İzokorik", "Anizokorik"]
        if pupil in pupil_options:
            st.session_state.pupils = pupil

    # Işık refleksi
    if ai_result.get("isik_refleksi") is not None:
        ir = ai_result["isik_refleksi"]
        ir_options = ["+/+", "+/-", "-/+", "-/-"]
        if ir in ir_options:
            st.session_state.light_reflex = ir

    # Göz hareketleri
    if ai_result.get("goz_hareketleri") is not None:
        goz = ai_result["goz_hareketleri"]
        goz_options = ["Serbest", "Kısıtlı"]
        if goz in goz_options:
            st.session_state.gaze_movement = goz
    
    if ai_result.get("goz_hareketleri_aciklama") is not None:
        st.session_state.gaze_note = str(ai_result["goz_hareketleri_aciklama"])

    # Görme alanı
    if ai_result.get("gorme_alani") is not None:
        gorme = ai_result["gorme_alani"]
        gorme_options = ["Normal", "Hemianopsi", "Hemianopsi+", "Kör"]
        if gorme in gorme_options:
            st.session_state.visual_field = gorme
    
    if ai_result.get("gorme_alani_aciklama") is not None:
        st.session_state.visual_field_note = str(ai_result["gorme_alani_aciklama"])

    # Motor muayene - Sayısal değerler (0-5)
    motor_fields = {
        "motor_sag_kol": "motor_right",
        "motor_sol_kol": "motor_left",
        "motor_sag_bacak": "motor_right_leg",
        "motor_sol_bacak": "motor_left_leg",
    }
    for json_key, session_key in motor_fields.items():
        if ai_result.get(json_key) is not None:
            try:
                val = int(ai_result[json_key])
                if 0 <= val <= 5:
                    st.session_state[session_key] = val
            except (ValueError, TypeError):
                pass

    # Motor açıklamalar
    motor_note_fields = {
        "motor_sag_kol_aciklama": "motor_right_note",
        "motor_sol_kol_aciklama": "motor_left_note",
        "motor_sag_bacak_aciklama": "motor_right_leg_note",
        "motor_sol_bacak_aciklama": "motor_left_leg_note",
    }
    for json_key, session_key in motor_note_fields.items():
        if ai_result.get(json_key) is not None:
            st.session_state[session_key] = str(ai_result[json_key])

    # Serebellar muayene
    if ai_result.get("serebellar_muayene") is not None:
        serebellar = ai_result["serebellar_muayene"]
        serebellar_options = ["Normal", "Dismetri", "Disdiadokokinezi", "Hepsi Normal"]
        if serebellar in serebellar_options:
            st.session_state.cerebellar = serebellar
    
    if ai_result.get("serebellar_aciklama") is not None:
        st.session_state.cerebellar_note = str(ai_result["serebellar_aciklama"])

    # Taban Cilt Refleksi (TCR)
    if ai_result.get("tcr") is not None:
        tcr_val = ai_result["tcr"]
        tcr_options = ["Bilateral Fleksör (Normal)", "Sağ Ekstansör (+)", "Sol Ekstansör (+)", "Lakayt"]
        if tcr_val in tcr_options:
            st.session_state.tcr = tcr_val
    
    if ai_result.get("tcr_aciklama") is not None:
        st.session_state.tcr_note = str(ai_result["tcr_aciklama"])

    # Duyu kaybı
    if ai_result.get("duyu_kaybi") is not None:
        st.session_state.duyu_kaybi = str(ai_result["duyu_kaybi"])

    # Ek bulgular
    if ai_result.get("ek_bulgular") is not None:
        st.session_state.ek_bulgular = str(ai_result["ek_bulgular"])


# ==================== SAYFA YAPILANDIRMASI ====================
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

    .ai-assistant-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px;
        padding: 4px;
        margin-bottom: 24px;
    }

    .ai-assistant-inner {
        background-color: var(--canvas);
        border-radius: 13px;
        padding: 24px;
    }

    .transfer-code-display {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px;
        padding: 32px;
        text-align: center;
        margin: 24px 0;
    }

    .transfer-code-display h1 {
        color: white !important;
        font-size: 64px !important;
        letter-spacing: 12px !important;
        margin: 0 !important;
    }

    .transfer-code-display p {
        color: rgba(255,255,255,0.8);
        font-size: 14px;
        margin-top: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'nihss_score' not in st.session_state:
    st.session_state.nihss_score = 0
if 'aspects_score' not in st.session_state:
    st.session_state.aspects_score = 10
if 'current_time' not in st.session_state:
    st.session_state.current_time = datetime.now() + timedelta(hours=3)
if 'ai_last_result' not in st.session_state:
    st.session_state.ai_last_result = None
if 'ai_transcribed_text' not in st.session_state:
    st.session_state.ai_transcribed_text = None
if 'transfer_code_generated' not in st.session_state:
    st.session_state.transfer_code_generated = None
if 'whatsapp_summary_text' not in st.session_state:
    st.session_state.whatsapp_summary_text = None

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
        ["🧠 Akut İnme", "🌀 Vertigo (HINTS)", "📊 NIHSS Hesaplayıcı", "🧫 ASPECTS Hesaplayıcı", "📤 Vaka Transfer"],
        label_visibility="collapsed"
    )


# ==================== VAKA TRANSFER SAYFASI ====================
if page == "📤 Vaka Transfer":
    st.markdown("# 📤 Vaka Transfer (Handover)")
    st.markdown("---")

    st.markdown("""
    <div class='info-box'>
        <p><strong>ℹ️ Vaka Transfer Sistemi:</strong><br>
        Hasta verilerini güvenli bir şekilde 4 haneli kod ile paylaşın. Veriler <strong>72 saat</strong> sonra otomatik olarak silinir.</p>
    </div>
    """, unsafe_allow_html=True)

    tab_send, tab_receive = st.tabs(["📤 Vaka Gönder", "📥 Vaka Al"])

    # ===== TAB 1: VAKA GÖNDER =====
    with tab_send:
        st.markdown("### 📤 Vaka Gönder")
        st.markdown("Aşağıdaki metin kutusuna handover metnini yapıştırın veya 'Akut İnme' sayfasındaki WhatsApp özetini kullanın.")

        # Eğer WhatsApp özeti session_state'de varsa otomatik doldur
        default_text = st.session_state.get("whatsapp_summary_text", "")

        handover_text = st.text_area(
            "Handover Metni",
            value=default_text,
            height=300,
            placeholder="WhatsApp handover metnini buraya yapıştırın veya 'Akut İnme' sayfasında 'Kaydet ve WhatsApp Özeti Oluştur' butonuna basın...",
            key="handover_text_input"
        )

        col1, col2 = st.columns([1, 3])
        with col1:
            send_button = st.button("🔑 Kod Üret ve Gönder", key="send_handover_btn", use_container_width=True)
        with col2:
            st.markdown("<p style='font-size: 12px; color: #888; padding-top: 12px;'>Veri 72 saat sonra otomatik silinecektir.</p>", unsafe_allow_html=True)

        if send_button:
            if not handover_text or handover_text.strip() == "":
                st.warning("⚠️ Lütfen önce handover metnini girin.")
            else:
                try:
                    with st.spinner("🔄 Firebase'e kaydediliyor ve kod üretiliyor..."):
                        db = init_firebase()
                        code = save_handover(db, handover_text.strip())
                        st.session_state.transfer_code_generated = code

                    st.success("✅ Vaka başarıyla kaydedildi!")

                    st.markdown(f"""
                    <div class='transfer-code-display'>
                        <p>Transfer Kodu</p>
                        <h1>{code}</h1>
                        <p>Bu kodu alıcıya iletin. Kod 72 saat geçerlidir.</p>
                    </div>
                    """, unsafe_allow_html=True)

                    # Kodu kopyalamak için text input
                    st.code(code, language=None)

                except Exception as e:
                    st.error(f"❌ Firebase Hatası: {str(e)}\n\nLütfen Firebase yapılandırmasını kontrol edin.")

        # Daha önce üretilmiş kodu göster
        if st.session_state.transfer_code_generated and not send_button:
            st.markdown(f"""
            <div class='transfer-code-display'>
                <p>Son Üretilen Transfer Kodu</p>
                <h1>{st.session_state.transfer_code_generated}</h1>
                <p>Bu kodu alıcıya iletin. Kod 72 saat geçerlidir.</p>
            </div>
            """, unsafe_allow_html=True)

    # ===== TAB 2: VAKA AL =====
    with tab_receive:
        st.markdown("### 📥 Vaka Al")
        st.markdown("Size iletilen 4 haneli transfer kodunu girerek hasta verisini görüntüleyin.")

        col1, col2 = st.columns([1, 3])
        with col1:
            receive_code = st.text_input(
                "Transfer Kodu",
                max_chars=4,
                placeholder="0000",
                key="receive_code_input",
                help="4 haneli sayısal kodu girin"
            )
        with col2:
            receive_button = st.button("🔍 Vakayı Getir", key="receive_handover_btn", use_container_width=True)

        if receive_button:
            if not receive_code or len(receive_code) != 4 or not receive_code.isdigit():
                st.warning("⚠️ Lütfen geçerli bir 4 haneli kod girin.")
            else:
                try:
                    with st.spinner("🔄 Vaka aranıyor..."):
                        db = init_firebase()
                        result = get_handover(db, receive_code)

                    if result is None:
                        st.error("❌ Bu kodla eşleşen bir vaka bulunamadı. Kodu kontrol edin.")
                    elif result.get("expired"):
                        st.error("⏰ Bu vakanın süresi dolmuş (72 saat). Veri artık erişilemez.")
                    else:
                        st.success("✅ Vaka bulundu!")

                        # Erişim bilgisi
                        access_count = result.get("access_count", 0)
                        created_at = result.get("created_at")
                        if created_at and hasattr(created_at, 'strftime'):
                            created_str = created_at.strftime("%d.%m.%Y %H:%M")
                        elif created_at and hasattr(created_at, 'seconds'):
                            created_str = datetime.utcfromtimestamp(created_at.seconds).strftime("%d.%m.%Y %H:%M")
                        else:
                            created_str = "-"

                        st.markdown(f"""
                        <div class='info-box'>
                            <p><strong>📋 Vaka Bilgisi:</strong><br>
                            Oluşturulma: {created_str} UTC | Erişim Sayısı: {access_count + 1}</p>
                        </div>
                        """, unsafe_allow_html=True)

                        # Handover metnini göster
                        summary = result.get("summary_text", "")
                        st.markdown(f"""
                        <div class='whatsapp-output'>
{summary}
                        </div>
                        """, unsafe_allow_html=True)

                        # Kopyalanabilir metin
                        st.code(summary, language=None)

                except Exception as e:
                    st.error(f"❌ Firebase Hatası: {str(e)}\n\nLütfen bağlantınızı kontrol edin.")


# ==================== NIHSS HESAPLAYICI SAYFASI ====================
elif page == "📊 NIHSS Hesaplayıcı":
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
        consciousness_1a = st.radio("1a - Bilinç Seviyesi", ["Alert (0)", "Drowsy (1)", "Stupor (2)", "Coma (3)"], horizontal=True, index=0, key="nihss_1a")
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
        q1 = st.radio("Ay - Yaş", ["İkisi de doğru (0)", "Bir doğru (1)", "Hiçbiri doğru (2)"], horizontal=True, index=0, key="nihss_1b_q1")
    with col2:
        q2 = st.radio("Ay - Yer", ["İkisi de doğru (0)", "Bir doğru (1)", "Hiçbiri doğru (2)"], horizontal=True, index=0, key="nihss_1b_q2")

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

    commands = st.radio("Aç/Kapat gözleri", ["İkisi de yapar (0)", "Bir yapar (1)", "Hiçbiri yapmaz (2)"], horizontal=True, index=0, key="nihss_1c")

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

    gaze = st.radio("Göz Bakışları", ["Normal (0)", "Paralizi var (1)", "Deviasyon var (2)"], horizontal=True, index=0, key="nihss_2")

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

    visual = st.radio("Görme Alanı", ["Normal (0)", "Hemianopsi (1)", "Hemianopsi+ (2)", "Kör (3)"], horizontal=True, index=0, key="nihss_3")

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

    facial = st.radio("Fasiyal Paresi", ["Normal (0)", "Hafif (1)", "Paralizi (2)", "Tam (3)"], horizontal=True, index=0, key="nihss_4")

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

    left_arm = st.radio("Sol Kol", ["Normal (0)", "Hafif (1)", "Orta (2)", "Ağır (3)", "Tam (4)"], horizontal=True, index=0, key="nihss_5a")

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

    right_arm = st.radio("Sağ Kol", ["Normal (0)", "Hafif (1)", "Orta (2)", "Ağır (3)", "Tam (4)"], horizontal=True, index=0, key="nihss_5b")

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

    left_leg = st.radio("Sol Bacak", ["Normal (0)", "Hafif (1)", "Orta (2)", "Ağır (3)", "Tam (4)"], horizontal=True, index=0, key="nihss_6a")

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

    right_leg = st.radio("Sağ Bacak", ["Normal (0)", "Hafif (1)", "Orta (2)", "Ağır (3)", "Tam (4)"], horizontal=True, index=0, key="nihss_6b")

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

    ataxia = st.radio("Ataksi", ["Yok (0)", "Bir ekstremite (1)", "İki ekstremite (2)"], horizontal=True, index=0, key="nihss_7")

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

    sensory = st.radio("Duyu", ["Normal (0)", "Hafif/moderat (1)", "Şiddetli (2)"], horizontal=True, index=0, key="nihss_8")

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

    language = st.radio("Dil/Afazi", ["Normal (0)", "Hafif (1)", "Ağır (2)", "Mute/Total (3)"], horizontal=True, index=0, key="nihss_9")

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

    dysarthria = st.radio("Dizartri", ["Normal (0)", "Hafif (1)", "Ağır (2)"], horizontal=True, index=0, key="nihss_10")

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

    neglect = st.radio("İhmal", ["Yok (0)", "Bir duyuda (1)", "İki duyuda (2)"], horizontal=True, index=0, key="nihss_11")

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
        BT'de erken iskemi bulgularını değerlendirmek için kullanılan puanlama sistemi. Maksimum puan 10.</p>
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

    # ==================== AI ASISTAN BÖLÜMÜ ====================
    with st.expander("🤖 AI Asistan - Otomatik Form Doldurma", expanded=False):
        st.markdown("""
        <div class='info-box'>
            <p><strong>💡 Kullanım:</strong> Hasta bilgilerini aşağıdaki sekmelerden birini kullanarak girin. 
            Klavye/dikte ile yazın ya da doğrudan ses kaydederek AI'nın formu otomatik doldurmasını sağlayın.<br>
            <strong>⚠️ Önemli:</strong> AI sadece sizin söylediğiniz/yazdığınız bilgileri çıkarır, hiçbir veriyi uydurmaz.</p>
        </div>
        """, unsafe_allow_html=True)

        tab_text, tab_audio = st.tabs(["✍️ Klavye / Dikte ile Yaz", "🎙️ Doğrudan Ses Kaydet"])

        with tab_text:
            clinical_text = st.text_area("Klinik Metin", height=150, placeholder="Örnek: 72 yaşında erkek hasta, 80 kilo, bilinç açık, tansiyonu 180/100...", key="ai_clinical_text")
            col_btn1, col_btn2 = st.columns([1, 3])
            with col_btn1:
                ai_text_submit = st.button("🚀 Metinden Formu Doldur", key="ai_text_submit_btn", use_container_width=True)
            with col_btn2:
                st.markdown("<p style='font-size: 12px; color: #888; padding-top: 12px;'>Llama 3.3 70B (Groq) ile analiz edilecektir.</p>", unsafe_allow_html=True)

            if ai_text_submit:
                if not clinical_text or clinical_text.strip() == "":
                    st.warning("⚠️ Lütfen önce klinik metni girin.")
                else:
                    try:
                        with st.spinner("🔄 AI metni analiz ediyor..."):
                            ai_result = get_groq_response_from_text(clinical_text)
                            st.session_state.ai_last_result = ai_result
                            apply_ai_data_to_session(ai_result)
                        st.success("✅ Form başarıyla dolduruldu!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Hata: {str(e)}")

        with tab_audio:
            st.markdown("<p style='font-size: 14px; color: #555;'>Mikrofon butonuna basın, muayene bulgularını söyleyin ve kaydı durdurun.</p>", unsafe_allow_html=True)
            audio_value = st.audio_input("🎙️ Ses kaydı yapın", key="ai_audio_input")
            col_btn1, col_btn2 = st.columns([1, 3])
            with col_btn1:
                ai_audio_submit = st.button("🚀 Sesi Analiz Et ve Formu Doldur", key="ai_audio_submit_btn", use_container_width=True)
            with col_btn2:
                st.markdown("<p style='font-size: 12px; color: #888; padding-top: 12px;'>Whisper + Llama 3.3 70B (Groq) ile analiz edilecektir.</p>", unsafe_allow_html=True)

            if ai_audio_submit:
                if audio_value is None:
                    st.warning("⚠️ Lütfen önce bir ses kaydı yapın.")
                else:
                    try:
                        with st.spinner("🔄 AI ses kaydını analiz ediyor..."):
                            audio_bytes = audio_value.read()
                            ai_result = get_groq_response_from_audio(audio_bytes)
                            st.session_state.ai_last_result = ai_result
                            apply_ai_data_to_session(ai_result)
                        st.success("✅ Ses kaydı analiz edildi ve form dolduruldu!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Hata: {str(e)}")

        if st.session_state.ai_last_result:
            with st.expander("🔍 Son AI Çıktısı (JSON)", expanded=False):
                st.json(st.session_state.ai_last_result)

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
            last_well_time_text = st.text_input("Son İyi Görülme (dün, 2 gün önce vb.)", "", key="last_well_time_text")
            last_well_time = st.time_input("Son İyi Görülme Saati", datetime.now().time(), key="last_well_time")
        with col2:
            if st.button("🕐 Şu Anki Saati Al", key="get_current_time"):
                st.session_state.current_time = datetime.now() + timedelta(hours=3)
            st.info(f"Kayıt Saati: {st.session_state.current_time.strftime('%H:%M')}")
        with col3:
            symptom_duration = st.text_input("Süre (dakika/saat)", "", key="symptom_duration")

        col1, col2 = st.columns(2)
        with col1:
            complaint = st.text_area("Şikayet", "", key="complaint")
        with col2:
            history = st.text_area("Hikaye", "", key="history")

        st.markdown("---")
        st.markdown("### 💊 Kullanılan İlaçlar")
        medications = st.text_area("Kullanılan İlaçlar", "", key="medications")

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
                ht_note = st.text_input("Açıklama", "", key="ht_note")
        with col2:
            dm_check = st.checkbox("Diabetes Mellitus (DM)", key="dm_check")
            if dm_check:
                col2a, col2b = st.columns(2)
                with col2a:
                    dm_duration = st.number_input("Süre (sayı)", 0, 100, 0, key="dm_duration")
                with col2b:
                    dm_unit = st.selectbox("Birim", ["Ay", "Yıl"], key="dm_unit")
                dm_note = st.text_input("Açıklama", "", key="dm_note")
        with col3:
            svo_check = st.checkbox("SVO (İnme Öyküsü)", key="svo_check")
            if svo_check:
                col3a, col3b = st.columns(2)
                with col3a:
                    svo_duration = st.number_input("Süre (sayı)", 0, 100, 0, key="svo_duration")
                with col3b:
                    svo_unit = st.selectbox("Birim", ["Ay", "Yıl"], key="svo_unit")
                svo_note = st.text_input("Açıklama", "", key="svo_note")

        col1, col2 = st.columns(2)
        with col1:
            malignancy_check = st.checkbox("Malignite", key="malignancy_check")
            if malignancy_check:
                col1a, col1b = st.columns(2)
                with col1a:
                    malignancy_duration = st.number_input("Süre (sayı)", 0, 100, 0, key="malignancy_duration")
                with col1b:
                    malignancy_unit = st.selectbox("Birim", ["Ay", "Yıl"], key="malignancy_unit")
                malignancy_note = st.text_input("Açıklama", "", key="malignancy_note")
        with col2:
            ckd_check = st.checkbox("Kronik Böbrek Yetmezliği (KBY)", key="ckd_check")
            if ckd_check:
                col2a, col2b = st.columns(2)
                with col2a:
                    ckd_duration = st.number_input("Süre (sayı)", 0, 100, 0, key="ckd_duration")
                with col2b:
                    ckd_unit = st.selectbox("Birim", ["Ay", "Yıl"], key="ckd_unit")
                ckd_note = st.text_input("Açıklama", "", key="ckd_note")

        col1, col2 = st.columns(2)
        with col1:
            cad_check = st.checkbox("Koroner Arter Hastalığı (KAH)", key="cad_check")
            if cad_check:
                col1a, col1b = st.columns(2)
                with col1a:
                    cad_duration = st.number_input("Süre (sayı)", 0, 100, 0, key="cad_duration")
                with col1b:
                    cad_unit = st.selectbox("Birim", ["Ay", "Yıl"], key="cad_unit")
                cad_note = st.text_input("Açıklama", "", key="cad_note")
        with col2:
            cabg_check = st.checkbox("CABG (Kalp Bypass)", key="cabg_check")
            if cabg_check:
                col2a, col2b = st.columns(2)
                with col2a:
                    cabg_duration = st.number_input("Süre (sayı)", 0, 100, 0, key="cabg_duration")
                with col2b:
                    cabg_unit = st.selectbox("Birim", ["Ay", "Yıl"], key="cabg_unit")
                cabg_note = st.text_input("Açıklama", "", key="cabg_note")

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
                other_chronic_note = st.text_input("Açıklama", "", key="other_chronic_note")

        st.markdown("---")
        st.markdown("### 📋 Özgeçmiş")
        medical_history = st.text_area("Detaylı Özgeçmiş", "", key="medical_history")

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
        nihss_input = st.number_input("NIHSS Skoru (0-42)", 0, 42, int(st.session_state.nihss_score), key="nihss_input")
        st.info(f"💡 NIHSS Hesaplayıcı'dan gelen skor: {st.session_state.nihss_score}")
    with col2:
        aspects_input = st.number_input("ASPECTS Skoru (0-10)", 0, 10, int(st.session_state.aspects_score), key="aspects_input")
        st.info(f"💡 ASPECTS Hesaplayıcı'dan gelen skor: {st.session_state.aspects_score}")

    if aspects_input < 7:
        st.error("🚨 ASPECTS < 7! Büyük infarkt riski. TPA kontrendike olabilir!")

    st.markdown("### 💉 TPA Doz Hesaplayıcı")
    if weight > 0:
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

    # NÖROLOJİK MUAYENE
    st.markdown("## 🔬 AÇIKLAMALI NÖROLOJİK MUAYENE")

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
        consciousness = st.radio("Bilinç Durumu", ["Açık", "Uykuya Meyilli", "Koma"], horizontal=True, index=0, key="consciousness", label_visibility="collapsed")
    with col2:
        consciousness_note = st.text_input("Ek Açıklama", "", key="consciousness_note")

    st.markdown("#### 📍 Oryantasyon Soruları")
    col1, col2, col3 = st.columns(3)
    with col1:
        orientation_time = st.radio("Zaman (Ay/Yıl)", ["Doğru", "Yanlış", "Bilmiyor"], horizontal=True, index=0, key="orientation_time")
    with col2:
        orientation_place = st.radio("Yer (Neresi)", ["Doğru", "Yanlış", "Bilmiyor"], horizontal=True, index=0, key="orientation_place")
    with col3:
        orientation_person = st.radio("Kişi (Kendini tanıyor mu)", ["Evet", "Hayır", "Kısmen"], horizontal=True, index=0, key="orientation_person")

    st.markdown("#### 🤝 Kooperasyon ve Emirlere Uygunluk")
    col1, col2 = st.columns([3, 2])
    with col1:
        cooperation = st.radio("Kooperasyon/Emirler", ["Tam Kooperatif (Her emri yapıyor)", "Kısmen Kooperatif (Bazılarını yapıyor)", "Kooperatif Değil (Yapamıyor)"], horizontal=True, index=0, key="cooperation", label_visibility="collapsed")
    with col2:
        cooperation_note = st.text_input("Ek Açıklama", "", key="cooperation_note", help="Örn: Gözlerini aç/kapat, dişlerini göster vb.")

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
        speech = st.radio("Konuşma Durumu", ["Doğal", "Dizartri", "Afazi"], horizontal=True, index=0, key="speech", label_visibility="collapsed")
    with col2:
        speech_note = st.text_input("Ek Açıklama", "", key="speech_note")

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
        facial_exam = st.radio("Fasiyal Muayene", ["Doğal", "Santral Asimetri", "Periferik Asimetri", "Göz Hareket Kısıtlı"], horizontal=True, index=0, key="facial_exam", label_visibility="collapsed")
    with col2:
        facial_exam_note = st.text_input("Ek Açıklama", "", key="facial_exam_note")

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
        pupils = st.radio("Pupiller", ["İzokorik", "Anizokorik"], horizontal=True, index=0, key="pupils", label_visibility="collapsed")
    with col2:
        light_reflex = st.radio("Işık Refleksi (IR)", ["+/+", "+/-", "-/+", "-/-"], horizontal=True, index=0, key="light_reflex", label_visibility="collapsed")
    with col3:
        pupils_note = st.text_input("Ek Açıklama", "", key="pupils_note")

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
        gaze_movement = st.radio("Göz Hareketleri (GH)", ["Serbest", "Kısıtlı"], horizontal=True, index=0, key="gaze_movement", label_visibility="collapsed")
    with col2:
        gaze_note = st.text_input("Ek Açıklama", "", key="gaze_note")

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
        visual_field = st.radio("Görme Alanı", ["Normal", "Hemianopsi", "Hemianopsi+", "Kör"], horizontal=True, index=0, key="visual_field", label_visibility="collapsed")
    with col2:
        visual_field_note = st.text_input("Ek Açıklama", "", key="visual_field_note")

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
            motor_right = st.radio("Sağ Üst Ekstremite", [5, 4, 3, 2, 1, 0], horizontal=True, index=0, key="motor_right", label_visibility="collapsed")
        with col1b:
            motor_right_note = st.text_input("Ek Açıklama", "", key="motor_right_note")
        col1a, col1b = st.columns([3, 2])
        with col1a:
            motor_left = st.radio("Sol Üst Ekstremite", [5, 4, 3, 2, 1, 0], horizontal=True, index=0, key="motor_left", label_visibility="collapsed")
        with col1b:
            motor_left_note = st.text_input("Ek Açıklama", "", key="motor_left_note")
    with col2:
        col2a, col2b = st.columns([3, 2])
        with col2a:
            motor_right_leg = st.radio("Sağ Alt Ekstremite", [5, 4, 3, 2, 1, 0], horizontal=True, index=0, key="motor_right_leg", label_visibility="collapsed")
        with col2b:
            motor_right_leg_note = st.text_input("Ek Açıklama", "", key="motor_right_leg_note")
        col2a, col2b = st.columns([3, 2])
        with col2a:
            motor_left_leg = st.radio("Sol Alt Ekstremite", [5, 4, 3, 2, 1, 0], horizontal=True, index=0, key="motor_left_leg", label_visibility="collapsed")
        with col2b:
            motor_left_leg_note = st.text_input("Ek Açıklama", "", key="motor_left_leg_note")

    st.markdown("### 🏃 Serebellar Muayene")
    with st.expander("ℹ️ Açıklama"):
        st.markdown("""
        **Serebellar muayene:** Beyincikğin kontrol ettiği denge, koordinasyon ve hareket ölçülülüğünü test eder.
        
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
        cerebellar = st.radio("Serebellar Muayene", ["Normal", "Dismetri", "Disdiadokokinezi", "Hepsi Normal"], horizontal=True, index=0, key="cerebellar", label_visibility="collapsed")
    with col2:
        cerebellar_note = st.text_input("Ek Açıklama", "", key="cerebellar_note")

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
        tcr = st.radio("Taban Cilt Refleksi", ["Bilateral Fleksör (Normal)", "Sağ Ekstansör (+)", "Sol Ekstansör (+)", "Lakayt"], horizontal=True, index=0, key="tcr", label_visibility="collapsed")
    with col2:
        tcr_note = st.text_input("Ek Açıklama", "", key="tcr_note")

    st.markdown("---")

    # WHATSAPP HANDOVER
    st.markdown("## 📱 WhatsApp Handover")

    if st.button("💾 Kaydet ve WhatsApp Özeti Oluştur", key="whatsapp_button"):
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")

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

        chronic_diseases = []
        if ht_check:
            note_str = f" - {ht_note}" if 'ht_note' in dir() and ht_note else ""
            chronic_diseases.append(f"HT ({st.session_state.get('ht_duration', 0)} {st.session_state.get('ht_unit', 'Yıl')}){note_str}")
        if dm_check:
            note_str = f" - {dm_note}" if 'dm_note' in dir() and dm_note else ""
            chronic_diseases.append(f"DM ({st.session_state.get('dm_duration', 0)} {st.session_state.get('dm_unit', 'Yıl')}){note_str}")
        if svo_check:
            note_str = f" - {svo_note}" if 'svo_note' in dir() and svo_note else ""
            chronic_diseases.append(f"SVO ({st.session_state.get('svo_duration', 0)} {st.session_state.get('svo_unit', 'Yıl')}){note_str}")
        if malignancy_check:
            note_str = f" - {malignancy_note}" if 'malignancy_note' in dir() and malignancy_note else ""
            chronic_diseases.append(f"Malignite ({st.session_state.get('malignancy_duration', 0)} {st.session_state.get('malignancy_unit', 'Yıl')}){note_str}")
        if ckd_check:
            note_str = f" - {ckd_note}" if 'ckd_note' in dir() and ckd_note else ""
            chronic_diseases.append(f"KBY ({st.session_state.get('ckd_duration', 0)} {st.session_state.get('ckd_unit', 'Yıl')}){note_str}")
        if cad_check:
            note_str = f" - {cad_note}" if 'cad_note' in dir() and cad_note else ""
            chronic_diseases.append(f"KAH ({st.session_state.get('cad_duration', 0)} {st.session_state.get('cad_unit', 'Yıl')}){note_str}")
        if cabg_check:
            note_str = f" - {cabg_note}" if 'cabg_note' in dir() and cabg_note else ""
            chronic_diseases.append(f"CABG ({st.session_state.get('cabg_duration', 0)} {st.session_state.get('cabg_unit', 'Yıl')}){note_str}")
        if other_chronic_check:
            note_str = f" - {other_chronic_note}" if 'other_chronic_note' in dir() and other_chronic_note else ""
            chronic_diseases.append(f"{st.session_state.get('other_chronic', 'Diğer')} ({st.session_state.get('other_chronic_duration', 0)} {st.session_state.get('other_chronic_unit', 'Yıl')}){note_str}")

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

💉 *TPA KARARI:*
• {tpa_decision}{tpa_reasons}
        """.strip()

        # WhatsApp özetini session_state'e kaydet (Vaka Transfer için)
        st.session_state.whatsapp_summary_text = whatsapp_summary

        st.markdown(f"""
        <div class='whatsapp-output'>
        {whatsapp_summary}
        </div>
        """, unsafe_allow_html=True)

        st.code(whatsapp_summary, language=None)
        st.info("💡 Bu özeti '📤 Vaka Transfer' sayfasından 4 haneli kod ile paylaşabilirsiniz.")

# ==================== VERTIGO SAYFASI ====================
elif page == "🌀 Vertigo (HINTS)":
    st.markdown("# 🌀 Vertigo ve Baş Dönmesi (HINTS Muayenesi)")
    st.markdown("---")

    st.markdown("## 📋 Vertigo Öyküsü ve Vitaller")
    col1, col2, col3 = st.columns(3)
    with col1:
        vertigo_onset = st.selectbox("Şikayet Başlangıcı", ["Ani (Saniyeler)", "Dakikalar/Saatler", "Günler"], key="vertigo_onset")
    with col2:
        vertigo_trigger = st.selectbox("Tetikleyici", ["Baş hareketiyle artıyor", "Sürekli/Spontan"], key="vertigo_trigger")
    with col3:
        vertigo_duration = st.text_input("Süre", "", key="vertigo_duration")

    st.markdown("### Eşlik Eden Bulgular")
    accompanying_symptoms = st.multiselect("Eşlik Eden Bulgular", ["Bulantı/Kusma", "İşitme Kaybı / Tinnitus", "Şiddetli Baş/Ense Ağrısı (Kırmızı Bayrak!)", "Görme Bozukluğu/Çift Görme (Kırmızı Bayrak!)"], key="accompanying_symptoms", label_visibility="collapsed")

    st.markdown("---")
    st.markdown("## 🔬 HINTS + Plus Muayenesi")

    st.markdown("### 1. Head Impulse Test (vHIT)")
    head_impulse = st.radio("Head Impulse Testi", ["Anormal / Gözden Kaçırma Var (Periferik Lehine)", "Normal (Santral İnme Lehine!)"], horizontal=True, key="head_impulse", label_visibility="collapsed")

    st.markdown("### 2. Nystagmus")
    nystagmus = st.radio("Nistagmus", ["Tek Yönlü Yatay (Periferik)", "Yön Değiştiren / Vertikal (Santral İnme!)", "Yok"], horizontal=True, key="nystagmus", label_visibility="collapsed")

    st.markdown("### 3. Test of Skew (Göz Kayması)")
    test_skew = st.radio("Test of Skew", ["Yok (Normal)", "Var / Vertikal Kayma (Santral İnme!)"], horizontal=True, key="test_skew", label_visibility="collapsed")

    st.markdown("### 4. Yeni İşitme Kaybı (Plus)")
    hearing_loss = st.radio("İşitme Kaybı", ["Yok", "Var (AICA İnmesi şüphesi)"], horizontal=True, key="hearing_loss", label_visibility="collapsed")

    st.markdown("---")
    st.markdown("## 🔄 Pozisyonel Test (BPPV için)")
    dix_hallpike = st.selectbox("Dix-Hallpike Testi", ["Yapılmadı", "Negatif", "Sağ BPPV (Nistagmus +)", "Sol BPPV (Nistagmus +)"], key="dix_hallpike")

    st.markdown("---")
    st.markdown("## 🎯 Karar Destek ve Çıktı")

    has_severe_headache = "Şiddetli Baş/Ense Ağrısı (Kırmızı Bayrak!)" in accompanying_symptoms
    has_visual_disturbance = "Görme Bozukluğu/Çift Görme (Kırmızı Bayrak!)" in accompanying_symptoms
    has_central_nystagmus = "Yön Değiştiren / Vertikal (Santral İnme!)" in nystagmus
    has_central_skew = "Var / Vertikal Kayma (Santral İnme!)" in test_skew
    has_normal_head_impulse = "Normal (Santral İnme Lehine!)" in head_impulse
    has_hearing_loss = "Var (AICA İnmesi şüphesi)" in hearing_loss

    central_risk = (has_severe_headache or has_visual_disturbance or has_central_nystagmus or has_central_skew or has_normal_head_impulse or has_hearing_loss)

    if central_risk:
        st.markdown("""
        <div class='alert-danger'>
            <h2>🚨 DİKKAT: SANTRAL VERTİGO / İNME ŞÜPHESİ!</h2>
            <p><strong>Arka sistem (Posterior Sirkülasyon) inmesi olabilir.</strong></p>
            <p>MR ve Nöroloji Konsültasyonu planlayın!</p>
        </div>
        """, unsafe_allow_html=True)

        risk_factors = []
        if has_severe_headache: risk_factors.append("✓ Şiddetli Baş/Ense Ağrısı")
        if has_visual_disturbance: risk_factors.append("✓ Görme Bozukluğu/Çift Görme")
        if has_central_nystagmus: risk_factors.append("✓ Santral Nistagmus")
        if has_central_skew: risk_factors.append("✓ Pozitif Test of Skew")
        if has_normal_head_impulse: risk_factors.append("✓ Normal Head Impulse")
        if has_hearing_loss: risk_factors.append("✓ Yeni İşitme Kaybı (AICA)")
        for factor in risk_factors:
            st.markdown(f"- {factor}")
    else:
        st.markdown("""
        <div class='alert-success'>
            <h2>✅ Periferik Vertigo ile Uyumlu Bulgular</h2>
            <p>Santral inme bulgusu yok. İç kulak kaynaklı vertigo düşünülmeli.</p>
        </div>
        """, unsafe_allow_html=True)

    if "BPPV" in dix_hallpike:
        st.info(f"🔄 {dix_hallpike} - BPPV tanısı ile uyumlu. Epley manevrası düşünülmeli.")

    st.markdown("---")
    st.markdown("## 📱 Vertigo WhatsApp Özeti")

    if st.button("💾 Vertigo WhatsApp Özeti Oluştur", key="vertigo_whatsapp"):
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")
        risk_status = "🚨 SANTRAL VERTİGO / İNME ŞÜPHESİ" if central_risk else "✅ Periferik Vertigo"

        risk_factors = []
        if has_severe_headache: risk_factors.append("✓ Şiddetli Baş/Ense Ağrısı")
        if has_visual_disturbance: risk_factors.append("✓ Görme Bozukluğu/Çift Görme")
        if has_central_nystagmus: risk_factors.append("✓ Santral Nistagmus")
        if has_central_skew: risk_factors.append("✓ Pozitif Test of Skew")
        if has_normal_head_impulse: risk_factors.append("✓ Normal Head Impulse")
        if has_hearing_loss: risk_factors.append("✓ Yeni İşitme Kaybı (AICA)")

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
    <p style='font-size: 12px; margin-top: 8px;'>Akut İnme ve Vertigo Karar Destek Sistemi v3.0 (AI + Firebase Destekli)</p>
</div>
""", unsafe_allow_html=True)
