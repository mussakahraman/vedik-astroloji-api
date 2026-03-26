from flask import Flask, request, jsonify
import swisseph as swe
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
import traceback
import os

app = Flask(__name__)

# --- SÖZLÜKLER VE VERİLER ---
BURCLAR = ["Mesha (Koc)", "Vrishabha (Boga)", "Mithuna (Ikizler)", "Karka (Yengec)", "Simha (Aslan)", "Kanya (Basak)", "Tula (Terazi)", "Vrishchika (Akrep)", "Dhanus (Yay)", "Makara (Oglak)", "Kumbha (Kova)", "Meena (Balik)"]
BURC_KISA = ["Ar","Ta","Ge","Cn","Le","Vi","Li","Sc","Sg","Cp","Aq","Pi"]
GEZEGEN_LISTESI = [(swe.SUN, "Gunes", "Su"), (swe.MOON, "Ay", "Mo"), (swe.MARS, "Mars", "Ma"), (swe.MERCURY, "Merkur", "Me"), (swe.JUPITER, "Jupiter", "Ju"), (swe.VENUS, "Venus", "Ve"), (swe.SATURN, "Saturn", "Sa"), (swe.TRUE_NODE, "Rahu", "Ra")]
NAKSHATRALAR = [("Ashwini","Ke"),("Bharani","Ve"),("Krittika","Su"),("Rohini","Mo"),("Mrigashira","Ma"),("Ardra","Ra"),("Punarvasu","Ju"),("Pushya","Sa"),("Ashlesha","Me"),("Magha","Ke"),("Purva Phalguni","Ve"),("Uttara Phalguni","Su"),("Hasta","Mo"),("Chitra","Ma"),("Swati","Ra"),("Vishakha","Ju"),("Anuradha","Sa"),("Jyeshtha","Me"),("Mula","Ke"),("Purva Ashadha","Ve"),("Uttara Ashadha","Su"),("Shravana","Mo"),("Dhanishtha","Ma"),("Shatabhisha","Ra"),("Purva Bhadrapada","Ju"),("Uttara Bhadrapada","Sa"),("Revati","Me")]
DASHA_SIRASI = [("Ketu","Ke",7),("Shukra","Ve",20),("Surya","Su",6),("Chandra","Mo",10),("Mangala","Ma",7),("Rahu","Ra",18),("Guru","Ju",16),("Shani","Sa",19),("Budha","Me",17)]
LAGNA_SAHIPLERI = {0:"Ma",1:"Ve",2:"Me",3:"Mo",4:"Su",5:"Me",6:"Ve",7:"Ma",8:"Ju",9:"Sa",10:"Sa",11:"Ju"}
GEZ_ADI = {"Su":"Gunes","Mo":"Ay","Ma":"Mars","Me":"Merkur","Ju":"Jupiter","Ve":"Venus","Sa":"Saturn","Ra":"Rahu","Ke":"Ketu"}
GUCLER = {"Su":{"uchcha":0,"neecha":6,"own":[4]},"Mo":{"uchcha":1,"neecha":7,"own":[3]},"Ma":{"uchcha":9,"neecha":3,"own":[0,7]},"Me":{"uchcha":5,"neecha":11,"own":[2,5]},"Ju":{"uchcha":3,"neecha":9,"own":[8,11]},"Ve":{"uchcha":11,"neecha":5,"own":[1,6]},"Sa":{"uchcha":6,"neecha":0,"own":[9,10]},"Ra":{"uchcha":1,"neecha":7,"own":[]},"Ke":{"uchcha":7,"neecha":1,"own":[]}}

# --- YARDIMCI FONKSİYONLAR ---
def koordinat_al(sehir):
    geolocator = Nominatim(user_agent="vedik_astro_test", timeout=10)
    location = geolocator.geocode(sehir)
    if not location: raise ValueError("Sehir bulunamadi: " + sehir)
    return location.latitude, location.longitude

def julian_gun(tarih_str, saat_str, utc_offset):
    dt = datetime.strptime(tarih_str + " " + saat_str, "%Y-%m-%d %H:%M")
    utc_dt = dt - timedelta(hours=utc_offset)
    return swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute / 60.0)

def derece_fmt(ekl):
    ekl = ekl % 360
    d, m = int(ekl % 30), int(((ekl % 30) - int(ekl % 30)) * 60)
    s = int(((((ekl % 30) - d) * 60 - m) * 60))
    return f"{d}d {m:02d}' {s:02d}\""

def burc_bilgi(ekl):
    no = int((ekl % 360) / 30)
    return {"no": no, "ad": BURCLAR[no], "kisa": BURC_KISA[no], "derece": derece_fmt(ekl), "tam": round(ekl, 4)}

