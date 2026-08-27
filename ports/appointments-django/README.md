# Twoje zadanie: port Appointments do Django REST Framework

Ten katalog celowo zawiera wyłącznie ten dokument. Masz samodzielnie przepisać
[referencyjne Appointments w FastAPI](../../reference/appointments-fastapi/README.md)
na Django, Django REST Framework i Django ORM.

Nie kopiuj struktury routerów ani warstwy SQLAlchemy. Odtwarzasz kontrakt i
reguły domenowe przy użyciu narzędzi właściwych Django.

## Co wykonujesz samodzielnie

- inicjalizację projektu i aplikacji Django,
- modele Django ORM,
- serializery i ViewSety lub APIView,
- Django migrations,
- filtrowanie, sortowanie i paginację,
- uwierzytelnianie `X-API-Key`,
- spójny format błędów,
- logikę stref czasowych i wolnych terminów,
- transakcje i ochronę przed nakładaniem wizyt,
- idempotencję i maszynę stanów,
- indeksy oraz constraints PostgreSQL,
- testy jednostkowe, integracyjne i współbieżności,
- healthcheck,
- własny Dockerfile,
- własną, odizolowaną bazę PostgreSQL,
- własne wpisy lub plik Docker Compose.

Nie otrzymujesz gotowego projektu Django ani infrastruktury dla portu.

## Kontrakt do odtworzenia

Port ma zachować ścieżki bez końcowego ukośnika:

| Metoda | Ścieżka |
| --- | --- |
| `GET` | `/health` |
| `GET, POST` | `/api/v1/specialists` |
| `GET, PATCH, DELETE` | `/api/v1/specialists/{id}` |
| `GET, POST` | `/api/v1/services` |
| `GET, PATCH, DELETE` | `/api/v1/services/{id}` |
| `GET, POST` | `/api/v1/availability-rules` |
| `GET, PUT, DELETE` | `/api/v1/availability-rules/{id}` |
| `GET, POST` | `/api/v1/availability-exceptions` |
| `GET, PUT, DELETE` | `/api/v1/availability-exceptions/{id}` |
| `GET` | `/api/v1/available-slots` |
| `GET, POST` | `/api/v1/appointments` |
| `GET` | `/api/v1/appointments/{id}` |
| `POST` | `/api/v1/appointments/{id}/confirm` |
| `POST` | `/api/v1/appointments/{id}/cancel` |

Muszą zgadzać się:

- modele wejściowe i wyjściowe,
- kody HTTP,
- paginacja `items`, `total`, `offset`, `limit`,
- parametry filtrowania,
- nagłówki `X-API-Key`, `Idempotency-Key` i `Idempotency-Replayed`,
- format błędów,
- interpretacja stref IANA i świadomych czasów z offsetem,
- reguły oraz wyjątki dostępności,
- generowanie slotów co 15 minut,
- maszyna stanów wizyty,
- zachowanie przy dwóch równoległych rezerwacjach.

## Niezmienniki wymagane w bazie

- unikalny email specjalisty,
- unikalna nazwa usługi u specjalisty,
- dodatni czas trwania i nieujemna cena,
- poprawna kolejność początków i końców przedziałów,
- jeden wyjątek dostępności na specjalistę i datę,
- unikalny klucz idempotencji,
- brak nakładających się aktywnych wizyt jednego specjalisty.

Ostatni warunek musi być chroniony przez PostgreSQL także wtedy, gdy dwa
żądania przejdą walidację aplikacyjną jednocześnie. Możesz użyć własnej migracji
SQL do utworzenia `btree_gist` i `ExclusionConstraint` albo innego rozwiązania
o równie silnej gwarancji.

## Minimalna kolejność pracy

1. Uruchom referencyjne FastAPI i poznaj `/docs`.
2. Zaprojektuj modele Django i migracje.
3. Zaimplementuj CRUD katalogu oraz dostępności.
4. Zaimplementuj generowanie wolnych terminów ze strefami czasowymi.
5. Dodaj rezerwacje, idempotencję i maszynę stanów.
6. Dodaj bazodanową ochronę przed nakładaniem wizyt.
7. Napisz testy własnej implementacji.
8. Przygotuj Dockerfile i bazę portu.
9. Skieruj `contract-tests/appointments` na swój adres przez
   `APPOINTMENTS_BASE_URL`.

Port jest ukończony, gdy wspólny kontrakt przechodzi dla FastAPI i Django, a
dwie równoległe rezerwacje tego samego terminu zawsze kończą się jednym `201`
i jednym `409`.
