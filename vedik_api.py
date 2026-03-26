"""
Vedik Astroloji Hesaplama API v2.0
Railway.app veya Render.com'a yükle, çalıştır.

Kurulum:
  pip install flask pyswisseph geopy

Endpoint'ler:
  GET  /saglik          -> API durumu
  POST /harita          -> JSON cikti
  POST /harita/liste    -> Referans programa benzer duz metin liste
"""

from flask import Flask, request, jsonify
import swisseph as swe
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim

app = Flask(__name__)

BURCLAR = [
    "Mesha (Koc)", "Vrishabha (Boga)", "Mithuna (Ikizler)",
    "Karka (Yengec)", "Simha (Aslan)", "Kanya (Basak)",
    "Tula (Terazi)", "Vrishchika (Akrep)", "Dhanus (Yay)",
    "Makara (Oglak)", "Kumbha (Kova)", "Meena (Balik)"
]

BURC_KISA = ["Ar","Ta","Ge","Cn","Le","Vi","Li","Sc","Sg","Cp","Aq","Pi"]

GEZEGEN_LISTESI = [
    (swe.SUN,       "Gunes",   "Su"),
    (swe.MOON,      "Ay",      "Mo"),
    (swe.MARS,      "Mars",    "Ma"),
    (swe.MERCURY,   "Merkur",  "Me"),
    (swe.JUPITER,   "Jupiter", "Ju"),
    (swe.VENUS,     "Venus",   "Ve"),
    (swe.SATURN,    "Saturn",  "Sa"),
    (swe.TRUE_NODE, "Rahu",    "Ra"),
]

NAKSHATRALAR = [
    ("Ashwini","Ke"),("Bharani","Ve"),("Krittika","Su"),
    ("Rohini","Mo"),("Mrigashira","Ma"),("Ardra","Ra"),
    ("Punarvasu","Ju"),("Pushya","Sa"),("Ashlesha","Me"),
    ("Magha","Ke"),("Purva Phalguni","Ve"),("Uttara Phalguni","Su"),
    ("Hasta","Mo"),("Chitra","Ma"),("Swati","Ra"),
    ("Vishakha","Ju"),("Anuradha","Sa"),("Jyeshtha","Me"),
    ("Mula","Ke"),("Purva Ashadha","Ve"),("Uttara Ashadha","Su"),
    ("Shravana","Mo"),("Dhanishtha","Ma"),("Shatabhisha","Ra"),
    ("Purva Bhadrapada","Ju"),("Uttara Bhadrapada","Sa"),("Revati","Me"),
]

DASHA_SIRASI = [
    ("Ketu","Ke",7),("Shukra","Ve",20),("Surya","Su",6),
    ("Chandra","Mo",10),("Mangala","Ma",7),("Rahu","Ra",18),
    ("Guru","Ju",16),("Shani","Sa",19),("Budha","Me",17),
]

LAGNA_SAHIPLERI = {
    0:"Ma",1:"Ve",2:"Me",3:"Mo",4:"Su",5:"Me",
    6:"Ve",7:"Ma",8:"Ju",9:"Sa",10:"Sa",11:"Ju"
}

GEZ_ADI = {
    "Su":"Gunes","Mo":"Ay","Ma":"Mars","Me":"Merkur",
    "Ju":"Jupiter","Ve":"Venus","Sa":"Saturn","Ra":"Rahu","Ke":"Ketu"
}

GUCLER = {
    "Su":{"uchcha":0,"neecha":6,"own":[4]},
    "Mo":{"uchcha":1,"neecha":7,"own":[3]},
    "Ma":{"uchcha":9,"neecha":3,"own":[0,7]},
    "Me":{"uchcha":5,"neecha":11,"own":[2,5]},
    "Ju":{"uchcha":3,"neecha":9,"own":[8,11]},
    "Ve":{"uchcha":11,"neecha":5,"own":[1,6]},
    "Sa":{"uchcha":6,"neecha":0,"own":[9,10]},
    "Ra":{"uchcha":1,"neecha":7,"own":[]},
    "Ke":{"uchcha":7,"neecha":1,"own":[]},
}