def nak_bilgi(ekl):
    ekl %= 360
    no = min(int(ekl / (360.0/27)), 26)
    pada = int((ekl % (360.0/27)) / (360.0/27/4)) + 1
    ad, sahip = NAKSHATRALAR[no]
    return {"ad": ad, "pada": pada, "sahip": sahip, "no": no}

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
        b, nak = burc_bilgi(ekl), nak_bilgi(ekl)
        gezegenler[kisa] = {"ad": ad, "burc": b["ad"], "burc_kisa": b["kisa"], "burc_no": b["no"], "derece": b["derece"], "tam": b["tam"], "ev": int(((ekl - lagna_ekl) % 360) / 30) + 1, "nakshatra": nak["ad"], "pada": nak["pada"], "nakshatra_sahip": nak["sahip"], "guc": guc_str(kisa, b["no"]), "retrograd": bool(hiz[3] < 0)}
        if kisa == "Mo": ay_ekl = ekl
    rahu_ekl = gezegenler["Ra"]["tam"]
    ketu_ekl = (rahu_ekl + 180) % 360
    kb, knak = burc_bilgi(ketu_ekl), nak_bilgi(ketu_ekl)
    gezegenler["Ke"] = {"ad": "Ketu", "burc": kb["ad"], "burc_kisa": kb["kisa"], "burc_no": kb["no"], "derece": kb["derece"], "tam": kb["tam"], "ev": int(((ketu_ekl - lagna_ekl) % 360) / 30) + 1, "nakshatra": knak["ad"], "pada": knak["pada"], "nakshatra_sahip": knak["sahip"], "guc": guc_str("Ke", kb["no"]), "retrograd": False}
    evler = [{"ev": i + 1, "burc": BURCLAR[(lagna["no"] + i) % 12], "burc_kisa": BURC_KISA[(lagna["no"] + i) % 12], "sahip": GEZ_ADI.get(LAGNA_SAHIPLERI.get((lagna["no"] + i) % 12), "?"), "sahip_kisa": LAGNA_SAHIPLERI.get((lagna["no"] + i) % 12)} for i in range(12)]
    ay_nak = nak_bilgi(ay_ekl)
    dasha_idx = next(i for i, (_, k, _) in enumerate(DASHA_SIRASI) if k == ay_nak["sahip"])
    ilerleme = (ay_ekl % (360.0/27)) / (360.0/27)
    ilk_sure = DASHA_SIRASI[dasha_idx][2]
    kalan = ilk_sure * (1 - ilerleme)
    dt = datetime.strptime(tarih, "%Y-%m-%d")
    bas = dt - timedelta(days=(ilk_sure - kalan) * 365.25)
    zincir = []
    for i in range(9):
        ad, kisa, sure = DASHA_SIRASI[(dasha_idx + i) % 9]
        gercek = kalan if i == 0 else sure
        bit = bas + timedelta(days=gercek * 365.25)
        zincir.append({"dasha": ad, "kisa": kisa, "sure": round(gercek, 2), "baslangic": bas.strftime("%d.%m.%Y"), "bitis": bit.strftime("%d.%m.%Y")})
        bas = bit
    return {"lagna": lagna, "gezegenler": gezegenler, "evler": evler, "ay_nakshatra": ay_nak, "dasha": {"suanki": next((z for z in zincir if datetime.strptime(z["baslangic"], "%d.%m.%Y") <= datetime.now() <= datetime.strptime(z["bitis"], "%d.%m.%Y")), zincir[-1]), "zincir": zincir}, "yogalar": [], "koordinat": {"lat": round(lat, 4), "lon": round(lon, 4)}, "ayanamsha": round(ayan, 6)}

def liste_olustur(veri, girdi):
    l, g, d = veri["lagna"], veri["gezegenler"], veri["dasha"]
    satirlar = ["="*72, "  VEDIK DOGUM HARITASI", "="*72, f"  Tarih: {girdi['tarih']}  Saat: {girdi['saat']}  Yer: {girdi['sehir']}", "="*72]
    satirlar.append(f"\n  LAGNA: {l['ad']} {l['derece']}\n")
    satirlar.append(f"  {'Gezegen':<10} {'Burc':<15} {'Derece':<12} {'Ev':<4} {'Nakshatra':<15} {'Guc':<10}")
    satirlar.append("-" * 72)
    for k in ["Su","Mo","Ma","Me","Ju","Ve","Sa","Ra","Ke"]:
        gz = g[k]
        satirlar.append(f"  {gz['ad']:<10} {gz['burc']:<15} {gz['derece']:<12} {gz['ev']:<4} {gz['nakshatra']:<15} {gz['guc']:<10}")
    return "\n".join(satirlar)

# --- FLASK YOLLARI ---
@app.route("/saglik")
def saglik(): return jsonify({"durum": "aktif"})

@app.route("/harita", methods=["POST"])
def harita_json():
    try:
        data = request.get_json()
        if not data: return jsonify({"hata": "Veri yok"}), 400
        return jsonify(hesapla(data["tarih"], data["saat"], data["sehir"], data.get("utc_offset", 3)))
    except Exception as e: return jsonify({"hata": str(e)}), 500

@app.route("/harita/liste", methods=["POST"])
def harita_liste():
    try:
        data = request.get_json()
        veri = hesapla(data["tarih"], data["saat"], data["sehir"], data.get("utc_offset", 3))
        return liste_olustur(veri, data), 200, {"Content-Type": "text/plain; charset=utf-8"}
    except Exception as e: return str(e), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
