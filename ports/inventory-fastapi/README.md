# Twoje zadanie: port Inventory & Orders do FastAPI

Ten katalog celowo zawiera wyłącznie ten dokument. Masz samodzielnie przepisać
[referencyjne Inventory w Django](../../reference/inventory-django/README.md)
na FastAPI, SQLAlchemy i Alembic.

Nie kopiuj kodu Django ani jego podziału na moduły. Źródłem prawdy są zachowanie
HTTP, opis domeny i testy kontraktowe.

## Co wykonujesz samodzielnie

- inicjalizację projektu FastAPI,
- modele Pydantic,
- modele i relacje SQLAlchemy,
- konfigurację sesji i dependency injection,
- migracje Alembic,
- routery i warstwę logiki biznesowej,
- filtrowanie, wyszukiwanie, sortowanie i paginację,
- uwierzytelnianie `X-API-Key`,
- spójny format błędów,
- transakcje, blokady i idempotencję,
- indeksy i constraints PostgreSQL,
- testy jednostkowe, integracyjne i współbieżności,
- healthcheck,
- własny Dockerfile,
- własną, odizolowaną bazę PostgreSQL,
- własne wpisy lub plik Docker Compose.

Repozytorium nie dostarcza dla tego portu szkieletu aplikacji ani gotowych
plików infrastruktury.

## Kontrakt do odtworzenia

Port ma zachować ścieżki z końcowym ukośnikiem:

| Metoda | Ścieżka |
| --- | --- |
| `GET` | `/health/` |
| `GET, POST` | `/api/v1/products/` |
| `GET, PATCH, PUT, DELETE` | `/api/v1/products/{id}/` |
| `GET, POST` | `/api/v1/warehouses/` |
| `GET, PATCH, PUT, DELETE` | `/api/v1/warehouses/{id}/` |
| `GET, POST` | `/api/v1/stocks/` |
| `GET, PATCH, PUT, DELETE` | `/api/v1/stocks/{id}/` |
| `GET, POST` | `/api/v1/orders/` |
| `GET` | `/api/v1/orders/{id}/` |
| `POST` | `/api/v1/orders/{id}/cancel/` |
| `POST` | `/api/v1/orders/{id}/complete/` |

Muszą zgadzać się:

- nazwy pól request i response,
- kody HTTP,
- paginacja Django DRF: `count`, `next`, `previous`, `results`,
- filtry, wyszukiwanie i sortowanie,
- nagłówki `X-API-Key`, `Idempotency-Key` i `Idempotency-Replayed`,
- format `error.code`, `error.message`, `error.details`,
- semantyka statusów zamówienia,
- skutki operacji widoczne przez API,
- zachowanie podczas wyścigu o ostatnią sztukę.

Dynamiczne UUID i czasy nie muszą być identyczne z wersją referencyjną, ale
muszą mieć właściwy typ i znaczenie.

## Niezmienniki wymagane w bazie

- jeden `Stock` dla pary produkt–magazyn,
- `quantity >= 0`,
- `reserved >= 0`,
- `reserved <= quantity`,
- dodatnia ilość pozycji i rezerwacji,
- dodatnia cena produktu i pozycji,
- unikalny klucz idempotencji,
- brak oversellingu przy wielu procesach aplikacji.

Samo sprawdzenie `available` przed zapisem nie wystarczy. Rozwiązanie musi
korzystać z transakcji i mechanizmu PostgreSQL, który serializuje konfliktujące
operacje.

## Minimalna kolejność pracy

1. Uruchom referencję i przejdź ręcznie główne endpointy.
2. Zaprojektuj modele oraz pierwszą migrację Alembic.
3. Zaimplementuj CRUD i format błędów.
4. Zaimplementuj zamówienie bez współbieżności.
5. Dodaj atomowe rezerwacje i blokady.
6. Dodaj idempotencję oraz maszynę stanów.
7. Napisz własne testy implementacji.
8. Przygotuj Dockerfile i bazę portu.
9. Skieruj `contract-tests/inventory` na swój adres przez
   `INVENTORY_BASE_URL`.

Port jest ukończony, gdy te same testy kontraktowe przechodzą przeciwko Django
i FastAPI, a test równoległy zawsze kończy się jednym `201` i jednym `409`.
