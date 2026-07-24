import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, timedelta
import datetime
import calendar
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import io 

# --- SAYFA AYARLARI (En üstte olmalıdır) ---
st.set_page_config(page_title="Turizm Fakültesi İzin Takip", layout="wide")

# --- GİZLİ KASA AYARLARI (MAİL VE GİRİŞ ŞİFRELERİ) ---
try:
    GONDERICI_MAIL = st.secrets["GONDERICI_MAIL"]
    GONDERICI_SIFRE = st.secrets["GONDERICI_SIFRE"]
    ADMIN_USER = st.secrets["ADMIN_USER"]
    ADMIN_PASS = st.secrets["ADMIN_PASS"]
except:
    GONDERICI_MAIL = "mail_yok" 
    GONDERICI_SIFRE = "sifre_yok" 
    ADMIN_USER = "admin"
    ADMIN_PASS = "12345"

# --- 1. AYARLAR: HOCALAR, BÖLÜMLER VE MAİL LİSTESİ ---
fakulte_verileri = {
    "Turizm Rehberliği": [
        "Prof. Dr. Bekir Bora DEDEOĞLU", "Prof. Dr. İbrahim YILMAZ", "Doç. Dr. Zeynep ÇOKAL", 
        "Doç. Dr. Ömer ÇOBAN", "Doç. Dr. İbrahim Akın ÖZEN", "Doç. Dr. Koray ÇAMLICA", 
        "Doç. Dr. Meral DURSUN KÜÇÜKOĞLU", "Dr. Öğr. Üyesi Nurgül ÇALIŞKAN", 
        "Dr. Öğr. Üyesi Meral BÜYÜKKURU", "Öğr. Gör. Hülya CEYLAN", "Öğr. Gör. Filiz YÜKSEL", 
        "Arş. Gör. Dr. Aybüke ÖZSOY", "Arş. Gör. Filiz DALKILIÇ", "Arş. Gör. Büşra YAMANGİL"
    ],
    "Gastronomi ve Mutfak Sanatları": [
        "Prof. Dr. Nilüfer ŞAHİN", "Prof. Dr. Lütfi BUYRUK", "Doç. Dr. İbrahim İLHAN", 
        "Doç. Dr. Emine KALE", "Doç. Dr. Emrah KESKİN", "Doç. Dr. Günay EROL", 
        "Dr. Öğr. Üyesi Firdevs YÖNET EREN", "Dr. Öğr. Üyesi Durmuş Ali AYDEMİR", 
        "Öğr. Gör. Kader PARLAK", "Öğr. Gör. İnci İLLEEZ", "Arş. Gör. Sinem DİKME GÜL"
    ],
    "Turizm İşletmeciliği": [
        "Prof. Dr. Şule AYDIN", "Doç. Dr. Duygu EREN", "Doç. Dr. Şule ARDIÇ YETİŞ", 
        "Doç. Dr. Ebru GÜNEREN", "Doç. Dr. Burcu Gülsevil BELBER", "Doç. Dr. Eda ÖZGÜL KATLAV", 
        "Doç. Dr. Ozan ATSIZ", "Doç. Dr. Gaye DENİZ", "Dr. Öğr. Üyesi Gamze ÇOBAN YILDIZ", 
        "Dr. Öğr. Üyesi Neşe YILMAZ", "Dr. Öğr. Üyesi Lokman DİNÇ", "Dr. Öğr. Üyesi Onur Şevket YILDIZ", 
        "Arş. Gör. Dr. Meral AKYÜZ", "Arş. Gör. Rümeysa UNAT"
    ]
}

yonetim_bilgileri = {
    "Turizm Rehberliği": {
        "baskan_adi": "Prof. Dr. Bekir Bora DEDEOĞLU",
        "eposta": "nurgulcaliskan@nevsehir.edu.tr" 
    },
    "Gastronomi ve Mutfak Sanatları": {
        "baskan_adi": "Doç. Dr. Günay EROL",
        "eposta": "gunayerol@nevsehir.edu.tr" 
    },
    "Turizm İşletmeciliği": {
        "baskan_adi": "Doç. Dr. Duygu EREN",
        "eposta": "deren@nevsehir.edu.tr" 
    },
    "Dekanlik": {
        "baskan_adi": "Prof. Dr. Bekir Bora DEDEOĞLU",
        "eposta": "b.bora.dedeoglu@nevsehir.edu.tr"
    }
}

