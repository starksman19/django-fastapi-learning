# Ściąga: struktura Dockerfile i Docker Compose

## Najważniejsze rozróżnienie

- `Dockerfile` opisuje, jak zbudować jeden obraz, na przykład obraz API.
- `compose.yaml` opisuje, jakie kontenery uruchomić i jak je ze sobą połączyć.

Gotowy PostgreSQL ma już obraz `postgres:16-alpine`, więc nie wymaga naszego
Dockerfile. Własny kod Django lub FastAPI trzeba umieścić we własnym obrazie,
dlatego każda aplikacja referencyjna ma Dockerfile.

## Podstawowa struktura Dockerfile

Minimalny przykład dla aplikacji Python:

```dockerfile
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.6 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Docker wykonuje instrukcje od góry do dołu. Każda instrukcja budująca tworzy
warstwę obrazu, którą Docker może później pobrać z cache.

### Najczęściej używane instrukcje

| Instrukcja | Znaczenie |
| --- | --- |
| `FROM python:3.12-slim` | Wybiera obraz bazowy. Od tej warstwy zaczyna się budowa. |
| `FROM ... AS runtime` | Nadaje etapowi nazwę używaną w buildzie wieloetapowym. |
| `WORKDIR /app` | Ustawia katalog roboczy dla kolejnych instrukcji i procesu. |
| `COPY źródło cel` | Kopiuje pliki z kontekstu budowania do obrazu. |
| `COPY --from=...` | Kopiuje plik z innego obrazu albo wcześniejszego etapu. |
| `RUN polecenie` | Wykonuje polecenie podczas budowania obrazu. |
| `ENV NAZWA=wartość` | Ustawia zmienną środowiskową w obrazie. |
| `USER app` | Uruchamia kolejne instrukcje i proces jako wskazany użytkownik. |
| `EXPOSE 8000` | Dokumentuje port aplikacji wewnątrz kontenera. |
| `CMD [...]` | Ustawia domyślne polecenie wykonywane po uruchomieniu kontenera. |
| `ENTRYPOINT [...]` | Ustawia stały program startowy, do którego trafiają argumenty. |

`RUN` działa w czasie budowania obrazu, natomiast `CMD` działa dopiero podczas
uruchamiania kontenera.

`EXPOSE` nie udostępnia portu na komputerze. Mapowanie portu wykonuje dopiero
sekcja `ports` w Compose lub opcja `docker run -p`.

## Kolejność kopiowania plików

Najpierw kopiuj pliki zależności i instaluj paczki, a kod aplikacji dopiero
później:

```dockerfile
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app app
```

Dzięki temu zmiana kodu aplikacji nie wymusza ponownego instalowania wszystkich
zależności. Warstwa z zależnościami może zostać pobrana z cache.

Plik `.dockerignore` określa, czego Docker nie powinien wysyłać do kontekstu
budowania, na przykład `.git`, `.venv`, cache i plików IDE.

## Build wieloetapowy

Dockerfile może tworzyć kilka wariantów obrazu:

```dockerfile
FROM python:3.12-slim AS runtime

# instalacja wyłącznie zależności potrzebnych aplikacji

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS test

# doinstalowanie zależności developerskich

CMD ["pytest", "-ra"]
```

W tym repozytorium etap `runtime` nie zawiera `pytest`, a etap `test` rozszerza
go o zależności testowe. Compose wybiera etap przez:

```yaml
build:
  target: runtime
```

albo:

```yaml
build:
  target: test
```

## Podstawowa struktura compose.yaml

Minimalny zestaw API i bazy może wyglądać tak:

```yaml
name: example-project

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: example
      POSTGRES_USER: example
      POSTGRES_PASSWORD: development-password
    ports:
      - "5433:5432"
    volumes:
      - db-data:/var/lib/postgresql/data

  api:
    build:
      context: .
      dockerfile: app/Dockerfile
      target: runtime
    environment:
      POSTGRES_HOST: db
      POSTGRES_PORT: "5432"
    ports:
      - "8001:8000"
    depends_on:
      - db

