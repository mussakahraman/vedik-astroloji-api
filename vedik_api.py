from flask import Flask, request, jsonify
import swisseph as swe
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
import traceback
import os

app = Flask(__name__)

# --- SABİT VERİLER ---
BURCLAR = ["Mesha (Koc)", "Vrishabha (Boga)", "Mithuna (Ikizler)", "Karka (Yengec)", "Simha (Aslan)", "Kanya (Basak)", "Tula (Terazi)", "Vrishchika (Akrep)", "Dhanus (Yay)", "Makara (Oglak)", "Kumbha (Kova)", "Meena (Balik)"]
BURC_KISA = ["Ar","Ta","Ge","Cn","Le","Vi","Li","Sc","Sg","Cp","Aq","Pi"]
GEZEGEN_LISTESI = [(swe.SUN, "Gunes", "Su"), (swe.MOON, "Ay", "Mo"), (swe.MARS, "Mars", "Ma"), (swe.MERCURY, "Merkur", "Me"), (swe.JUPITER, "Jupiter", "Ju"), (swe.VENUS, "Venus", "Ve"), (swe.SATURN, "Saturn", "Sa"), (swe.TRUE_NODE, "Rahu", "Ra")]
NAKSHATRALAR = [("Ashwini","Ke"),("Bharani","Ve"),("Krittika","Su"),("Rohini","Mo"),("Mrigashira","Ma"),("Ardra","Ra"),("Punarvasu","Ju"),("Pushya","Sa"),("Ashlesha","Me"),("Magha","Ke"),("Purva Phalguni","Ve"),("Uttara Phalguni","Su"),("Hasta","Mo"),("Chitra","Ma"),("Swati","Ra"),("Vishakha","Ju"),("Anuradha","Sa"),("Jyeshtha","Me"),("Mula","Ke"),("Purva Ashadha","Ve"),("Uttara Ashadha","Su"),("Shravana","Mo"),("Dhanishtha","Ma"),("Shatabhisha","Ra"),("Purva Bhadrapada","Ju"),("Uttara Bhadrapada","Sa"),("Revati","Me")]
DASHA_SIRASI = [("Ketu","Ke",7),("Shukra","Ve",20),("Surya","Su",6),("Chandra","Mo",10),("Mangala","Ma",7),("Rahu","Ra",18),("Guru","Ju",16),("Shani","Sa",19),("Budha","Me",17)]
LAGNA_SAHIPLERI = {0:"Ma",1:"Ve",2:"Me",3:"Mo",4:"Su",5:"Me",6:"Ve",7:"Ma",8:"Ju",9:"Sa",10:"Sa",11:"Ju"}
GEZ_ADI = {"Su":"Gunes","Mo":"Ay","Ma":"Mars","Me":"Merkur","Ju":"Jupiter","Ve":"Venus","Sa":"Saturn","Ra":"Rahu","Ke":"Ketu"}
GUCLER = {"Su":{"uchcha":0,"neecha":6,"own":[4]},"Mo":{"uchcha":1,"neecha":7,"own":[3]},"Ma":{"uchcha":9,"neecha":3,"own":[0,7]},"Me":{"uchcha":5,"neecha":11,"own":[2,5]},"Ju":{"uchcha":3,"neecha":9,"own":[8,11]},"Ve":{"uchcha":11,"neecha":5,"own":[1,6]},"Sa":{"uchcha":6,"neecha":0,"own":[9,10]},"Ra":{"uchcha":1,"neecha":7,"own":[]},"Ke":{"uchcha":7,"neecha":1,"own":[]}}

# --- HESAPLAMA FONKSİYONLARI ---
def koordinat_al(sehir):
    geolocator = Nominatim(user_agent="vedik_api_v3", timeout=15)
    location = geolocator.geocode(sehir)
    if not location: raise ValueError(f"Sehir bulunamadi: {sehir}")
    return location.latitude, location.longitude

def julian_gun(tarih_str, saat_str, utc_offset):
    # ISO format kontrolü
    dt = datetime.strptime(f"{tarih_str} {saat_str}", "%Y-%m-%d %H:%M")
    utc_dt = dt - timedelta(hours=float(utc_offset))
    return swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute / 60.0)

def derece_fmt(ekl):
    ekl %= 360
    d = int(ekl % 30)
    m = int(((ekl % 30) - d) * 60)
    s = int(((((ekl % 30) - d) * 60) - m) * 60)
    return f"{d}d {m:02d}' {s:02d}\""

def burc_bilgi(ekl):
    no = int((ekl % 360) / 30)
    return {"no": no, "ad": BURCLAR[no], "kisa": BURC_KISA[no], "derece": derece_fmt(ekl), "tam": round(ekl, 4)}