renk_paleti = ["#E74C3C", "#8E44AD", "#2980B9", "#27AE60", "#F39C12", "#D35400", "#16A085", "#34495E", "#E67E22", "#9B59B6", "#1ABC9C", "#3498DB", "#C0392B", "#2C3E50", "#F1C40F"]
hoca_renkleri = {}
renk_indeksi = 0
for hocalar in fakulte_verileri.values():
    for hoca in hocalar:
        hoca_renkleri[hoca] = renk_paleti[renk_indeksi % len(renk_paleti)]
        renk_indeksi += 1

# --- 2. VERİTABANI BAĞLANTISI ---
conn = sqlite3.connect('izinler.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS izin_tablosu (id INTEGER PRIMARY KEY AUTOINCREMENT, hoca_adi TEXT, bolum TEXT, baslangic TEXT, bitis TEXT, gun_sayisi INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS izin_tablosu_yedek (id INTEGER PRIMARY KEY, hoca_adi TEXT, bolum TEXT, baslangic TEXT, bitis TEXT, gun_sayisi INTEGER)''')
conn.commit()

# --- 3. YARDIMCI FONKSİYONLAR ---
def takvim_html_olustur(yil, ay, secili_bolum):
    df = pd.read_sql_query("SELECT * FROM izin_tablosu", conn)
    gunluk_izinler = {}
    for _, row in df.iterrows():
        start = datetime.datetime.strptime(row['baslangic'], "%Y-%m-%d").date()
        end = datetime.datetime.strptime(row['bitis'], "%Y-%m-%d").date()
        delta = end - start
        for i in range(delta.days + 1):
            gun = start + timedelta(days=i)
            if gun not in gunluk_izinler: gunluk_izinler[gun] = []
            if (row['hoca_adi'], row['bolum']) not in gunluk_izinler[gun]:
                gunluk_izinler[gun].append((row['hoca_adi'], row['bolum']))

    cal = calendar.Calendar(firstweekday=0)
    ay_gunleri = cal.monthdatescalendar(yil, ay)
    aylar_isim = {1:"Ocak", 2:"Şubat", 3:"Mart", 4:"Nisan", 5:"Mayıs", 6:"Haziran", 7:"Temmuz", 8:"Ağustos", 9:"Eylül", 10:"Ekim", 11:"Kasım", 12:"Aralık"}
    
    html_kodu = f"<h3 style='font-family: Arial; margin-bottom:5px; color:#2c3e50;'>{secili_bolum} - {aylar_isim[ay]} {yil}</h3>"
    html_kodu += "<table style='width:100%; border-collapse: collapse; font-family: Arial; font-size: 12px; table-layout: fixed;'>"
    html_kodu += "<tr style='background-color: #f0f2f6;'><th style='border:1px solid #ddd; padding:5px;'>Pzt</th><th style='border:1px solid #ddd; padding:5px;'>Sal</th><th style='border:1px solid #ddd; padding:5px;'>Çar</th><th style='border:1px solid #ddd; padding:5px;'>Per</th><th style='border:1px solid #ddd; padding:5px;'>Cum</th><th style='border:1px solid #ddd; padding:5px;'>Cmt</th><th style='border:1px solid #ddd; padding:5px;'>Paz</th></tr>"
    
    for hafta in ay_gunleri:
        html_kodu += "<tr>"
        for gun in hafta:
            if gun.month == ay:
                izindekiler = gunluk_izinler.get(gun, [])
                hucre = f"<div style='font-weight:bold; color:#555;'>{gun.day}</div>"
                for hoca, blm in izindekiler:
                    if secili_bolum == "Tüm Fakülte" or secili_bolum == blm:
                        renk = hoca_renkleri.get(hoca, "#000")
                        hucre += f"<div style='background-color:{renk}; color:white; padding:3px; margin-top:2px; border-radius:3px; font-size:10px;'>{hoca}</div>"
                html_kodu += f"<td style='border:1px solid #ddd; padding:5px; vertical-align:top; height:80px;'>{hucre}</td>"
            else:
                html_kodu += "<td style='border:1px solid #ddd; background-color:#fafafa;'></td>"
        html_kodu += "</tr>"
    html_kodu += "</table>"
    return html_kodu

