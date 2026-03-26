from flask import Flask, request, jsonify
import swisseph as swe
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
import traceback
import os
import math

app = Flask(__name__)

# --- SABİT VERİLER (TEKNİK TABLO İÇİN) ---
BURCLAR = ["Mesha (Koc)", "Vrishabha (Boga)", "Mithuna (Ikizler)", "Karka (Yengec)", "Simha (Aslan)", "Kanya (Basak)", "Tula (Terazi)", "Vrishchika (Akrep)", "Dhanus (Yay)", "Makara (Oglak)", "Kumbha (Kova)", "Meena (Balik)"]
BURC_KISA = ["Ar", "Ta", "Ge", "Cn", "Le", "Vi", "Li", "Sc", "Sg", "Cp", "Aq", "Pi"]
GEZEGEN_LISTESI = [
    (swe.SUN, "Gunes", "Su"), (swe.MOON, "Ay", "Mo"), (swe.MARS, "Mars", "Ma"),
    (swe.MERCURY, "Merkur", "Me"), (swe.JUPITER, "Jupiter", "Ju"), (swe.VENUS, "Venus", "Ve"),
    (swe.SATURN, "Saturn", "Sa")
]
NAKSHATRALAR = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishtha", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]

# Chara Karaka sıralaması (Görseldeki BK, DK vb. için)
KARAKALAR = ["AK", "AmK", "BK", "MK", "PK", "GK", "DK"]

# --- HESAPLAMA FONKSİYONLARI ---

# 1. Navamsa (D-9) Burcunu Hesaplama (Matematiksel)
def navamsa_burcu_hesapla(ekl_derece):
    ekl_derece %= 360
    r_burc_no = int(ekl_derece / 30)
    derece_burc = ekl_derece % 30
    navamsa_no = int(derece_burc / (30.0/9.0))
    
    # Navamsa burcunun hesaplanması (Ateş, Toprak, Hava, Su üçlemelerine göre)
    nav_burc_no = 0
    if r_burc_no in [0, 4, 8]:   # Ateş (Koç, Aslan, Yay) -> Koç'tan başlar
        nav_burc_no = (0 + navamsa_no) % 12
    elif r_burc_no in [1, 5, 9]: # Toprak (Boğa, Başak, Oğlak) -> Oğlak'tan başlar
        nav_burc_no = (9 + navamsa_no) % 12
    elif r_burc_no in [2, 6, 10]: # Hava (İkizler, Terazi, Kova) -> Terazi'den başlar
        nav_burc_no = (6 + navamsa_no) % 12
    elif r_burc_no in [3, 7, 11]: # Su (Yengeç, Akrep, Balık) -> Yengeç'ten başlar
        nav_burc_no = (3 + navamsa_no) % 12
    return nav_burc_no

def koordinat_al(sehir):
    geolocator = Nominatim(user_agent="vedik_api_final_jagannatha_v1", timeout=15)
    location = geolocator.geocode(sehir)
    if not location: raise ValueError(f"Sehir bulunamadi: {sehir}")
    return location.latitude, location.longitude

def julian_gun(tarih_str, saat_str, utc_offset):
    # saniyeyi de dahil ettik: HH:MM:SS
    dt = datetime.strptime(f"{tarih_str} {saat_str}", "%Y-%m-%d %H:%M:%S")
    utc_dt = dt - timedelta(hours=float(utc_offset))
    return swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0)

def derece_fmt_tam(ekl):
    ekl %= 360
    d = int(ekl)
    m = int((ekl - d) * 60)
    s = int((((ekl - d) * 60) - m) * 60)
    return f"{d:02d} {m:02d}' {s:02d}\""

def derece_fmt_burc(ekl):
    # Burç içindeki dereceyi gösterir (Görseldeki "Longitude" sütunu)
    d_burc = ekl % 30
    d = int(d_burc)
    m = int((d_burc - d) * 60)
    s = int((((d_burc - d) * 60) - m) * 60)
    return f"{d:02d} {BURC_KISA[int(ekl/30)]} {m:02d}' {s:02d}\""

