# Wdrożenie: Render + PostgreSQL + Cloudflare R2

## 1. GitHub

Wrzuć cały projekt V4 do prywatnego repozytorium GitHub.

Nie wrzucaj:
- `.env`
- `.venv`
- `instance`
- lokalnych plików uczniów.

`.gitignore` już je pomija.

## 2. Cloudflare R2

W Cloudflare:
1. utwórz bucket R2, np. `jw-korepetycje`,
2. utwórz klucz API z prawem odczytu i zapisu do tego bucketa,
3. zapisz:
   - Account ID,
   - Access Key ID,
   - Secret Access Key,
   - nazwę bucketa.

Bucket nie musi być publiczny.

Aplikacja generuje krótkotrwałe, podpisane linki do pobierania plików
dopiero po sprawdzeniu, czy zalogowany użytkownik ma dostęp.

## 3. Render

Najwygodniej utworzyć Blueprint na podstawie `render.yaml`.

Ustaw sekrety:
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`
- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET_NAME`

Render tworzy PostgreSQL i przekazuje `DATABASE_URL`.

## 4. Administrator

Przy starcie `bootstrap_admin.py` utworzy administratora tylko wtedy,
gdy konto o podanym `ADMIN_EMAIL` jeszcze nie istnieje.

Hasło nie jest ponownie nadpisywane przy każdym restarcie.

## 5. Health check / UptimeRobot

Endpoint:

`https://twoja-domena.pl/health`

Prawidłowa odpowiedź ma status HTTP 200.

W UptimeRobot utwórz monitor HTTP(S) dla tego adresu.

## 6. Własna domena i Cloudflare

Po wdrożeniu w Render:
1. dodaj własną domenę w ustawieniach usługi Render,
2. ustaw rekord DNS zgodnie z informacją Render,
3. możesz prowadzić DNS przez Cloudflare.

## 7. Pliki

Lokalnie:
`STORAGE_BACKEND=local`

Na Render:
`STORAGE_BACKEND=r2`

Kod aplikacji jest ten sam — zmienia się tylko konfiguracja.
