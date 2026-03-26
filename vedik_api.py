from flask import Flask, request, jsonify
import swisseph as swe
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
import traceback
import os

app = Flask(__name__)

# --- VERİLER VE SÖZLÜKLER ---
BURCLAR = ["Mesha (Koc)", "Vrishabha (Boga)", "Mithuna (Ikizler)", "Karka (Yengec)", "Simha (Aslan)", "Kanya (Basak)", "Tula (Terazi)", "Vrishchika (Akrep)", "Dhanus (Yay)", "Makara (Oglak)", "Kumbha (Kova)", "Meena (Balik)"]
BURC_KISA = ["Ar","Ta","Ge","Cn","Le","Vi","Li","Sc","Sg","Cp","Aq","Pi"]
GEZEGEN_LISTESI = [(swe.SUN, "Gunes", "Su"), (swe.MOON, "Ay", "Mo"), (swe.MARS, "Mars", "Ma"), (swe.MERCURY, "Merkur", "Me"), (swe.JUPITER, "Jupiter", "Ju"), (swe.VENUS, "Venus", "Ve"), (swe.SATURN, "Saturn", "Sa"), (swe.TRUE_NODE, "Rahu", "Ra")]
NAKSHATRALAR = [("Ashwini","Ke"),("Bharani","Ve"),("Krittika","Su"),("Rohini","Mo"),("Mrigashira","Ma"),("Ardra","Ra"),("Punarvasu","Ju"),("Pushya","Sa"),("Ashlesha","Me"),("Magha","Ke"),("Purva Phalguni","Ve"),("Uttara Phalguni","Su"),("Hasta","Mo"),("Chitra","Ma"),("Swati","Ra"),("Vishakha","Ju"),("Anuradha","Sa"),("Jyeshtha","Me"),("Mula","Ke"),("Purva Ashadha","Ve"),("Uttara Ashadha","Su"),("Shravana","Mo"),("Dhanishtha","Ma"),("Shatabhisha","Ra"),("Purva Bhadrapada","Ju"),("Uttara Bhadrapada","Sa"),("Revati","Me")]
DASHA_SIRASI = [("Ketu","Ke",7),("Shukra","Ve",20),("Surya","Su",6),("Chandra","Mo",10),("Mangala","Ma",7),("Rahu","Ra",18),("Guru","Ju",16),("Shani","Sa",19),("Budha","Me",17)]
LAGNA_SAHIPLERI = {0:"Ma",1:"Ve",2:"Me",3:"Mo",4:"Su",5:"Me",6:"Ve",7:"Ma",8:"Ju",9:"Sa",10:"Sa",11:"Ju"}
GEZ_ADI = {"Su":"Gunes","Mo":"Ay","Ma":"Mars","Me":"Merkur","Ju":"Jupiter","Ve":"Venus","Sa":"Saturn","Ra":"Rahu","Ke":"Ketu"}
GUCLER = {"Su":{"uchcha":0,"neecha":6,"own":[4]},"Mo":{"uchcha":1,"neecha":7,"own":[3]},"Ma":{"uchcha":9,"neecha":3,"own":[0,7]},"Me":{"uchcha":5,"neecha":11,"own":[2,5]},"Ju":{"uchcha":3,"neecha":9,"own":[8,11]},"Ve":{"uchcha":11,"neecha":5,"own":[1,6]},"Sa":{"uchcha":6,"neecha":0,"own":[9,10]},"Ra":{"uchcha":1,"neecha":7,"own":[]},"Ke":{"uchcha":7,"neecha":1,"own":[]}}

# --- HESAPLAMA MOTORU ---
def koordinat_al(sehir):
    geolocator = Nominatim(user_agent="vedik_api_test", timeout=10)
    location = geolocator.geocode(sehir)
    if not location: raise ValueError("Sehir bulunamadi: " + sehir)
    return location.latitude, location.longitude

def julian_gun(tarih_str, saat_str, utc_offset):
    dt = datetime.strptime(tarih_str + " " + saat_str, "%Y-%m-%d %H:%M")
    utc_dt = dt - timedelta(hours=utc_offset)
    return swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute / 60.0)

def derece_fmt(ekl):
    ekl %= 360
    d = int(ekl % 30)
    m = int(((ekl % 30) - d) * 60)
    return f"{d}d {m:02d}'"

def burc_bilgi(ekl):
    no = int((ekl % 360) / 30)
    return {"no": no, "ad": BURCLAR[no], "kisa": BURC_KISA[no], "derece": derece_fmt(ekl), "tam": round(ekl, 4)}

def nak_bilgi(ekl):
    ekl %= 360
    no = min(int(ekl / (360.0/27)), 26)
    pada = int((ekl % (360.0/27)) / (360.0/27/4)) + 1
    return {"ad": NAKSHATRALAR[no][0], "pada": pada, "sahip": NAKSHATRALAR[no][1]}

def hesapla(tarih, saat, sehir, utc_offset=3):
    lat, lon = koordinat_al(sehir)
    jd = julian_gun(tarih, saat, utc_offset)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    _, ascmc = swe.houses(jd, lat, lon, b'W')
    lagna_ekl = (ascmc[0] - swe.get_ayanamsa_ut(jd)) % 360
    lagna = burc_bilgi(lagna_ekl)
    gezegenler = {}
    for gez_id, ad, kisa in GEZEGEN_LISTESI:
        pos, hiz = swe.calc_ut(jd, gez_id, swe.FLG_SIDEREAL)
        ekl = pos[0] % 360
        b, n = burc_bilgi(ekl), nak_bilgi(ekl)
        gezegenler[kisa] = {"ad": ad, "burc": b["ad"], "derece": b["derece"], "ev": int(((ekl - lagna_ekl) % 360) / 30) + 1, "nakshatra": n["ad"]}
    return {"lagna": lagna, "gezegenler": gezegenler}

def liste_olustur(veri, girdi):
    l, g = veri["lagna"], veri["gezegenler"]
    s = [f"{'='*50}", f" VEDIK HARITA: {girdi['sehir'].upper()}", f"{'='*50}", f" LAGNA: {l['ad']} {l['derece']}"]
    s.append(f"\n {'Gezegen':<10} {'Burc':<15} {'Ev':<5} {'Derece'}")
    s.append("-" * 50)
    for k, gz in g.items():
        s.append(f" {gz['ad']:<10} {gz['burc']:<15} {gz['ev']:<5} {gz['derece']}")
    return "\n".join(s)

# --- YOLLAR ---
@app.route("/")
def ana_sayfa(): return "API Aktif. Lutfen /saglik veya /harita yollarini kullanin."

@app.route("/saglik")
def saglik(): return jsonify({"durum": "aktif", "mesaj": "Railway baglantisi tamam"})

@app.route("/harita/liste", methods=["POST"])
def harita_liste():
    try:
        data = request.get_json()
        veri = hesapla(data["tarih"], data["saat"], data["sehir"], data.get("utc_offset", 3))
        return liste_olustur(veri, data), 200, {"Content-Type": "text/plain; charset=utf-8"}
    except Exception as e: return f"Hata: {str(e)}", 500

if __name__ == "__main__":
    # Railway'in verdigi portu zorunlu kılıyoruz
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
