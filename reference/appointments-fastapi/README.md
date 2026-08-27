# Appointments API — FastAPI, SQLAlchemy i Alembic

Kompletna implementacja referencyjna mikroserwisu rezerwacji wizyt. Serwis
pokazuje FastAPI, Pydantic, SQLAlchemy 2, Alembic i mechanizmy PostgreSQL,
których nie da się wiarygodnie zastąpić walidacją w pamięci.

## Odpowiedzialność serwisu

Serwis zarządza:

- specjalistami i ich strefami czasowymi,
- usługami oraz czasem ich trwania,
- tygodniowymi regułami dostępności,
- wyjątkami dla konkretnych dat,
- generowaniem wolnych terminów,
- rezerwacją, potwierdzaniem i anulowaniem wizyt,
- idempotencją i ochroną przed podwójną rezerwacją.

## Struktura implementacji

```text
app/
├── config.py             konfiguracja przez Pydantic Settings
├── database.py           engine, Session i dependency
├── models.py             modele SQLAlchemy, indeksy i constraints
├── schemas.py            modele wejściowe i wyjściowe Pydantic
├── security.py           dependency uwierzytelniające
├── errors.py             wspólny format błędów
├── services.py           transakcje, dostępność i idempotencja
├── routers/catalog.py    CRUD katalogu i kalendarza
├── routers/appointments.py  terminy i maszyna stanów
└── main.py               aplikacja FastAPI i healthcheck
alembic/                   środowisko i migracje
tests/                     testy integracyjne i współbieżności
Dockerfile                 obraz wyłącznie aplikacji referencyjnej
```

Sesja SQLAlchemy jest dostarczana przez dependency. Granice transakcji dla
rezerwacji i zmian stanu są jawne w warstwie serwisowej.

## Model danych

| Model | Znaczenie |
| --- | --- |
| `Specialist` | osoba świadcząca usługi wraz ze strefą IANA |
| `Service` | usługa specjalisty, czas trwania i cena |
| `AvailabilityRule` | powtarzalne okno dostępności dla dnia tygodnia |
| `AvailabilityException` | pełna niedostępność albo specjalne okno konkretnego dnia |
| `Appointment` | wizyta klienta, przedział czasu, status i idempotencja |

Dzień tygodnia używa konwencji Pythona: poniedziałek `0`, niedziela `6`.
`starts_on` i `ends_on` ograniczają okres obowiązywania reguły.

## Strefy czasowe i wolne terminy

Klient musi wysłać `starts_at` z offsetem, np. `2026-09-10T10:00:00+02:00`.
Wartości bez informacji o strefie są odrzucane. Aplikacja:

1. interpretuje dostępność w strefie IANA specjalisty,
2. sprawdza regułę albo wyjątek dla lokalnej daty,
3. zapisuje znaczniki jako `timestamptz`,
4. porównuje wizyty jako momenty w czasie,
5. generuje kandydatów co 15 minut z uwzględnieniem czasu trwania usługi.

Wyjątek dla daty zastępuje reguły tygodniowe. `available=false` zamyka cały
dzień; `available=true` wymaga własnego okna `start_time`–`end_time`.

## Ochrona przed podwójną rezerwacją

Wczesne zapytanie o kolizję daje czytelny błąd, ale nie wystarcza przy dwóch
równoległych transakcjach. Ostateczną ochroną jest PostgreSQL:

```sql
EXCLUDE USING gist (
  specialist_id WITH =,
  tstzrange(starts_at, ends_at, '[)') WITH &&
)
WHERE (status IN ('booked', 'confirmed'))
```

Migracja włącza rozszerzenie `btree_gist`. Dwie aktywne wizyty jednego
specjalisty nie mogą się nakładać, nawet gdy żądania trafiają równocześnie do
różnych procesów aplikacji. Wizyty anulowane nie blokują terminu dzięki
warunkowi częściowemu.

Klucz idempotencji jest serializowany blokadą advisory. Identyczne powtórzenie
zwraca wcześniejszą wizytę, a zmienione żądanie z tym samym kluczem zwraca
`409`.

## Maszyna stanów

```text
booked ──> confirmed ──> cancelled
   └──────────────────> cancelled
```

Ponowne potwierdzenie lub anulowanie do już osiągniętego stanu jest
idempotentne. Pozostałe przejścia są odrzucane.

## Indeksy i ograniczenia