volumes:
  db-data:
```

### Najważniejsze elementy Compose

| Element | Znaczenie |
| --- | --- |
| `name` | Nazwa całego projektu Compose. Jest częścią automatycznych nazw zasobów. |
| `services` | Lista usług, z których powstaną kontenery. |
| `image` | Gotowy obraz i jego tag, na przykład `postgres:16-alpine`. |
| `build` | Instrukcja zbudowania własnego obrazu z Dockerfile. |
| `build.context` | Katalog dostępny dla instrukcji `COPY` podczas budowania. |
| `build.dockerfile` | Położenie Dockerfile względem kontekstu budowania. |
| `build.target` | Etap wieloetapowego Dockerfile, który ma zostać zbudowany. |
| `environment` | Zmienne przekazywane do procesu działającego w kontenerze. |
| `command` | Polecenie startowe zastępujące `CMD` z Dockerfile. |
| `ports` | Mapowanie portów w formacie `port_hosta:port_kontenera`. |
| `volumes` | Trwałe dane albo pliki montowane w kontenerze. |
| `depends_on` | Zależność kolejności uruchamiania usług. |
| `healthcheck` | Polecenie sprawdzające, czy usługa jest gotowa do pracy. |
| `profiles` | Usługi opcjonalne, uruchamiane tylko ze wskazanym profilem. |

## Kontekst budowania

W tym repozytorium API ma konfigurację:

```yaml
build:
  context: .
  dockerfile: reference/inventory-django/Dockerfile
```

`context: .` oznacza katalog główny repozytorium. Dlatego instrukcje `COPY` w
Dockerfile używają ścieżek względem katalogu głównego, a nie względem katalogu,
w którym znajduje się Dockerfile.

Dockerfile nie może kopiować plików znajdujących się poza swoim kontekstem
budowania.

## Port hosta i port kontenera

```yaml
ports:
  - "8001:8000"
```

- `8001` to port na Windowsie, na przykład `http://localhost:8001`.
- `8000` to port procesu działającego wewnątrz kontenera.

Kontenery komunikują się między sobą przez port wewnętrzny. Dlatego inne usługi
łączą się z API przez `inventory-api:8000`, a nie przez `localhost:8001`.

## Nazwy usług jako adresy sieciowe

Compose automatycznie tworzy wspólną sieć i DNS. Nazwa usługi staje się nazwą
hosta:

```yaml
services:
  inventory-db:
    image: postgres:16-alpine

  inventory-api:
    environment:
      POSTGRES_HOST: inventory-db
```

Wewnątrz kontenera `localhost` oznacza ten konkretny kontener. API musi więc
łączyć się z bazą przez nazwę usługi `inventory-db`.

## Zmienne z pliku .env

Zapis:

```yaml
POSTGRES_PASSWORD: ${INVENTORY_DB_PASSWORD:-inventory-dev-password}
```

oznacza:

- użyj `INVENTORY_DB_PASSWORD` z systemu albo pliku `.env`, jeżeli istnieje,
- w przeciwnym razie użyj wartości `inventory-dev-password`.

Sekretów produkcyjnych nie należy wpisywać do Dockerfile, obrazu ani
commitowanego pliku Compose. Wartości z tego repozytorium są wyłącznie lokalnymi
danymi developerskimi.

## Dane trwałe w wolumenach

```yaml
services:
  db:
    volumes:
      - db-data:/var/lib/postgresql/data

volumes:
  db-data:
```

`db-data` jest nazwanym wolumenem zarządzanym przez Dockera. Dane PostgreSQL
przetrwają usunięcie i ponowne utworzenie kontenera przez `docker compose down`.
Usunie je dopiero `docker compose down -v`.

## Oczekiwanie na gotowość usługi

