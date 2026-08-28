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
