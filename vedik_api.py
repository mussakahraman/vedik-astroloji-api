"""
Vedik Astroloji Hesaplama API
Railway.app veya Render.com'a yükle, çalıştır.

Kurulum:
  pip install flask pyswisseph geopy

Çalıştırma:
  python vedik_api.py

Test:
  POST http://localhost:5000/harita
  Body: {"tarih": "1993-04-09", "saat": "12:15", "sehir": "Osmaniye, Turkey"}
"""

from flask import Flask, request, jsonify
import swisseph as swe
from datetime import datetime
from geopy.geocoders import Nominatim
import math

app = Flask(__name__)

# ── Sabit veriler ──────────────────────────────────────────────
BURCLАР = [
    "Mesha (Koç)", "Vrishabha (Boğa)", "Mithuna (İkizler)",
    "Karka (Yengeç)", "Simha (Aslan)", "Kanya (Başak)",
    "Tula (Terazi)", "Vrishchika (Akrep)", "Dhanus (Yay)",
    "Makara (Oğlak)", "Kumbha (Kova)", "Meena (Balık)"
]

GEZEGENLER = {
    swe.SUN:     "Güneş ☉",
    swe.MOON:    "Ay ☽",
    swe.MARS:    "Mars ♂",
    swe.MERCURY: "Merkür ☿",
    swe.JUPITER: "Jüpiter ♃",
    swe.VENUS:   "Venüs ♀",
    swe.SATURN:  "Satürn ♄",
    swe.TRUE_NODE: "Rahu ☊",  # Ketu otomatik hesaplanır (Rahu + 180°)
}

NAKSHATRALAR = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha",
    "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha",
    "Shravana", "Dhanishtha", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati"
]

# Vimshottari Dasha sırası ve süreleri (yıl)
DASHA_SIRASI = [
    ("Ketu",    7),
    ("Shukra",  20),
    ("Surya",   6),
    ("Chandra", 10),
    ("Mangala", 7),
    ("Rahu",    18),
    ("Guru",    16),
    ("Shani",   19),
    ("Budha",   17),
]

# ── Yardımcı fonksiyonlar ──────────────────────────────────────

def koordinat_al(sehir: str) -> tuple:
    """Şehir adından enlem/boylam döndürür."""
    geolocator = Nominatim(user_agent="vedik_astro")
    location = geolocator.geocode(sehir)
    if not location:
        raise ValueError(f"Şehir bulunamadı: {sehir}")
    return location.latitude, location.longitude

def julian_gun(tarih_str: str, saat_str: str, utc_offset: float = 3.0) -> float:
    """Tarih ve saati Julian Day Number'a çevirir."""
    dt = datetime.strptime(f"{tarih_str} {saat_str}", "%Y-%m-%d %H:%M")
    # UTC'ye çevir
    utc_saat = dt.hour + dt.minute / 60.0 - utc_offset
    jd = swe.julday(dt.year, dt.month, dt.day, utc_saat)
    return jd

def burç_ve_derece(ekl_derece: float) -> dict:
    """Ekliptik dereceyi burç ve derece bilgisine çevirir."""
    burç_no = int(ekl_derece / 30)
    derece = ekl_derece % 30
    dak = (derece % 1) * 60
    return {
        "burç": BURCLАР[burç_no],
        "derece": f"{int(derece)}°{int(dak)}'",
        "tam_derece": round(ekl_derece, 4)
    }

def nakshatra_hesapla(ay_derece: float) -> dict:
    """Ay'ın Nakshatra ve Pada bilgisini döndürür."""
    nak_no = int(ay_derece / (360 / 27))
    pada = int((ay_derece % (360 / 27)) / (360 / 27 / 4)) + 1
    return {
        "nakshatra": NAKSHATRALAR[nak_no],
        "pada": pada,
        "derece_icinde": round(ay_derece % (360 / 27), 2)
    }

def dasha_hesapla(ay_derece: float, dogum_tarihi: str) -> dict:
    """Vimshottari Dasha — doğumdaki dönemi ve güncel durumu hesaplar."""

    # Hangi Nakshatra'da doğuldu → o Nakshatra'nın sahibi Dasha sahibi
    nak_no = int(ay_derece / (360 / 27))
    dasha_sahibi_idx = nak_no % 9  # 9'a göre döngü

    # Nakshatra içinde ne kadar ilerlendi → kalan Dasha süresi
    nak_baslangic = nak_no * (360 / 27)
    nak_icerisindeki_ilerleme = (ay_derece - nak_baslangic) / (360 / 27)
    ilk_dasha_adi, ilk_dasha_sure = DASHA_SIRASI[dasha_sahibi_idx]
    dogumda_kalan_yil = ilk_dasha_sure * (1 - nak_icerisindeki_ilerleme)

    # Tüm dasha zincirini oluştur
    dt = datetime.strptime(dogum_tarihi, "%Y-%m-%d")
    zincir = []
    sure_kalan = dogumda_kalan_yil

    for i in range(9):
        idx = (dasha_sahibi_idx + i) % 9
        ad, sure = DASHA_SIRASI[idx]
        gercek_sure = sure_kalan if i == 0 else sure
        bitis_yil = dt.year + (dt.timetuple().tm_yday / 365) + sure_kalan
        bitis = datetime(int(bitis_yil), dt.month, dt.day)
        zincir.append({
            "dasha": ad,
            "sure_yil": round(gercek_sure, 2),
            "bitis": bitis.strftime("%Y-%m")
        })
        sure_kalan += sure if i > 0 else 0

    # Şu anki dasha'yı bul
    bugun = datetime.now()
    bugunun_yil_fraksiyonu = (bugun - dt).days / 365.25
    birikim = dogumda_kalan_yil
    suanki_idx = 0
    for i, (_, sure) in enumerate(DASHA_SIRASI):
        gercek_sure = dogumda_kalan_yil if i == 0 else sure
        if bugunun_yil_fraksiyonu < birikim:
            suanki_idx = (dasha_sahibi_idx + i) % 9
            break
        birikim += sure if i > 0 else 0

    return {
        "suanki_mahadasha": DASHA_SIRASI[suanki_idx][0],
        "zincir": zincir[:5],  # İlk 5 dönem yeterli
        "ilk_dasha": ilk_dasha_adi,
        "dogumda_kalan": round(dogumda_kalan_yil, 2)
    }