Samo uruchomienie kontenera PostgreSQL nie oznacza jeszcze, że baza przyjmuje
połączenia. Dlatego baza ma `healthcheck`, a API może poczekać na stan `healthy`:

```yaml
depends_on:
  inventory-db:
    condition: service_healthy
```

Bez healthchecka `depends_on` pilnuje głównie kolejności uruchomienia, ale nie
gwarantuje, że baza zakończyła inicjalizację.

## Krótka kolejność pisania plików

1. Wybierz mały, oficjalny obraz bazowy w `FROM`.
2. Ustaw `WORKDIR` i potrzebne zmienne `ENV`.
3. Skopiuj pliki zależności i zainstaluj paczki.
4. Skopiuj kod aplikacji.
5. Uruchamiaj aplikację jako użytkownik bez uprawnień administratora.
6. Ustaw domyślne `CMD` i udokumentuj port przez `EXPOSE`.
7. W `compose.yaml` dodaj bazę przez `image`, a API przez `build`.
8. Dodaj zmienne, porty, wolumeny, healthcheck i `depends_on`.
9. Sprawdź konfigurację poleceniem `docker compose config`.
10. Zbuduj i uruchom środowisko przez `docker compose up --build -d`.

Więcej komend znajduje się w dokumencie
[Ściąga z przydatnych komend Dockera](docker-command-cheatsheet.md).

# Kompletne przykłady z komentarzami

Poniższe przykłady odpowiadają plikom używanym w tym repozytorium. Komentarze
zaczynające się od `#` są częścią przykładów edukacyjnych i można je pozostawić
w plikach — Docker oraz Docker Compose je ignorują.

Puste linie służą tylko do podziału pliku na czytelne sekcje.

## Dockerfile aplikacji Django — instrukcja po instrukcji

Oryginalny plik znajduje się w
`reference/inventory-django/Dockerfile`.

```dockerfile
# Używa lekkiego obrazu z Pythonem 3.12 i nazywa pierwszy etap "runtime".
FROM python:3.12-slim AS runtime

# Kopiuje programy uv i uvx z oficjalnego obrazu uv do katalogu /bin.
# Nie trzeba dzięki temu instalować uv przez pip.
COPY --from=ghcr.io/astral-sh/uv:0.12.6 /uv /uvx /bin/

# Nie zapisuje plików .pyc w kontenerze.
# Wyłącza buforowanie stdout/stderr, aby logi pojawiały się od razu.
# Nakazuje uv utworzyć środowisko w /opt/venv.
# Dodaje programy z tego środowiska, np. gunicorn i pytest, do PATH.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Ustawia główny katalog roboczy dla kolejnych instrukcji.
WORKDIR /workspace

# Tworzy systemową grupę i użytkownika app bez uprawnień administratora.
RUN addgroup --system app && adduser --system --ingroup app app

# Kopiuje główny pyproject.toml workspace'a i jego zablokowane wersje paczek.
COPY pyproject.toml uv.lock ./

# Kopiuje metadane wszystkich członków workspace'a.
# uv potrzebuje ich do poprawnego odczytania wspólnego pliku uv.lock.
COPY reference/inventory-django/pyproject.toml reference/inventory-django/pyproject.toml
COPY reference/appointments-fastapi/pyproject.toml reference/appointments-fastapi/pyproject.toml
COPY contract-tests/pyproject.toml contract-tests/pyproject.toml

# Instaluje zależności produkcyjne aplikacji inventory-django.
# --frozen zabrania zmiany uv.lock.
# --no-dev pomija zależności developerskie, takie jak pytest.
# --package wybiera jeden projekt z workspace'a.
# --no-install-workspace instaluje zależności przed skopiowaniem kodu aplikacji.
# --compile-bytecode kompiluje kod zależności do bytecode podczas budowania.
RUN uv sync \
    --frozen \
    --no-dev \
    --package inventory-django \
    --no-install-workspace \
    --compile-bytecode

# Kopiuje kod Django do obrazu po zainstalowaniu zależności.
COPY reference/inventory-django reference/inventory-django

# Przekazuje użytkownikowi app prawa do katalogu aplikacji.
RUN chown -R app:app /workspace/reference/inventory-django

# Od tej chwili polecenia są wykonywane w katalogu projektu Django.
WORKDIR /workspace/reference/inventory-django

# Proces aplikacji nie będzie działał jako root.
USER app

# Dokumentuje, że aplikacja nasłuchuje w kontenerze na porcie 8000.
EXPOSE 8000

# Domyślne polecenie uruchamiające Django przez serwer Gunicorn.
# config.wsgi:application wskazuje obiekt WSGI Django.
# 0.0.0.0 pozwala przyjmować połączenia spoza kontenera.
# Pozostałe parametry konfigurują procesy, wątki i timeout.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "60"]

# Rozpoczyna etap testowy, dziedziczący wszystko z etapu runtime.
FROM runtime AS test

# Tymczasowo wraca do roota, aby zmodyfikować środowisko /opt/venv.
USER root

# Ponownie synchronizuje paczki, ale bez --no-dev.
# Dzięki temu etap testowy otrzymuje pytest i pytest-django.
RUN uv sync \
    --frozen \
    --package inventory-django \
    --no-install-workspace \
    --compile-bytecode

# Testy również są uruchamiane jako użytkownik bez uprawnień administratora.
USER app

# Domyślnym poleceniem etapu testowego jest uruchomienie testów.
# -ra pokazuje krótkie podsumowanie testów pominiętych i nieudanych.
CMD ["pytest", "-ra"]
```