def eposta_gonder(alici_eposta, konu, html_icerik):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = konu
    msg["From"] = GONDERICI_MAIL
    msg["To"] = alici_eposta
    part = MIMEText(html_icerik, "html")
    msg.attach(part)
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(GONDERICI_MAIL, GONDERICI_SIFRE)
        server.sendmail(GONDERICI_MAIL, alici_eposta, msg.as_string())
        server.quit()
        return "BASARILI"
    except Exception as e:
        return str(e)


# --- 4. GÜVENLİK VE GÖRÜNÜM AYARLARI ---
if "giris_yapildi" not in st.session_state:
    st.session_state["giris_yapildi"] = False

# =========================================================================
# 🔴 MİSAFİR (HERKESE AÇIK) EKRAN (GİRİŞ YAPILMAMIŞSA)
# =========================================================================
if not st.session_state["giris_yapildi"]:
    st.title("🌴 Turizm Fakültesi İzin Takip Sistemi")
    st.info("👁️ Şu an **Misafir Modundasınız**. Sistemdeki güncel izinleri görüntüleyebilirsiniz. Veri girişi için yetkili girişi yapınız.")
    
    pub_sekme1, pub_sekme2 = st.tabs(["📅 Takvim Görüntüle", "🔐 Yetkili Girişi"])
    
    # 1. SEKME: SADECE TAKVİM GÖRÜNTÜLEME
    with pub_sekme1:
        aylar = {1:"Ocak", 2:"Şubat", 3:"Mart", 4:"Nisan", 5:"Mayıs", 6:"Haziran", 7:"Temmuz", 8:"Ağustos", 9:"Eylül", 10:"Ekim", 11:"Kasım", 12:"Aralık"}
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            secilen_ay_isim = st.selectbox("Görüntülenecek Ay", list(aylar.values()), index=date.today().month-1, key="pub_ay")
            secilen_ay = [k for k, v in aylar.items() if v == secilen_ay_isim][0]
        with f_col2: 
            secilen_yil = st.selectbox("Yıl", [2026, 2027, 2028, 2029, 2030], index=0, key="pub_yil")
        with f_col3: 
            filtre_bolum = st.selectbox("Takvimi Görüntülenecek Bölüm", ["Tüm Fakülte"] + list(fakulte_verileri.keys()), key="pub_bolum")
            
        ekran_takvimi = takvim_html_olustur(secilen_yil, secilen_ay, filtre_bolum)
        st.markdown(ekran_takvimi, unsafe_allow_html=True)
        
    # 2. SEKME: YETKİLİ GİRİŞ EKRANI
    with pub_sekme2:
        bos1, orta, bos2 = st.columns([1, 1, 1])
        with orta:
            st.markdown("<h3 style='text-align: center;'>Yönetici Girişi</h3>", unsafe_allow_html=True)
            with st.form("login_form"):
                kullanici_adi = st.text_input("Kullanıcı Adı")
                sifre = st.text_input("Şifre", type="password")
                giris_butonu = st.form_submit_button("Giriş Yap", use_container_width=True)
                
                if giris_butonu:
                    if kullanici_adi == ADMIN_USER and sifre == ADMIN_PASS:
                        st.session_state["giris_yapildi"] = True
                        st.rerun()
                    else:
                        st.error("Kullanıcı adı veya şifre hatalı!")