def koordinat_al(sehir):
    geolocator = Nominatim(user_agent="vedik_astro_v2")
    location = geolocator.geocode(sehir)
    if not location:
        raise ValueError(f"Sehir bulunamadi: {sehir}")
    return location.latitude, location.longitude

def julian_gun(tarih_str, saat_str, utc_offset):
    dt = datetime.strptime(f"{tarih_str} {saat_str}", "%Y-%m-%d %H:%M")
    utc_dt = dt - timedelta(hours=utc_offset)
    return swe.julday(utc_dt.year, utc_dt.month, utc_dt.day,
                      utc_dt.hour + utc_dt.minute / 60.0)

def derece_fmt(ekl):
    ekl = ekl % 360
    d = int(ekl % 30)
    m = int(((ekl % 30) - d) * 60)
    s = int((((ekl % 30) - d) * 60 - m) * 60)
    return f"{d}d {m:02d}' {s:02d}\""

def burc_bilgi(ekl):
    ekl = ekl % 360
    no = int(ekl / 30)
    return {"no": no, "ad": BURCLAR[no], "kisa": BURC_KISA[no],
            "derece": derece_fmt(ekl), "tam": round(ekl, 4)}

def nak_bilgi(ekl):
    ekl = ekl % 360
    no = min(int(ekl / (360/27)), 26)
    pada = int((ekl % (360/27)) / (360/27/4)) + 1
    ad, sahip = NAKSHATRALAR[no]
    return {"ad": ad, "pada": pada, "sahip": sahip, "no": no}

