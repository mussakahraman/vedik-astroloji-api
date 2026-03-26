from flask import Flask, request, jsonify
import swisseph as swe
import traceback
import os

app = Flask(__name__)

# --- TEKNİK SABİTLER ---
BURC_KISA = ["Ar", "Ta", "Ge", "Cn", "Le", "Vi", "Li", "Sc", "Sg", "Cp", "Aq", "Pi"]
NAK_LISTE = ["Ashw", "Bhar", "Krit", "Rohi", "Mrig", "Ardr", "Puna", "Push", "Ashl", "Magh", "P_Ph", "U_Ph", "Hast", "Chit", "Swat", "Vish", "Anur", "Jyes", "Mula", "P_As", "U_As", "Shra", "Dhan", "Shat", "P_Bh", "U_Bh", "Reva"]
KARAKA_SIRALAMASI = ["AK", "AmK", "BK", "MK", "PK", "GK", "DK"]

def navamsa_hesapla(ekl):
    ekl %= 360
    r_no, n_no = int(ekl / 30), int((ekl % 30) / (30/9))
    offsets = [0, 9, 6, 3] 
    return BURC_KISA[(offsets[r_no % 4] + n_no) % 12]

def nak_detay(ekl):
    ekl %= 360
    n_no = int(ekl / (360/27))
    pada = int((ekl % (360/27)) / (360/108)) + 1
    return NAK_LISTE[min(n_no, 26)], pada

@app.route("/")
def ana(): return "API Calisiyor"

@app.route("/harita/liste", methods=["POST"])
def harita_liste():
    try:
        data = request.get_json(silent=True) or {}
        t_str = data.get("tarih", "09.04.1993")
        s_str = data.get("saat", "12:30")
        utc = float(data.get("utc_offset", 3))
        
        # Tarih Ayrıştırma
        d, m, y = map(int, t_str.replace('-', '.').split('.'))
        sa, dk = map(int, s_str.replace('-', ':').split(':'))
        
        # Julian Day
        jd = swe.julday(y, m, d, (sa + dk/60.0) - utc)
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        ayan = swe.get_ayanamsa_ut(jd)
        
        # Lagna (Osmaniye Koordinat)
        lat, lon = 37.07, 36.24
        _, ascmc = swe.houses(jd, lat, lon, b'W')
        l_ekl = (ascmc[0] - ayan) % 360
        
        # 7 Gezegen (Hata düzeltilmiş versiyon)
        gez_list = []
        ids = [(0, "Sun"), (1, "Moon"), (2, "Mars"), (3, "Merc"), (4, "Jupt"), (5, "Venu"), (6, "Satu")]
        
        for g_id, ad in ids:
            # Sadece pozisyon ve hızı al, flags ekle (swe.FLG_SPEED)
            res = swe.calc_ut(jd, g_id, swe.FLG_SIDEREAL | swe.FLG_SPEED)
            ekl = res[0][0] % 360
            hiz = res[0][3] # Hız verisi res[0]'ın 4. elemanıdır
            retro = " (R)" if hiz < 0 else ""
            gez_list.append({"ad": ad, "ekl": ekl, "deg_in_sign": ekl % 30, "retro": retro})

        # Karaka
        sirali = sorted(gez_list, key=lambda x: x['deg_in_sign'], reverse=True)
        k_map = {sirali[i]['ad']: KARAKA_SIRALAMASI[i] for i in range(len(KARAKA_SIRALAMASI))}

        # Tablo Oluşturma
        h = f"{'Body':<15} {'Deg':<8} {'Nak':<10} {'P':<3} {'Rasi':<5} {'Navam':<5}"
        out = [f"VEDIK HARITA: {data.get('sehir','OSMANIYE').upper()}", "="*55, h, "-"*55]
        
        # Lagna
        nk, pd = nak_detay(l_ekl)
        out.append(f"{'Lagna':<15} {int(l_ekl%30):02}°{int((l_ekl%1)*60):02}' {nk:<10} {pd:<3} {BURC_KISA[int(l_ekl/30)]:<5} {navamsa_hesapla(l_ekl):<5}")
        
        for g in gez_list:
            nk, pd = nak_detay(g['ekl'])
            tag = k_map.get(g['ad'], "")
            full_name = f"{g['ad']}{g['retro']} - {tag}" if tag else g['ad']
            out.append(f"{full_name:<15} {int(g['ekl']%30):02}°{int((g['ekl']%1)*60):02}' {nk:<10} {pd:<3} {BURC_KISA[int(g['ekl']/30)]:<5} {navamsa_hesapla(g['ekl']):<5}")

        # Rahu & Ketu
        r_res = swe.calc_ut(jd, swe.TRUE_NODE, swe.FLG_SIDEREAL)
        r_ekl = r_res[0][0] % 360
        for ad, e in [("Rahu", r_ekl), ("Ketu", (r_ekl+180)%360)]:
            nk, pd = nak_detay(e)
            out.append(f"{ad:<15} {int(e%30):02}°{int((e%1)*60):02}' {nk:<10} {pd:<3} {BURC_KISA[int(e/30)]:<5} {navamsa_hesapla(e):<5}")

        return "\n".join(out), 200, {"Content-Type": "text/plain; charset=utf-8"}

    except Exception as e:
        return f"Hata: {str(e)}\n{traceback.format_exc()}", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
