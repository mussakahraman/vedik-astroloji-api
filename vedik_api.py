from flask import Flask, request, jsonify
import swisseph as swe
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
import traceback
import os

app = Flask(__name__)

# --- SABİT VERİLER ---
BURCLAR = ["Mesha (Koc)", "Vrishabha (Boga)", "Mithuna (Ikizler)", "Karka (Yengec)", "Simha (Aslan)", "Kanya (Basak)", "Tula (Terazi)", "Vrishchika (Akrep)", "Dhanus (Yay)", "Makara (Oglak)", "Kumbha (Kova)", "Meena (Balik)"]
GEZEGEN_LISTESI = [(swe.SUN, "Gunes", "Su"), (swe.MOON, "Ay", "Mo"), (swe.MARS, "Mars", "Ma"), (swe.MERCURY, "Merkur", "Me"), (swe.JUPITER, "Jupiter", "Ju"), (swe.VENUS, "Venus", "Ve"), (swe.SATURN, "Saturn", "Sa")]

@app.route("/")
def index(): return "API Aktif"

@app.route("/saglik")
def saglik(): return jsonify({"status": "ok"})

@app.route("/harita/liste", methods=["POST"])
def harita_liste():
    try:
        data = request.get_json(force=True)
        tarih = data.get("tarih")
        saat = data.get("saat")
        sehir = data.get("sehir")
        utc_offset = float(data.get("utc_offset", 3))

        # Koordinat alma (Hata ihtimaline karşı manuel koruma)
        lat, lon = 37.07, 36.24 # Varsayılan Osmaniye koordinatları
        try:
            geolocator = Nominatim(user_agent="vedik_test_v1")
            location = geolocator.geocode(sehir, timeout=10)
            if location:
                lat, lon = location.latitude, location.longitude
        except:
            pass # Geopy hata verirse varsayılan Osmaniye'den devam et

        # Zaman hesaplama
        dt = datetime.strptime(f"{tarih} {saat}", "%Y-%m-%d %H:%M")
        utc_dt = dt - timedelta(hours=utc_offset)
        jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0)
        
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        ayan = swe.get_ayanamsa_ut(jd)
        
        # Evler ve Lagna
        _, ascmc = swe.houses(jd, lat, lon, b'W')
        lagna_ekl = (ascmc[0] - ayan) % 360
        lagna_no = int(lagna_ekl / 30)
        
        res = [f"VEDIK HARITA - {sehir.upper()}", "="*30]
        res.append(f"YUKSELEN: {BURCLAR[lagna_no]}")
        res.append("-" * 30)
        
        for gez_id, ad, kisa in GEZEGEN_LISTESI:
            pos, _ = swe.calc_ut(jd, gez_id, swe.FLG_SIDEREAL)
            ekl = pos[0] % 360
            b_no = int(ekl / 30)
            ev = int(((ekl - lagna_ekl) % 360) / 30) + 1
            res.append(f"{ad:<10}: {BURCLAR[b_no]:<15} Ev: {ev}")
            
        return "\n".join(res), 200, {"Content-Type": "text/plain; charset=utf-8"}

    except Exception as e:
        # Hata olursa PowerShell'e detayı gönder
        return f"Kod Hatasi: {str(e)}\n{traceback.format_exc()}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