def nak_bilgi(ekl):
    ekl %= 360
    no = min(int(ekl / (360.0/27)), 26)
    pada = int((ekl % (360.0/27)) / (360.0/27/4)) + 1
    return {"ad": NAKSHATRALAR[no][0], "pada": pada, "sahip": NAKSHATRALAR[no][1], "no": no}

def guc_str(kisa, burc_no):
    g = GUCLER.get(kisa, {})
    if burc_no == g.get("uchcha"): return "Uchcha"
    if burc_no == g.get("neecha"): return "Neecha"
    if burc_no in g.get("own", []): return "Swakshetra"
    return "-"

def hesapla(tarih, saat, sehir, utc_offset=3):
    lat, lon = koordinat_al(sehir)
    jd = julian_gun(tarih, saat, utc_offset)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    
    _, ascmc = swe.houses(jd, lat, lon, b'W')
    ayan = swe.get_ayanamsa_ut(jd)
    lagna_ekl = (ascmc[0] - ayan) % 360
    lagna = burc_bilgi(lagna_ekl)
    
    gezegenler = {}
    ay_ekl = 0
    for gez_id, ad, kisa in GEZEGEN_LISTESI:
        pos, hiz = swe.calc_ut(jd, gez_id, swe.FLG_SIDEREAL)
        ekl = pos[0] % 360
        b, n = burc_bilgi(ekl), nak_bilgi(ekl)
        retro = bool(hiz[3] < 0)
        gezegenler[kisa] = {
            "ad": ad, "burc": b["ad"], "derece": b["derece"], "ev": int(((ekl - lagna_ekl) % 360) / 30) + 1,
            "nakshatra": n["ad"], "pada": n["pada"], "guc": guc_str(kisa, b["no"]), "retro": "R" if retro else "-"
        }
        if kisa == "Mo": ay_ekl = ekl

    # Rahu/Ketu Aksı
    rahu_ekl = (swe.calc_ut(jd, swe.TRUE_NODE, swe.FLG_SIDEREAL)[0][0]) % 360
    ketu_ekl = (rahu_ekl + 180) % 360
    kb, kn = burc_bilgi(ketu_ekl), nak_bilgi(ketu_ekl)
    gezegenler["Ke"] = {
        "ad": "Ketu", "burc": kb["ad"], "derece": kb["derece"], "ev": int(((ketu_ekl - lagna_ekl) % 360) / 30) + 1,
        "nakshatra": kn["ad"], "pada": kn["pada"], "guc": guc_str("Ke", kb["no"]), "retro": "-"
    }
    
    return {"lagna": lagna, "gezegenler": gezegenler, "koordinat": {"lat": round(lat, 2), "lon": round(lon, 2)}}

def liste_olustur(veri, girdi):
    l, g = veri["lagna"], veri["gezegenler"]
    s = ["="*65, "  VEDIK ASTROLOJI ANALIZI", "="*65]
    s.append(f"  YER: {girdi['sehir'].upper()} | TARIH: {girdi['tarih']} | SAAT: {girdi['saat']}")
    s.append(f"  LAGNA: {l['ad']} ({l['derece']})")
    s.append("-" * 65)
    s.append(f"  {'Gezegen':<10} {'Burc':<16} {'Ev':<4} {'Derece':<12} {'Nakshatra':<12} {'R'}")
    s.append("-" * 65)
    for k in ["Su","Mo","Ma","Me","Ju","Ve","Sa","Ra","Ke"]:
        gz = g[k]
        s.append(f"  {gz['ad']:<10} {gz['burc']:<16} {gz['ev']:<4} {gz['derece']:<12} {gz['nakshatra']:<12} {gz['retro']}")
    s.append("="*65)
    return "\n".join(s)

# --- FLASK YOLLARI ---
@app.route("/")
def index(): return "Vedik API v3 Calisiyor. /saglik adresini kontrol edin."

@app.route("/saglik")
def saglik(): return jsonify({"durum": "aktif", "mesaj": "Sistem Bulutla El Sikisti", "zaman": datetime.now().isoformat()})

@app.route("/harita/liste", methods=["POST"])
def harita_liste():
    try:
        data = request.get_json(force=True)
        if not data: return "Hata: JSON verisi bulunamadi", 400
        veri = hesapla(data["tarih"], data["saat"], data["sehir"], data.get("utc_offset", 3))
        return liste_olustur(veri, data), 200, {"Content-Type": "text/plain; charset=utf-8"}
    except Exception as e:
        return f"Sistem Hatasi: {str(e)}\n{traceback.format_exc()}", 500

if __name__ == "__main__":
    # Railway ve Render için dinamik port yakalama
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