Compose buduje etap `runtime` dla działającego API oraz etap `test` dla usługi
`inventory-tests`. Dzięki temu obraz produkcyjny nie zawiera narzędzi testowych.

## Dockerfile aplikacji FastAPI — instrukcja po instrukcji

Oryginalny plik znajduje się w
`reference/appointments-fastapi/Dockerfile`.

```dockerfile
# Rozpoczyna produkcyjny etap runtime na bazie lekkiego obrazu Pythona 3.12.
FROM python:3.12-slim AS runtime

# Pobiera gotowe programy uv i uvx z oficjalnego obrazu Astral.
COPY --from=ghcr.io/astral-sh/uv:0.12.6 /uv /uvx /bin/

# Wyłącza pliki .pyc, włącza natychmiastowe logi i konfiguruje środowisko uv.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Ustawia katalog roboczy workspace'a.
WORKDIR /workspace

# Tworzy użytkownika app, aby API nie działało jako root.
RUN addgroup --system app && adduser --system --ingroup app app

# Kopiuje konfigurację głównego workspace'a i lockfile.
COPY pyproject.toml uv.lock ./

# Kopiuje pliki pyproject członków workspace'a wymagane do odczytania uv.lock.
COPY reference/inventory-django/pyproject.toml reference/inventory-django/pyproject.toml
COPY reference/appointments-fastapi/pyproject.toml reference/appointments-fastapi/pyproject.toml
COPY contract-tests/pyproject.toml contract-tests/pyproject.toml

# Instaluje wyłącznie produkcyjne zależności projektu appointments-fastapi.
# Znaczenie flag jest takie samo jak w Dockerfile Django.
RUN uv sync \
    --frozen \
    --no-dev \
    --package appointments-fastapi \
    --no-install-workspace \
    --compile-bytecode

# Kopiuje kod FastAPI i migracje Alembic do obrazu.
COPY reference/appointments-fastapi reference/appointments-fastapi

# Nadaje użytkownikowi app prawa do katalogu projektu.
RUN chown -R app:app /workspace/reference/appointments-fastapi

# Ustawia katalog FastAPI jako bieżący katalog procesu.
WORKDIR /workspace/reference/appointments-fastapi

# Przełącza wykonywanie na użytkownika bez uprawnień administratora.
USER app

# Dokumentuje wewnętrzny port aplikacji.
EXPOSE 8000

# Uruchamia obiekt app z modułu app.main przez serwer Uvicorn.
# Serwer nasłuchuje na wszystkich interfejsach kontenera i używa dwóch workerów.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

# Tworzy wariant testowy na podstawie kompletnego etapu runtime.
FROM runtime AS test

# Root jest potrzebny jedynie do zmiany zawartości środowiska /opt/venv.
USER root

# Instaluje także grupę dev, zawierającą pytest i httpx.
RUN uv sync \
    --frozen \
    --package appointments-fastapi \
    --no-install-workspace \
    --compile-bytecode

# Testy nie wymagają działania jako root.
USER app

# Ustawia pytest jako domyślne polecenie obrazu testowego.
CMD ["pytest", "-ra"]
```