| Element | Cel |
| --- | --- |
| `Specialist.email UNIQUE` | jednoznaczny specjalista |
| indeks `(active, name)` | listowanie aktywnych specjalistów |
| `(specialist_id, name) UNIQUE` | brak duplikatów usług |
| dodatni czas i nieujemna cena `CHECK` | poprawność usług |
| indeks `(specialist_id, weekday, active)` | wybór reguł dostępności |
| `(specialist_id, exception_date) UNIQUE` | jeden wyjątek dla daty |
| indeks `(specialist_id, starts_at)` | kalendarz specjalisty |
| częściowy indeks aktywnych wizyt | szybkie wyszukiwanie konfliktów |
| exclusion constraint GiST | atomowa ochrona przed nakładaniem wizyt |

## Uwierzytelnianie i błędy

Wszystkie endpointy poza `/health` wymagają:

```text
X-API-Key: dev-appointments-api-key
```

Każdy kontrolowany błąd ma format:

```json
{
  "error": {
    "code": "slot_unavailable",
    "message": "Wybrany termin jest już zajęty.",
    "details": null
  }
}
```

## Endpointy

| Metoda | Ścieżka | Znaczenie |
| --- | --- | --- |
| `GET` | `/health` | gotowość aplikacji i bazy |
| `GET, POST` | `/api/v1/specialists` | lista i tworzenie specjalistów |
| `GET, PATCH, DELETE` | `/api/v1/specialists/{id}` | szczegóły i modyfikacja |
| `GET, POST` | `/api/v1/services` | lista i tworzenie usług |
| `GET, PATCH, DELETE` | `/api/v1/services/{id}` | szczegóły i modyfikacja |
| `GET, POST` | `/api/v1/availability-rules` | reguły tygodniowe |
| `GET, PUT, DELETE` | `/api/v1/availability-rules/{id}` | szczegóły, zastąpienie i usunięcie reguły |
| `GET, POST` | `/api/v1/availability-exceptions` | wyjątki dat |
| `GET, PUT, DELETE` | `/api/v1/availability-exceptions/{id}` | szczegóły, zastąpienie i usunięcie wyjątku |
| `GET` | `/api/v1/available-slots?service_id=&day=` | wolne terminy usługi |
| `GET, POST` | `/api/v1/appointments` | lista i rezerwacja wizyty |
| `GET` | `/api/v1/appointments/{id}` | szczegóły wizyty |
| `POST` | `/api/v1/appointments/{id}/confirm` | potwierdzenie |
| `POST` | `/api/v1/appointments/{id}/cancel` | anulowanie |

Listy specjalistów, usług i wizyt obsługują `offset` i `limit`. Dodatkowe
parametry pozwalają filtrować po aktywności, specjaliście, statusie i adresie
klienta. Interaktywna dokumentacja wszystkich schema znajduje się pod `/docs`.

Rezerwacja wymaga `Idempotency-Key` i body:

```json
{
  "specialist_id": "UUID",
  "service_id": "UUID",
  "customer_name": "Jan Kowalski",
  "customer_email": "jan@example.com",
  "starts_at": "2026-09-10T10:00:00+02:00"
}
```

Po nowej rezerwacji FastAPI uruchamia małe zadanie w tle reprezentujące punkt
integracji z przyszłym systemem powiadomień. Zadanie nie wykonuje prawdziwej
wysyłki.

## Uruchamianie

Lokalne zależności instaluje `uv` na podstawie wspólnego lockfile'a:

```bash
uv sync --package appointments-fastapi
uv run --package appointments-fastapi --directory reference/appointments-fastapi alembic history
```

Do uruchomienia migracji i API nadal potrzebny jest PostgreSQL opisany w
`compose.yaml`.

Z katalogu głównego:

```bash
docker compose up --build -d appointments-db appointments-api
```

API: `http://localhost:8002`, Swagger UI: `http://localhost:8002/docs`.
Alembic wykonuje migracje przed uruchomieniem Uvicorna.

```bash
docker compose run --rm appointments-api alembic current
docker compose run --rm appointments-api alembic history
```

## Testy

```bash
docker compose --profile app-tests run --rm appointments-tests
```

Docker buduje wtedy target `test` z `pytest` i `httpx`; zwykły obraz
`appointments-api` zawiera tylko zależności uruchomieniowe.

Testy obejmują CRUD katalogu, reguły i wyjątki dostępności, ponowne zwolnienie
terminu po anulowaniu, uwierzytelnianie, idempotencję, maszynę stanów i dwie
równoległe próby rezerwacji tego samego terminu.

## Konfiguracja

| Zmienna | Znaczenie |
| --- | --- |
| `DATABASE_URL` | pełny URL SQLAlchemy do PostgreSQL przez psycopg |
| `APPOINTMENTS_API_KEY` | klucz wymagany przez API |

Wartości domyślne są przeznaczone wyłącznie do lokalnego laboratorium.
