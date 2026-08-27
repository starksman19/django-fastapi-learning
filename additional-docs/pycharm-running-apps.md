# Uruchamianie aplikacji z PyCharma

Ten dokument zakłada, że repozytorium zostało otwarte w PyCharmie, zależności
zostały zsynchronizowane przez `uv`, a interpreter projektu wskazuje na:

```text
C:\Users\barte\PycharmProjects\django-fastapi-learning\.venv\Scripts\python.exe
```

Najwygodniejszy wariant do pracy z debuggerem wygląda następująco:

- bazy PostgreSQL działają w Dockerze,
- Django i FastAPI są uruchamiane bezpośrednio z PyCharma,
- każda aplikacja ma własną konfigurację Run/Debug.

## 1. Uruchomienie baz danych

Otwórz terminal PyCharma w katalogu głównym repozytorium. Jeżeli wcześniej
uruchomiłeś całe API w Dockerze, zatrzymaj kontenery aplikacji, aby nie zajmowały
portów `8001` i `8002`:

```powershell
docker compose stop inventory-api appointments-api
docker compose up -d inventory-db appointments-db
docker compose ps
```

Bazy będą dostępne pod następującymi adresami:

| Aplikacja | Adres bazy |
| --- | --- |
| Inventory — Django DRF | `localhost:5433` |
| Appointments — FastAPI | `localhost:5434` |

## 2. Konfiguracja Run/Debug dla Django

W PyCharmie wybierz **Run → Edit Configurations**, kliknij **+**, a następnie
wybierz **uv run**. Ustaw następujące wartości:

| Pole | Wartość |
| --- | --- |
| Name | `Inventory Django` |
| Run | `Script` |
| Script | `$PROJECT_DIR$/reference/inventory-django/manage.py` |
| Arguments | `runserver 127.0.0.1:8001` |
| Python Interpreter | interpreter `.venv` z katalogu głównego repozytorium |
| uv arguments | `--package inventory-django` |

W polu **Environment variables** dodaj:

```text
POSTGRES_HOST=localhost;POSTGRES_PORT=5433;POSTGRES_DB=inventory_reference;POSTGRES_USER=inventory;POSTGRES_PASSWORD=inventory-dev-password;INVENTORY_API_KEY=dev-inventory-api-key;DJANGO_SECRET_KEY=unsafe-development-only-secret;DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1;DJANGO_DEBUG=true
```

Przy pierwszym uruchomieniu nowej bazy wykonaj migracje w terminalu PyCharma:

```powershell
$env:POSTGRES_HOST="localhost"
$env:POSTGRES_PORT="5433"
$env:POSTGRES_DB="inventory_reference"
$env:POSTGRES_USER="inventory"
$env:POSTGRES_PASSWORD="inventory-dev-password"

uv run --package inventory-django python reference/inventory-django/manage.py migrate
```

Następnie uruchom konfigurację **Inventory Django** zielonym przyciskiem Run
albo użyj Debug, jeżeli chcesz korzystać z breakpointów.

Dokumentacja API będzie dostępna pod adresem:

```text
http://localhost:8001/api/docs/
```

## 3. Konfiguracja Run/Debug dla FastAPI

Ponownie wybierz **Run → Edit Configurations**, kliknij **+** i wybierz
**uv run**. Ustaw:

| Pole | Wartość |
| --- | --- |
| Name | `Appointments FastAPI` |
| Run | `Module` |
| Module | `uvicorn` |
| Arguments | `app.main:app --reload --host 127.0.0.1 --port 8002` |
| Python Interpreter | interpreter `.venv` z katalogu głównego repozytorium |
| uv arguments | `--package appointments-fastapi --directory $PROJECT_DIR$/reference/appointments-fastapi` |

W polu **Environment variables** dodaj:

```text
DATABASE_URL=postgresql+psycopg://appointments:appointments-dev-password@localhost:5434/appointments_reference;APPOINTMENTS_API_KEY=dev-appointments-api-key
```

Przy pierwszym uruchomieniu nowej bazy wykonaj migracje Alembic:

```powershell
$env:DATABASE_URL="postgresql+psycopg://appointments:appointments-dev-password@localhost:5434/appointments_reference"
$env:APPOINTMENTS_API_KEY="dev-appointments-api-key"

uv run --package appointments-fastapi --directory reference/appointments-fastapi alembic upgrade head
```

Następnie uruchom konfigurację **Appointments FastAPI** przez Run albo Debug.

Dokumentacja API będzie dostępna pod adresem:

```text
http://localhost:8002/docs
```

## 4. Uruchamianie aplikacji z terminala

Konfiguracje PyCharma nie są wymagane. Te same aplikacje można uruchomić z
terminala po ustawieniu opisanych wyżej zmiennych środowiskowych.

Django:

```powershell
uv run --package inventory-django python reference/inventory-django/manage.py runserver 127.0.0.1:8001
```

FastAPI, w osobnym terminalu:

```powershell
uv run --package appointments-fastapi --directory reference/appointments-fastapi uvicorn app.main:app --reload --host 127.0.0.1 --port 8002
```

Każda aplikacja zajmuje terminal, w którym została uruchomiona. Zatrzymasz ją
skrótem `Ctrl+C`.

## 5. Alternatywa: całe środowisko w Dockerze

Jeżeli nie potrzebujesz debuggera PyCharma, możesz uruchomić obie bazy i obie
aplikacje w Dockerze:

```powershell
docker compose up --build -d
docker compose ps
```

Podgląd logów:

```powershell
docker compose logs -f inventory-api
docker compose logs -f appointments-api
```

Zatrzymanie całego środowiska:

```powershell
docker compose down
```

Polecenie `docker compose down` zachowuje dane zapisane w wolumenach baz.
