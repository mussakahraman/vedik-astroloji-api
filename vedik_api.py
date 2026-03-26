from flask import Flask, request, jsonify
import swisseph as swe
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
import traceback
import os

app = Flask(__name__)

# --- SABİT VERİLER ---
BURC_KISA = ["Ar", "Ta", "Ge", "Cn", "Le", "Vi", "Li", "Sc", "Sg", "Cp", "Aq", "Pi"]
NAKSHATRALAR = ["Ashw", "Bhar", "Krit", "Rohi", "Mrig", "Ardr", "Puna", "Push", "Ashl", "Magh", "P_Ph", "U_Ph", "Hast", "Chit", "Swat", "Vish", "Anur", "Jyes", "Mula", "P_As", "U_As", "Shra", "Dhan", "Shat", "P_Bh", "U_Bh", "Reva"]
# Karaka sıralaması: En yüksek derece AK, en düşük DK
KARAKA_ADLARI = ["AK", "AmK", "BK", "MK", "PK", "GK", "DK"]

def get_navamsa(ekl):
    ekl %= 360
    r_no = int(ekl / 30)
    nav_no = int((ekl % 30) / (30/9))
    start_signs = [0, 9, 6, 3] # Ates, Toprak, Hava, Su baslangic burclari
    return BURC_KISA[(start_signs[r_no % 4] + nav_no) % 12]

def get_nak(ekl):
    ekl %= 360
    n_no = int(ekl / (360/27))
    pada = int((ekl % (360/27)) / (360/108)) + 1
    return NAKSHATRALAR[n_no], pada

@app.route("/saglik")
def saglik(): return jsonify({"durum": "aktif"})

@app.route("/harita/liste", methods=["POST"])
def harita_liste():
    try:
        data = request.get_json(force=True)
        tarih, saat, sehir = data["tarih"], data["saat"], data["sehir"]
        lat, lon = 37.07, 36.24 # Osmaniye default
        
        # Zaman hesaplama (Saniye dahil)
        if len(saat.split(':')) == 2: saat += ":00"
        dt = datetime.strptime(f"{tarih} {saat}", "%Y-%m-%d %H:%M:%S")
        jd = swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute/60.0 + dt.second/3600.0 - float(data.get("utc_offset", 3)))
        
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        ayan = swe.get_ayanamsa_ut(jd)
        
        # Lagna
        _, ascmc = swe.houses(jd, lat, lon, b'W')
        l_ekl = (ascmc[0] - ayan) % 360
        l_nak, l_pada = get_nak(l_ekl)
        
        gez_verileri = []
        ids = [(0,"Sun"), (1,"Moon"), (2,"Mars"), (3,"Mercury"), (4,"Jupiter"), (5,"Venus"), (6,"Saturn")]
        
        for g_id, ad in ids:
            pos, hiz = swe.calc_ut(jd, g_id, swe.FLG_SIDEREAL)
            ekl = pos[0] % 360
            retro = " (R)" if hiz[3] < 0 else ""
            gez_verileri.append({"ad": ad + retro, "ekl": ekl, "deg_in_sign": ekl % 30})

        # Karaka Hesapla (7 Gezegen)
        sirali = sorted(gez_verileri, key=lambda x: x['deg_in_sign'], reverse=True)
        karaka_map = {sirali[i]['ad']: KARAKA_ADLARI[i] for i in range(len(KARAKA_ADLARI))}

        # Tabloyu Oluştur
        lines = [f"{'Body':<15} {'Longitude':<15} {'Nakshatra':<12} {'Pada':<5} {'Rasi':<5} {'Navamsa':<5}", "-"*70]
        
        # Lagna Satırı
        lines.append(f"{'Lagna':<15} {int(l_ekl%30):02} {BURC_KISA[int(l_ekl/30)]} {int((l_ekl%1)*60):02}' {l_nak:<12} {l_pada:<5} {BURC_KISA[int(l_ekl/30)]:<5} {get_navamsa(l_ekl):<5}")
        
        # Gezegen Satırları
        for g in gez_verileri:
            nak, pada = get_nak(g['ekl'])
            k_ad = karaka_map.get(g['ad'], "")
            name_str = f"{g['ad']} - {k_ad}" if k_ad else g['ad']
            deg, sign_idx = int(g['ekl'] % 30), int(g['ekl'] / 30)
            lines.append(f"{name_str:<15} {deg:02} {BURC_KISA[sign_idx]} {int((g['ekl']%1)*60):02}' {nak:<12} {pada:<5} {BURC_KISA[sign_idx]:<5} {get_navamsa(g['ekl']):<5}")

        # Rahu & Ketu (Karakasız)
        r_pos, _ = swe.calc_ut(jd, swe.TRUE_NODE, swe.FLG_SIDEREAL)
        for ad, e in [("Rahu", r_pos[0]%30), ("Ketu", (r_pos[0]+180)%360)]:
            n, p = get_nak(e)
            lines.append(f"{ad:<15} {int(e%30):02} {BURC_KISA[int(e/30)]} {int((e%1)*60):02}' {n:<12} {p:<5} {BURC_KISA[int(e/30)]:<5} {get_navamsa(e):<5}")

        return "\n".join(lines), 200, {"Content-Type": "text/plain; charset=utf-8"}
    except Exception as e:
        return str(e), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
