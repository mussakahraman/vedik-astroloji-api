Invoke-WebRequest -Uri "https://vedik-astroloji-api-production.up.railway.app/harita/liste" -Method POST -ContentType "application/json" -Body '{"tarih":"1993-04-09","saat":"12:30","sehir":"Osmaniye, Turkey"}' | Select-Object -ExpandProperty Content
```

Şöyle bir çıktı göreceksin:
```
========================================================================
  VEDIK DOGUM HARITASI
========================================================================
  Tarih     : 1993-04-09   Saat : 12:30
  Yer       : Osmaniye, Turkey
  ...
  GEZEGENLER
------------------------------------------------------------------------
  Gezegen    Burc                  Derece        Ev   Nakshatra   ...
------------------------------------------------------------------------
  Gunes      Mesha (Koc)           25d 47' ...   10   Revati      ...
  Ay         Vrishchika (Akrep)    1d 44'  ...    4   Vishakha    ...
  ...