def guc_str(kisa, burc_no):
    g = GUCLER.get(kisa, {})
    if burc_no == g.get("uchcha"): return "Uchcha"
    if burc_no == g.get("neecha"): return "Neecha"
    if burc_no in g.get("own",[]): return "Swakshetra"
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
    ay_ekl = None
    for gez_id, ad, kisa in GEZEGEN_LISTESI:
        pos, hiz = swe.calc_ut(jd, gez_id, swe.FLG_SIDEREAL)
        ekl = pos[0] % 360
        b = burc_bilgi(ekl)
        ev = int(((ekl - lagna_ekl) % 360) / 30) + 1
        nak = nak_bilgi(ekl)
        retrograd = hiz[3] < 0 if len(hiz) > 3 else False
        gezegenler[kisa] = {
            "ad": ad, "burc": b["ad"], "burc_kisa": b["kisa"],
            "burc_no": b["no"], "derece": b["derece"], "tam": b["tam"],
            "ev": ev, "nakshatra": nak["ad"], "pada": nak["pada"],
            "nakshatra_sahip": nak["sahip"],
            "guc": guc_str(kisa, b["no"]),
            "retrograd": retrograd
        }
        if kisa == "Mo":
            ay_ekl = ekl

    rahu_ekl = gezegenler["Ra"]["tam"]
    ketu_ekl = (rahu_ekl + 180) % 360
    kb = burc_bilgi(ketu_ekl)
    knak = nak_bilgi(ketu_ekl)
    gezegenler["Ke"] = {
        "ad": "Ketu", "burc": kb["ad"], "burc_kisa": kb["kisa"],
        "burc_no": kb["no"], "derece": kb["derece"], "tam": kb["tam"],
        "ev": int(((ketu_ekl - lagna_ekl) % 360) / 30) + 1,
        "nakshatra": knak["ad"], "pada": knak["pada"],
        "nakshatra_sahip": knak["sahip"],
        "guc": guc_str("Ke", kb["no"]), "retrograd": False
    }

    evler = []
    for i in range(12):
        burc_no = (lagna["no"] + i) % 12
        sah = LAGNA_SAHIPLERI.get(burc_no, "?")
        evler.append({
            "ev": i + 1, "burc": BURCLAR[burc_no],
            "burc_kisa": BURC_KISA[burc_no],
            "sahip": GEZ_ADI.get(sah, "?"), "sahip_kisa": sah
        })

    ay_nak = nak_bilgi(ay_ekl)
    nak_no = ay_nak["no"]
    nak_sahip = ay_nak["sahip"]
    dasha_idx = next(i for i,(_, k, _) in enumerate(DASHA_SIRASI) if k == nak_sahip)
    nak_boyut = 360 / 27
    ilerleme = (ay_ekl % 360 - nak_no * nak_boyut) / nak_boyut
    _, _, ilk_sure = DASHA_SIRASI[dasha_idx]
    kalan = ilk_sure * (1 - ilerleme)

    dt = datetime.strptime(tarih, "%Y-%m-%d")
    bas = dt - timedelta(days=ilk_sure * 365.25 * ilerleme)
    zincir = []
    for i in range(9):
        idx = (dasha_idx + i) % 9
        ad, kisa, sure = DASHA_SIRASI[idx]
        gercek = kalan if i == 0 else sure
        bit = bas + timedelta(days=gercek * 365.25)
        zincir.append({"dasha": ad, "kisa": kisa, "sure": round(gercek, 2),
                        "baslangic": bas.strftime("%d.%m.%Y"),
                        "bitis": bit.strftime("%d.%m.%Y")})
        bas = bit

    bugun = datetime.now()
    suanki = next((z for z in zincir
                   if datetime.strptime(z["baslangic"], "%d.%m.%Y") <= bugun
                   <= datetime.strptime(z["bitis"], "%d.%m.%Y")), zincir[-1])

    dasha = {"suanki": suanki["dasha"], "baslangic": suanki["baslangic"],
             "bitis": suanki["bitis"], "zincir": zincir}

    yogalar = []
    ay_ev = gezegenler["Mo"]["ev"]
    ju_ev = gezegenler["Ju"]["ev"]
    if ju_ev in [(ay_ev + k - 1) % 12 + 1 for k in [1,4,7,10]]:
        yogalar.append("Gaja Kesari Yoga - Jupiter Ay'dan kendra evde")
    if gezegenler["Su"]["burc_no"] == gezegenler["Me"]["burc_no"]:
        yogalar.append("Budha-Aditya Yoga - Gunes + Merkur kavusum")
    ay_b = gezegenler["Mo"]["burc_no"]; ma_b = gezegenler["Ma"]["burc_no"]
    if ay_b == ma_b or abs(ay_b - ma_b) == 6:
        yogalar.append("Chandra-Mangala Yoga - Ay ve Mars iliskili")
    lsah = LAGNA_SAHIPLERI.get(lagna["no"],"")
    if gezegenler.get(lsah,{}).get("ev") == 1:
        yogalar.append("Lagnadhipati Yoga - Lagna sahibi 1. evde")

    return {
        "lagna": lagna, "gezegenler": gezegenler, "evler": evler,
        "ay_nakshatra": ay_nak, "dasha": dasha, "yogalar": yogalar,
        "koordinat": {"lat": round(lat,4), "lon": round(lon,4)},
        "ayanamsha": round(ayan, 6)
    }