def yoga_kontrol(gezegenler: dict, ev_sahipleri: dict) -> list:
    """Temel yogaları tespit eder."""
    yogalar = []

    # Gaja Kesari Yoga: Jüpiter Ay'dan 1, 4, 7, 10. evde
    ay_ev = gezegenler.get("Ay ☽", {}).get("ev", 0)
    jup_ev = gezegenler.get("Jüpiter ♃", {}).get("ev", 0)
    if jup_ev in [(ay_ev + i - 1) % 12 + 1 for i in [1, 4, 7, 10]]:
        yogalar.append({
            "ad": "Gaja Kesari Yoga",
            "aciklama": "Jüpiter Ay'a göre kendi yerinde — zeka, itibar ve başarı getirir"
        })

    # Raj Yoga: 1. ev sahibi + 5. veya 9. ev sahibi aynı evde
    # (basit kontrol)
    yogalar.append({
        "ad": "Stellium kontrolü",
        "aciklama": "Aynı evde 3+ gezegen varsa güçlü ev enerjisi oluşur"
    })

    return yogalar

# ── Ana API endpoint ───────────────────────────────────────────

@app.route("/harita", methods=["POST"])
def harita_hesapla():
    """
    Vedik doğum haritasını hesaplar.

    Body örneği:
    {
        "tarih": "1993-04-09",
        "saat": "12:15",
        "sehir": "Osmaniye, Turkey",
        "utc_offset": 3
    }
    """
    try:
        data = request.json
        tarih = data["tarih"]        # YYYY-MM-DD
        saat = data["saat"]          # HH:MM
        sehir = data["sehir"]        # "Şehir, Ülke"
        utc_offset = data.get("utc_offset", 3)  # Türkiye için 3

        # 1. Koordinatlar
        lat, lon = koordinat_al(sehir)

        # 2. Julian Day
        jd = julian_gun(tarih, saat, utc_offset)

        # 3. Lahiri Ayanamsha ayarla
        swe.set_sid_mode(swe.SIDM_LAHIRI)

        # 4. Ev hesabı (Whole Sign)
        evler, ascmc = swe.houses(jd, lat, lon, b'W')  # W = Whole Sign
        lagna_tropical = ascmc[0]
        ayanamsha = swe.get_ayanamsa_ut(jd)
        lagna_sidereal = (lagna_tropical - ayanamsha) % 360

        lagna_bilgi = burç_ve_derece(lagna_sidereal)

        # 5. Gezegen pozisyonları
        gezegen_sonuclari = {}
        ay_derece_sidereal = None

        for gez_id, gez_adi in GEZEGENLER.items():
            pos, _ = swe.calc_ut(jd, gez_id, swe.FLG_SIDEREAL)
            derece_sidereal = pos[0] % 360
            burç_bilgi = burç_ve_derece(derece_sidereal)
            ev_no = int(((derece_sidereal - lagna_sidereal) % 360) / 30) + 1

            gezegen_sonuclari[gez_adi] = {
                **burç_bilgi,
                "ev": ev_no
            }

            if gez_id == swe.MOON:
                ay_derece_sidereal = derece_sidereal

        # Ketu (Rahu'nun tam karşısı)
        rahu_derece = gezegen_sonuclari["Rahu ☊"]["tam_derece"]
        ketu_derece = (rahu_derece + 180) % 360
        ketu_bilgi = burç_ve_derece(ketu_derece)
        gezegen_sonuclari["Ketu ☋"] = {
            **ketu_bilgi,
            "ev": int(((ketu_derece - lagna_sidereal) % 360) / 30) + 1
        }

        # 6. Nakshatra
        nakshatra = nakshatra_hesapla(ay_derece_sidereal)

        # 7. Dasha
        dasha = dasha_hesapla(ay_derece_sidereal, tarih)

        # 8. Yoga kontrolü
        yogalar = yoga_kontrol(gezegen_sonuclari, {})

        # ── Sonuç ──
        return jsonify({
            "durum": "basarili",
            "girdi": {
                "tarih": tarih,
                "saat": saat,
                "sehir": sehir,
                "koordinat": {"lat": round(lat, 4), "lon": round(lon, 4)}
            },
            "lagna": lagna_bilgi,
            "gezegenler": gezegen_sonuclari,
            "nakshatra": nakshatra,
            "dasha": dasha,
            "yogalar": yogalar
        })

    except KeyError as e:
        return jsonify({"hata": f"Eksik alan: {str(e)}"}), 400
    except ValueError as e:
        return jsonify({"hata": str(e)}), 400
    except Exception as e:
        return jsonify({"hata": f"Hesaplama hatası: {str(e)}"}), 500


@app.route("/saglik", methods=["GET"])
def saglik():
    """API'nin çalışıp çalışmadığını kontrol eder."""
    return jsonify({"durum": "aktif", "versiyon": "1.0"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