def nak_bilgi_tam(ekl):
    ekl %= 360
    # 27 Nakshatra var, her biri 13 derece 20 dakika (400 dakika)
    total_minutes = ekl * 60.0
    nak_minutes = total_minutes % (360.0 * 60.0 / 27.0)
    
    # Nakshatra numarası (0-26)
    nak_no = int(total_minutes / (360.0 * 60.0 / 27.0))
    # Pada numarası (1-4) (400 dakika / 4 = 100 dakika)
    pada = int(nak_minutes / 100.0) + 1
    
    # Güvenlik kontrolü (360 dereceRevati'nin sonuna denk gelirse)
    if nak_no >= 27: nak_no = 26; pada = 4
    
    return {"ad": NAKSHATRALAR[nak_no], "pada": pada}

def hesapla_jagannatha(tarih, saat, sehir, utc_offset=3):
    # Saniyeli saati kontrol et
    if len(saat.split(':')) == 2: saat += ":00" # HH:MM ise HH:MM:00 yap

    lat, lon = koordinat_al(sehir)
    jd = julian_gun(tarih, saat, utc_offset)
    swe.set_sid_mode(swe.SIDM_LAHIRI) # Lahiri Ayanamsa (Standart)
    ayan = swe.get_ayanamsa_ut(jd)
    
    _, ascmc = swe.houses(jd, lat, lon, b'W')
    lagna_ekl = (ascmc[0] - ayan) % 360
    
    res = {"body": []}
    
    # Lagna Bilgisi
    l_nak = nak_bilgi_tam(lagna_ekl)
    res["body"].append({
        "Body": "Lagna",
        "Longitude": derece_fmt_tam(lagna_ekl),
        "Nakshatra": l_nak["ad"],
        "Pada": str(l_nak["pada"]),
        "Rasi": BURC_KISA[int(lagna_ekl/30)],
        "Navamsa": BURC_KISA[navamsa_burcu_hesapla(lagna_ekl)],
        "GezD": "" # Lagna Chara Karaka değildir
    })
    
    gez_hesaplar = [] # Karaka sıralaması için derece ve kısaltmaları saklayacağız

    # 7 Gezegen Hesaplaması
    for gez_id, ad, kisa in GEZEGEN_LISTESI:
        pos, hiz = swe.calc_ut(jd, gez_id, swe.FLG_SIDEREAL)
        ekl = pos[0] % 360
        g_nak = nak_bilgi_tam(ekl)
        retro = hiz[3] < 0 # Hız negatifse retrograd
        
        gez_hesaplar.append({"kisa": kisa, "ekl": ekl, "retro": retro})
        
        # Karaka henüz belli değil, placeholder koyuyoruz
        body_str = f"{ad} {'(R)' if retro else ''}".strip()
        
        res["body"].append({
            "Body": body_str,
            "Longitude": derece_fmt_tam(ekl),
            "Nakshatra": g_nak["ad"],
            "Pada": str(g_nak["pada"]),
            "Rasi": BURC_KISA[int(ekl/30)],
            "Navamsa": BURC_KISA[navamsa_burcu_hesapla(ekl)],
            "GezD": "" # Placeholder
        })

    # Rahu ve Ketu (Chara Karaka değiller)
    rahu_pos, _ = swe.calc_ut(jd, swe.TRUE_NODE, swe.FLG_SIDEREAL)
    rahu_ekl = rahu_pos[0] % 360
    r_nak = nak_bilgi_tam(rahu_ekl)
    res["body"].append({
        "Body": "Rahu", "Longitude": derece_fmt_tam(rahu_ekl), "Nakshatra": r_nak["ad"], "Pada": str(r_nak["pada"]),
        "Rasi": BURC_KISA[int(rahu_ekl/30)], "Navamsa": BURC_KISA[navamsa_burcu_hesapla(rahu_ekl)], "GezD": ""
    })
    
    # Ketu (Tam 180 derece zıt)
    ketu_ekl = (rahu_ekl + 180) % 360
    k_nak = nak_bilgi_tam(ketu_ekl)
    res["body"].append({
        "Body": "Ketu", "Longitude": derece_fmt_tam(ketu_ekl), "Nakshatra": k_nak["ad"], "Pada": str(k_nak["pada"]),
        "Rasi": BURC_KISA[int(ketu_ekl/30)], "Navamsa": BURC_KISA[navamsa_burcu_hesapla(ketu_ekl)], "GezD": ""
    })

    # Chara Karaka Hesaplaması (Dereceye göre sıralama: AK -> DK)
    # Sadece 7 gezegen için (Rahu/Ketu hariç)
    # AK (En yüksek derece), DK (En düşük derece)
    
    # Gezegenleri derecelerine göre sırala (Büyükten küçüğe)
    # Burada derecenin tam hali değil, 30 dereceye göre modülü alınmış hali kullanılır.
    # Görseldeki BK, DK vb. için bu gereklidir.
    for g in gez_hesaplar: g['deg_in_sign'] = g['ekl'] % 30
    gez_sirali = sorted(gez_hesaplar, key=lambda x: x['deg_in_sign'], reverse=True)
    
    # Karaka kısaltmalarını ekle
    karaka_map = {}
    for i, karaka in enumerate(KARAKALAR):
        if i < len(gez_sirali):
            karaka_map[gez_sirali[i]['kisa']] = karaka

    # Chara Karaka'yı "Body" sütununa ekleyelim (Görseldeki "Sun - BK" formatı)
    for b in res["body"]:
        gez_kisa = b['Body'].split()[0][:2] # Gunes -> Gu
        # Eğer varsa Chara Karaka'yı ekle
        if gez_kisa in karaka_map:
             b['Body'] += f" - {karaka_map[gez_kisa]}"

    return res

