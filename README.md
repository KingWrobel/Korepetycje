# JW Korepetycje — V4

V4 zachowuje funkcje V3 i dodaje przygotowanie do publikacji.

## Najważniejsze zmiany

- PostgreSQL przez `DATABASE_URL`,
- Cloudflare R2 do plików,
- lokalny storage podczas pracy w VS Code,
- migracje bazy danych przez Flask-Migrate,
- ochrona CSRF formularzy,
- bezpieczniejsze cookies w produkcji,
- `/health` dla UptimeRobot / Render,
- `render.yaml`,
- administrator tworzony ze zmiennych środowiskowych,
- pliki `.env`,
- skrypty Windows, które używają bezpośrednio `.venv`
  i nie uruchamiają przypadkiem Anacondy.

## Najprostsze uruchomienie na Windows

W folderze projektu uruchom:

```text
setup_windows.bat
```

Potem:

```text
run_windows.bat
```

Strona:
`http://127.0.0.1:5000`

Health check:
`http://127.0.0.1:5000/health`

## Ręczne uruchomienie

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
.\.venv\Scripts\python.exe -m flask --app app db upgrade
.\.venv\Scripts\python.exe seed.py
.\.venv\Scripts\python.exe app.py
```

## Przeniesienie lokalnych danych z V3

Jeżeli V3 zawiera już ważne dane:

1. Skopiuj `instance/korepetycje.db` z V3 do folderu `instance` w V4.
2. Nie wykonuj na tej skopiowanej bazie `db upgrade`, bo V3 ma już te tabele.
3. Zamiast tego wykonaj:

```powershell
.\.venv\Scripts\python.exe -m flask --app app db stamp 0001_initial
```

Od tego momentu przyszłe migracje będą działały normalnie.

Pliki z folderu `uploads` V3 możesz również skopiować do `uploads` V4.

## Produkcja

Do wdrożenia używany jest `render.yaml`.

Przed wdrożeniem przygotuj:
- repozytorium GitHub,
- bucket Cloudflare R2,
- R2 API Token / Access Keys.

W Render ustaw:
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`
- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET_NAME`

`DATABASE_URL` i `SECRET_KEY` obsługuje blueprint Rendera.

Szczegóły są w `DEPLOY_RENDER_R2.md`.