# =========================================================================
# 🟢 YÖNETİCİ EKRANI (GİRİŞ YAPILMIŞSA) - (SİZİN ANA SİSTEMİNİZ)
# =========================================================================
else:
    # Sol Menü (Çıkış Butonu)
    with st.sidebar:
        st.title("👨‍💼 Yönetici Paneli")
        st.write(f"Aktif Kullanıcı: **{ADMIN_USER}**")
        if st.button("🚪 Güvenli Çıkış Yap"):
            st.session_state["giris_yapildi"] = False
            st.rerun()

    # --- ANA ARAYÜZ (4 SEKME) ---
    st.title("🌴 Turizm Fakültesi İzin Takip Sistemi")
    sekme1, sekme2, sekme3, sekme4 = st.tabs(["📝 İzin Formu", "📅 Aylık Takvim", "✉️ E-Posta Bildirimleri", "⚙️ Veri & Yedek Yönetimi"])

    # --- SEKME 1: İZİN FORMU ---
    with sekme1:
        st.subheader("Yeni İzin Talebi Oluştur")
        secilen_bolum = st.selectbox("Lütfen Bölüm Seçiniz", list(fakulte_verileri.keys()))
        secilen_hoca = st.selectbox("Öğretim Üyesini Seçiniz", fakulte_verileri[secilen_bolum])
        col1, col2 = st.columns(2)
        with col1: baslangic_tarihi = st.date_input("İzin Başlangıç Tarihi", min_value=date.today())
        with col2: bitis_tarihi = st.date_input("İzin Bitiş Tarihi", min_value=baslangic_tarihi)
        
        if st.button("İzni Sisteme Kaydet", type="primary"):
            fark = bitis_tarihi - baslangic_tarihi
            gun_sayisi = fark.days + 1
            c.execute('''INSERT INTO izin_tablosu (hoca_adi, bolum, baslangic, bitis, gun_sayisi) VALUES (?, ?, ?, ?, ?)''', (secilen_hoca, secilen_bolum, baslangic_tarihi, bitis_tarihi, gun_sayisi))
            conn.commit()
            st.success(f"✅ {secilen_hoca} için {gun_sayisi} günlük izin başarıyla kaydedildi.")

    # --- SEKME 2: AYLIK TAKVİM ---
    with sekme2:
        aylar = {1:"Ocak", 2:"Şubat", 3:"Mart", 4:"Nisan", 5:"Mayıs", 6:"Haziran", 7:"Temmuz", 8:"Ağustos", 9:"Eylül", 10:"Ekim", 11:"Kasım", 12:"Aralık"}
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            secilen_ay_isim = st.selectbox("Görüntülenecek Ay", list(aylar.values()), index=date.today().month-1, key="goruntu_ay")
            secilen_ay = [k for k, v in aylar.items() if v == secilen_ay_isim][0]
        with f_col2: 
            secilen_yil = st.selectbox("Yıl", [2026, 2027, 2028, 2029, 2030], index=0, key="goruntu_yil")
        with f_col3: 
            filtre_bolum = st.selectbox("Takvimi Görüntülenecek Bölüm", ["Tüm Fakülte"] + list(fakulte_verileri.keys()), key="goruntu_bolum")
        ekran_takvimi = takvim_html_olustur(secilen_yil, secilen_ay, filtre_bolum)
        st.markdown(ekran_takvimi, unsafe_allow_html=True)

    # --- SEKME 3: OTOMATİK 3 AYLIK E-POSTA BİLDİRİMİ ---
    with sekme3:
        st.subheader("Yöneticilere Güncel Takvimleri İlet")
        su_an = date.today()
        aylar_yillar = []
        for i in range(3):
            m = su_an.month + i
            y = su_an.year
            if m > 12:
                m -= 12
                y += 1
            aylar_yillar.append((m, y))
        aylar_sozluk = {1:"Ocak", 2:"Şubat", 3:"Mart", 4:"Nisan", 5:"Mayıs", 6:"Haziran", 7:"Temmuz", 8:"Ağustos", 9:"Eylül", 10:"Ekim", 11:"Kasım", 12:"Aralık"}
        hesaplanan_ay_isimleri = [f"{aylar_sozluk[m]} {y}" for m, y in aylar_yillar]
        st.info(f"ℹ️ Aşağıdaki butona bastığınızda; **{', '.join(hesapl