def tablo_olustur_v2(veri, girdi):
    res = [f" VEDIK ANALIZ: {girdi['sehir'].upper()} | TARIH: {girdi['tarih']} | SAAT: {girdi['saat']}", "="*80]
    
    # Tablo Başlıkları (Jagannatha Hora Simülasyonu)
    header = f"{'Body':<15} {'Longitude':<15} {'Nakshatra':<15} {'Pada':<5} {'Rasi':<5} {'Navamsa':<5}"
    res.append(header)
    res.append("-" * 80)
    
    # Verileri ekle
    for b in veri["body"]:
        row = f"{b['Body']:<15} {b['Longitude']:<15} {b['Nakshatra']:<15} {b['Pada']:<5} {b['Rasi']:<5} {b['Navamsa']:<5}"
        res.append(row)
        
    return "\n".join(res)

# --- YOLLAR ---
@app.route("/")
def index(): return "Vedik API JHora SimCalisiyor."

@app.route("/saglik")
def saglik(): return jsonify({"status": "ok", "msg": "Jagannatha Hora Engine is Live"})

@app.route("/harita/liste", methods=["POST"])
def harita_liste():
    try:
        data = request.get_json(force=True)
        # Saniyeli saati al: HH:MM:SS
        saat = data.get("saat")
        if len(saat.split(':')) == 2: saat += ":00" # HH:MM ise HH:MM:00 yap
        
        veri = hesapla_jagannatha(data["tarih"], saat, data["sehir"], data.get("utc_offset", 3))
        
        # Tablo çıktısı (text/plain formatında)
        return tablo_olustur_v2(veri, data), 200, {"Content-Type": "text/plain; charset=utf-8"}
        
    except Exception as e:
        return f"Kod Hatasi (technical details):\n{traceback.format_exc()}\n\n{str(e)}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
