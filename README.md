# Django & FastAPI Microservices Learning Lab

Monorepo zawiera dwie kompletne, różne aplikacje referencyjne oraz dwa puste
obszary przeznaczone na ich samodzielne porty do przeciwnego frameworka.

| Domena | Gotowa implementacja referencyjna | Samodzielny port |
| --- | --- | --- |
| Inventory & Orders | Django REST Framework + Django ORM | FastAPI + SQLAlchemy + Alembic |
| Appointments | FastAPI + SQLAlchemy + Alembic | Django REST Framework + Django ORM |

Implementacje referencyjne są gotowymi backendami z PostgreSQL, migracjami,
testami, healthcheckami i Dockerfile. Katalogi `ports/` celowo zawierają tylko
README. Kod aplikacji, modele, migracje, testy, Dockerfile i konfigurację Docker
Compose dla portów należy przygotować samodzielnie.

## Co znajduje się w repozytorium

```text
.
├── pyproject.toml             # workspace uv i wspólna konfiguracja Ruff
├── uv.lock                    # jeden lockfile dla wszystkich części repo
├── .pre-commit-config.yaml
├── compose.yaml
├── .env.example
├── reference/
│   ├── inventory-django/       # kompletne Inventory & Orders w Django DRF
│   └── appointments-fastapi/   # kompletne Appointments w FastAPI
├── ports/
│   ├── inventory-fastapi/      # tylko README; port wykonujesz samodzielnie
│   └── appointments-django/    # tylko README; port wykonujesz samodzielnie
└── contract-tests/
    ├── inventory/              # wspólny kontrakt Inventory po HTTP
    └── appointments/           # wspólny kontrakt Appointments po HTTP
```

Szczegółowe opisy:

- [Inventory & Orders — Django DRF](reference/inventory-django/README.md),
- [Appointments — FastAPI i SQLAlchemy](reference/appointments-fastapi/README.md),
- [zadanie: port Inventory do FastAPI](ports/inventory-fastapi/README.md),
- [zadanie: port Appointments do Django](ports/appointments-django/README.md),
- [połączenie z bazami PostgreSQL w DBeaver](additional-docs/db-connection.md).

## Zależności i jakość kodu

Repozytorium jest workspace'em `uv`. Każda implementacja i testy kontraktowe
mają własny `pyproject.toml`, ale wszystkie korzystają z jednego `uv.lock` w
katalogu głównym. Katalogi `ports/` nie są członkami workspace'u, ponieważ ich
konfigurację tworzysz samodzielnie w ramach ćwiczenia.

Instalacja wszystkich zależności do lokalnego `.venv`:

```bash
uv sync --all-packages
```

Ruff ma długość linii ustawioną na 100 znaków. Kontrole można uruchomić bez
aktywowania środowiska:

```bash
uv run ruff check .
uv run ruff format --check .
```

Jednorazowa instalacja hooków i ręczne sprawdzenie całego repozytorium:

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

Po zmianie zależności uruchom `uv lock` i dodaj zaktualizowany `uv.lock` do
commita. Docker również instaluje pakiety z tego lockfile'a.

## Szybki start

Wymagania do uruchomienia całego środowiska: Docker z obsługą Compose. `uv` jest
potrzebny wyłącznie do lokalnej pracy z Pythonem i narzędziami jakości.

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
```

Na Windows plik środowiskowy można skopiować poleceniem:

```powershell
Copy-Item .env.example .env
```

Po przejściu healthchecków dostępne są:

| Usługa | Adres | Dokumentacja |
| --- | --- | --- |
| Inventory Django | `http://localhost:8001` | `http://localhost:8001/api/docs/` |
| Appointments FastAPI | `http://localhost:8002` | `http://localhost:8002/docs` |
| PostgreSQL Inventory | `localhost:5433` | baza `inventory_reference` |
| PostgreSQL Appointments | `localhost:5434` | baza `appointments_reference` |

Lokalne, demonstracyjne klucze API pochodzą z `.env.example`:

- Inventory: `X-API-Key: dev-inventory-api-key`,
- Appointments: `X-API-Key: dev-appointments-api-key`.