Dockerfile FastAPI ma tę samą konstrukcję co Dockerfile Django. Różnią się
wybieranym pakietem, kopiowanym katalogiem i poleceniem uruchamiającym serwer.

## Docker Compose — sekcja po sekcji i linia po linii

Poniżej znajduje się komentowany odpowiednik głównego `compose.yaml`. Wcięcia
są częścią składni YAML: element wcięty należy do elementu znajdującego się nad
nim.

```yaml
# Ustawia nazwę całego projektu Compose.
name: django-fastapi-learning

# Rozpoczyna słownik wszystkich usług, z których powstaną kontenery.
services:
  # Definiuje usługę pierwszej bazy PostgreSQL.
  inventory-db:
    # Używa gotowego obrazu postgres z tagiem 16-alpine.
    image: postgres:16-alpine

    # Przekazuje zmienne do skryptu startowego obrazu PostgreSQL.
    environment:
      # Tworzy bazę o tej nazwie przy pierwszym uruchomieniu pustego wolumenu.
      POSTGRES_DB: inventory_reference
      # Tworzy użytkownika bazy.
      POSTGRES_USER: inventory
      # Czyta hasło z .env, a po jego braku używa wartości developerskiej.
      POSTGRES_PASSWORD: ${INVENTORY_DB_PASSWORD:-inventory-dev-password}

    # Udostępnia port 5432 kontenera jako port 5433 na Windowsie.
    ports:
      - "5433:5432"

    # Montuje nazwany wolumen w katalogu danych PostgreSQL.
    volumes:
      - inventory-db-data:/var/lib/postgresql/data

    # Określa sposób sprawdzania gotowości bazy.
    healthcheck:
      # pg_isready sprawdza, czy PostgreSQL przyjmuje połączenia.
      # CMD-SHELL pozwala wykonać polecenie przez powłokę kontenera.
      test: ["CMD-SHELL", "pg_isready -U inventory -d inventory_reference"]
      # Kolejne próby są wykonywane co 3 sekundy.
      interval: 3s
      # Jedna próba może trwać maksymalnie 3 sekundy.
      timeout: 3s
      # Po 20 nieudanych próbach kontener otrzyma stan unhealthy.
      retries: 20

  # Definiuje usługę API Inventory napisanego w Django.
  inventory-api:
    # Zamiast gotowego image Compose zbuduje nasz obraz.
    build:
      # Kontekstem budowania jest katalog główny repozytorium.
      context: .
      # Wskazuje Dockerfile Django względem kontekstu.
      dockerfile: reference/inventory-django/Dockerfile
      # Buduje produkcyjny etap runtime, bez pytest.
      target: runtime

    # Przekazuje konfigurację do settings.py Django.
    environment:
      # inventory-db jest nazwą hosta bazy w sieci Compose.
      POSTGRES_HOST: inventory-db
      # Kontenery łączą się przez wewnętrzny port PostgreSQL.
      POSTGRES_PORT: "5432"
      POSTGRES_DB: inventory_reference
      POSTGRES_USER: inventory
      POSTGRES_PASSWORD: ${INVENTORY_DB_PASSWORD:-inventory-dev-password}
      INVENTORY_API_KEY: ${INVENTORY_API_KEY:-dev-inventory-api-key}
      DJANGO_SECRET_KEY: ${DJANGO_SECRET_KEY:-unsafe-development-only-secret}
      # Django akceptuje żądania wysłane pod tymi nazwami hostów.
      DJANGO_ALLOWED_HOSTS: localhost,127.0.0.1,inventory-api

    # Nadpisuje CMD z Dockerfile dla kontenera uruchamianego przez Compose.
    command:
      # Uruchamia powłokę sh.
      - sh
      # Przekazuje powłoce następną wartość jako tekst polecenia.
      - -c
      # Najpierw wykonuje migracje, a po sukcesie uruchamia Gunicorn.
      - python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --threads 4 --timeout 60

    # Udostępnia Django na Windowsie pod localhost:8001.
    ports:
      - "8001:8000"

    # Nie uruchamia API, dopóki inventory-db nie będzie healthy.
    depends_on:
      inventory-db:
        condition: service_healthy

    # Sprawdza endpoint zdrowia Django wewnątrz kontenera.
    healthcheck:
      # CMD uruchamia program bez dodatkowej powłoki.
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/', timeout=2)"]
      interval: 5s
      timeout: 3s
      retries: 20

  # Definiuje jednorazową usługę uruchamiającą testy Django.
  inventory-tests:
    # Usługa nie uruchamia się przy zwykłym docker compose up.
    profiles: ["app-tests"]

    # Buduje ten sam Dockerfile, ale wybiera etap test.
    build:
      context: .
      dockerfile: reference/inventory-django/Dockerfile
      target: test

    # Testy otrzymują oddzielny zestaw zmiennych środowiskowych.
    environment:
      POSTGRES_HOST: inventory-db
      POSTGRES_PORT: "5432"
      POSTGRES_DB: inventory_reference
      POSTGRES_USER: inventory
      POSTGRES_PASSWORD: ${INVENTORY_DB_PASSWORD:-inventory-dev-password}
      INVENTORY_API_KEY: ${INVENTORY_API_KEY:-dev-inventory-api-key}
      DJANGO_SECRET_KEY: ${DJANGO_SECRET_KEY:-unsafe-development-only-secret}
      DJANGO_ALLOWED_HOSTS: localhost,127.0.0.1,inventory-tests

    # Testy czekają na gotową bazę.
    depends_on:
      inventory-db:
        condition: service_healthy

    # Brak command oznacza użycie CMD ["pytest", "-ra"] z etapu test.

  # Definiuje drugą, niezależną bazę PostgreSQL.
  appointments-db:
    # Obie bazy używają tego samego gotowego obrazu.
    image: postgres:16-alpine

    # Inne wartości tworzą inną bazę i innego użytkownika.
    environment:
      POSTGRES_DB: appointments_reference
      POSTGRES_USER: appointments
      POSTGRES_PASSWORD: ${APPOINTMENTS_DB_PASSWORD:-appointments-dev-password}

    # Port 5434 hosta nie koliduje z portem pierwszej bazy.
    ports:
      - "5434:5432"

    # Drugi wolumen całkowicie oddziela dane obu baz.
    volumes:
      - appointments-db-data:/var/lib/postgresql/data

    # Sprawdza gotowość bazy Appointments.
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U appointments -d appointments_reference"]
      interval: 3s
      timeout: 3s
      retries: 20

  # Definiuje API Appointments napisane w FastAPI.
  appointments-api:
    # Buduje produkcyjny etap Dockerfile FastAPI.
    build:
      context: .
      dockerfile: reference/appointments-fastapi/Dockerfile
      target: runtime

    # Przekazuje URL połączenia SQLAlchemy i klucz API.
    environment:
      # appointments-db jest nazwą hosta, a 5432 portem wewnętrznym bazy.
      DATABASE_URL: postgresql+psycopg://appointments:${APPOINTMENTS_DB_PASSWORD:-appointments-dev-password}@appointments-db:5432/appointments_reference
      APPOINTMENTS_API_KEY: ${APPOINTMENTS_API_KEY:-dev-appointments-api-key}

    # Nadpisuje CMD z Dockerfile.
    command:
      - sh
      - -c
      # Najpierw aktualizuje bazę przez Alembic, potem uruchamia Uvicorn.
      - alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2

    # Udostępnia FastAPI na Windowsie pod localhost:8002.
    ports:
      - "8002:8000"

    # Czeka na zdrową bazę Appointments.
    depends_on:
      appointments-db:
        condition: service_healthy

    # Odpytuje endpoint zdrowia FastAPI.
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)"]
      interval: 5s
      timeout: 3s
      retries: 20

  # Definiuje jednorazową usługę testów FastAPI.
  appointments-tests:
    # Wymaga jawnego włączenia profilu app-tests.
    profiles: ["app-tests"]

    # Buduje etap zawierający pytest i httpx.
    build:
      context: .
      dockerfile: reference/appointments-fastapi/Dockerfile
      target: test

    # Testy łączą się z bazą Appointments przez sieć Compose.
    environment:
      DATABASE_URL: postgresql+psycopg://appointments:${APPOINTMENTS_DB_PASSWORD:-appointments-dev-password}@appointments-db:5432/appointments_reference
      APPOINTMENTS_API_KEY: ${APPOINTMENTS_API_KEY:-dev-appointments-api-key}

    # Nadpisuje CMD testowego Dockerfile, aby przed pytest wykonać migracje.
    command:
      - sh
      - -c
      - alembic upgrade head && pytest -ra

    # Uruchamia testy dopiero po przygotowaniu bazy.
    depends_on:
      appointments-db:
        condition: service_healthy

  # Definiuje testy kontraktowe wysyłające prawdziwe żądania HTTP do obu API.
  contract-tests:
    # Wymaga jawnego profilu tests.
    profiles: ["tests"]

    # Buduje osobny obraz z katalogu contract-tests.
    build:
      context: .
      dockerfile: contract-tests/Dockerfile

    # Przekazuje adresy obu usług widoczne w wewnętrznej sieci Compose.
    environment:
      INVENTORY_BASE_URL: http://inventory-api:8000
      INVENTORY_API_KEY: ${INVENTORY_API_KEY:-dev-inventory-api-key}
      APPOINTMENTS_BASE_URL: http://appointments-api:8000
      APPOINTMENTS_API_KEY: ${APPOINTMENTS_API_KEY:-dev-appointments-api-key}

    # Testy kontraktowe czekają, aż oba API przejdą healthcheck.
    depends_on:
      inventory-api:
        condition: service_healthy
      appointments-api:
        condition: service_healthy

# Deklaruje nazwane wolumeny użyte wcześniej przez usługi baz danych.
volumes:
  # Przechowuje pliki bazy Inventory niezależnie od kontenera.
  inventory-db-data:
  # Przechowuje pliki bazy Appointments niezależnie od kontenera.
  appointments-db-data:
```

## Jak czytać zależności całego zestawu

```text
inventory-db ────────→ inventory-api ────────┐
      └──────────────→ inventory-tests        │
                                              ├──→ contract-tests
appointments-db ─────→ appointments-api ─────┘
      └──────────────→ appointments-tests
```

Strzałka oznacza, że usługa po prawej potrzebuje zdrowej usługi po lewej.
Zwykłe `docker compose up` uruchamia bazy i API. Usługi testowe są przypisane do
profili, dlatego uruchamia się je osobnymi komendami opisanymi w ściądze z
komend Dockera.
