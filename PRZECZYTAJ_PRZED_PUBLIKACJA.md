# WAŻNE PRZED PUBLIKACJĄ

Ta wersja ma w `render.yaml` ustawione:

- Web Service: `plan: free`
- PostgreSQL: `plan: free`
- Region: `frankfurt`

To jest dobre do TESTÓW wdrożenia.

## Bardzo ważne

Bezpłatny Render PostgreSQL wygasa po 30 dniach.
Nie traktuj darmowej bazy jako docelowego miejsca dla prawdziwych danych uczniów.

Przed rozpoczęciem normalnego używania strony z uczniami:
- przejdź na płatny PostgreSQL z backupami,
  albo
- wybierz inne trwałe rozwiązanie bazodanowe.

Cloudflare R2 może pozostać miejscem na przesyłane pliki.