Są to wyłącznie wartości laboratoryjne. W innym środowisku należy je zmienić i
nie commitować pliku `.env`.

## Testy

### Testy kontraktowe

Testy w `contract-tests/` komunikują się wyłącznie po HTTP. Adresy usług i
klucze są przekazywane przez zmienne środowiskowe, dlatego ten sam zestaw można
uruchomić przeciwko implementacji referencyjnej albo portowi.

Przy działających usługach:

```bash
docker compose --profile tests run --rm contract-tests
```

Pełny przebieg od budowania obrazów po wynik testów:

```bash
docker compose --profile tests up --build --abort-on-container-exit --exit-code-from contract-tests
```

Testy obejmują uwierzytelnianie, format błędów, idempotencję, maszyny stanów i
dwa najważniejsze przypadki współbieżności:

- dwóch klientów próbuje kupić ostatnią sztukę produktu,
- dwóch klientów próbuje zarezerwować ten sam termin.

### Testy jednej implementacji

```bash
docker compose --profile app-tests run --rm inventory-tests
docker compose --profile app-tests run --rm appointments-tests
```

Usługi testowe korzystają z osobnych targetów Dockerfile zawierających
zależności developerskie. Obrazy uruchomieniowe API pozostają bez `pytest`.

Testy współbieżności korzystają z niezależnych połączeń do prawdziwego
PostgreSQL. SQLite nie jest używany jako zamiennik, ponieważ nie odwzorowałby
blokad i constraintów wymaganych przez te scenariusze.

## Dwie niezależne bazy

Każda implementacja referencyjna posiada własną bazę i własną historię
migracji:

- Django zarządza bazą `inventory_reference` przez Django migrations,
- FastAPI zarządza bazą `appointments_reference` przez Alembic.

Usługi nie współdzielą tabel i nie odczytują wzajemnie swoich danych. Po
ukończeniu portów powinny powstać kolejne dwie odizolowane bazy. Ostatecznie
laboratorium będzie więc uruchamiać cztery backendy i cztery bazy PostgreSQL.

PostgreSQL jest wymagany ze względu na:

- transakcje i blokady wierszy,
- równoległe zapisy,
- constraint wykluczający nakładające się terminy,
- indeksy częściowe i złożone,
- ograniczenia `UNIQUE` i `CHECK`,
- możliwość analizy zapytań przez `EXPLAIN ANALYZE`.

## Jak pracować z portami

1. Uruchom implementację referencyjną i poznaj jej kontrakt po HTTP.
2. Przeczytaj README wybranego portu, ale nie kopiuj architektury wewnętrznej.
3. W katalogu `ports/` utwórz od zera projekt w drugim frameworku.
4. Samodzielnie napisz modele, migracje, transakcje, testy i obsługę błędów.
5. Samodzielnie przygotuj Dockerfile, bazę i konfigurację Docker Compose portu.
6. Skieruj wspólne testy kontraktowe na port.
7. Porównaj zachowanie, liczbę zapytań, plany wykonania i ergonomię obu ORM.

Port nie musi mieć takiej samej architektury modułów jak wersja referencyjna.
Musi natomiast zachowywać się tak samo dla klienta HTTP i chronić te same
niezmienniki w bazie.

## Zakres edukacyjny

Repozytorium pokazuje zarówno podstawy, jak i zagadnienia produkcyjne:

- CRUD, walidację, serializację i OpenAPI,
- filtrowanie, wyszukiwanie, sortowanie i paginację,
- dependency injection i zarządzanie sesją,
- relacje ORM i problem N+1,
- migracje i rollback,
- indeksy zwykłe, złożone i częściowe,
- constraints jako ostatnią linię ochrony danych,
- granice transakcji i blokady wierszy,
- idempotencję,
- maszyny stanów,
- strefy czasowe,
- testowanie prawdziwej współbieżności,
- kontenery, healthchecki i izolację baz.

## Zatrzymanie środowiska

```bash
docker compose down
```

Usunięcie także lokalnych wolumenów baz danych:

```bash
docker compose down -v
```