def liste_olustur(veri, girdi):
    tarih, saat, sehir = girdi["tarih"], girdi["saat"], girdi["sehir"]
    l = veri["lagna"]
    g = veri["gezegenler"]
    d = veri["dasha"]
    nak = veri["ay_nakshatra"]
    satirlar = []
    s = satirlar.append

    s("=" * 72)
    s("  VEDIK DOGUM HARITASI")
    s("=" * 72)
    s(f"  Tarih     : {tarih}   Saat : {saat}")
    s(f"  Yer       : {sehir}")
    s(f"  Koordinat : {veri['koordinat']['lat']}N  {veri['koordinat']['lon']}E")
    s(f"  Ayanamsha : Lahiri  {veri['ayanamsha']}")
    s(f"  Ev Sistemi: Whole Sign")
    s("=" * 72)
    s(f"\n  LAGNA  :  {l['ad']}   {l['derece']}")
    s(f"            Nakshatra: {nak_bilgi(l['tam'])['ad']}")

    s("\n" + "-" * 72)
    s(f"  GEZEGENLER")
    s("-" * 72)
    s(f"  {'Gezegen':<10} {'Burc':<22} {'Derece':<13} {'Ev':<4} {'Nakshatra':<22} {'Pd':<3} {'Guc':<12} Ret")
    s("-" * 72)
    for k in ["Su","Mo","Ma","Me","Ju","Ve","Sa","Ra","Ke"]:
        gz = g.get(k)
        if not gz: continue
        r = "(R)" if gz["retrograd"] else "   "
        s(f"  {gz['ad']:<10} {gz['burc']:<22} {gz['derece']:<13} "
          f"{gz['ev']:<4} {gz['nakshatra']:<22} {gz['pada']:<3} {gz['guc']:<12} {r}")

    s("\n" + "-" * 72)
    s(f"  EVLER (Whole Sign)")
    s("-" * 72)
    s(f"  {'Ev':<5} {'Burc':<22} {'Sahip':<12} Gezegen(ler)")
    s("-" * 72)
    for ev in veri["evler"]:
        evdekiler = [g[k]["ad"] for k in ["Su","Mo","Ma","Me","Ju","Ve","Sa","Ra","Ke"]
                     if g.get(k, {}).get("ev") == ev["ev"]]
        s(f"  {ev['ev']:<5} {ev['burc']:<22} {ev['sahip']:<12} {', '.join(evdekiler) if evdekiler else '-'}")

    s("\n" + "-" * 72)
    s(f"  VIMSHOTTARI DASHA")
    s("-" * 72)
    s(f"  Ay Nakshatra : {nak['ad']}  Pada {nak['pada']}  (Sahip: {GEZ_ADI.get(nak['sahip'],'?')})")
    s(f"  Su an        : {d['suanki']} Mahadasha")
    s(f"               : {d['baslangic']} --> {d['bitis']}")
    s(f"\n  {'Donem':<14} {'Sure':<10} {'Baslangic':<14} Bitis")
    s("  " + "-" * 50)
    for z in d["zincir"]:
        isaret = "  << SU AN" if z["dasha"] == d["suanki"] else ""
        s(f"  {z['dasha']:<14} {str(z['sure'])+' yil':<10} {z['baslangic']:<14} {z['bitis']}{isaret}")

    if veri["yogalar"]:
        s("\n" + "-" * 72)
        s(f"  YOGALAR")
        s("-" * 72)
        for y in veri["yogalar"]:
            s(f"  * {y}")

    s("\n" + "=" * 72)
    return "\n".join(satirlar)

@app.route("/saglik", methods=["GET"])
def saglik():
    return jsonify({"durum": "aktif", "versiyon": "2.0"})

@app.route("/harita", methods=["POST"])
def harita_json():
    try:
        data = request.json
        veri = hesapla(data["tarih"], data["saat"], data["sehir"], data.get("utc_offset", 3))
        return jsonify({"durum": "basarili", "girdi": data, **veri})
    except Exception as e:
        return jsonify({"hata": str(e)}), 500

@app.route("/harita/liste", methods=["POST"])
def harita_liste():
    try:
        data = request.json
        veri = hesapla(data["tarih"], data["saat"], data["sehir"], data.get("utc_offset", 3))
        liste = liste_olustur(veri, data)
        return liste, 200, {"Content-Type": "text/plain; charset=utf-8"}
    except Exception as e:
        return f"HATA: {str(e)}", 500
@app.route("/debug", methods=["GET"])
def debug():
    try:
        import swisseph as swe
        from geopy.geocoders import Nominatim
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        return jsonify({"swe": "ok", "geopy": "ok"})
    except Exception as e:
        return jsonify({"hata": str(e)}), 500
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
