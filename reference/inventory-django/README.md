# Inventory & Orders API — Django REST Framework

Kompletna implementacja referencyjna mikroserwisu magazynowo-zamówieniowego w
Django, Django REST Framework, Django ORM i PostgreSQL. Publicznym kontraktem
jest API HTTP; port w FastAPI może mieć inną architekturę, ale musi zachować to
samo zachowanie.

## Odpowiedzialność serwisu

Serwis zarządza:

- produktami i ich cenami,
- magazynami,
- ilością fizyczną i zarezerwowaną,
- zamówieniami i pozycjami,
- rezerwacjami zapasu,
- anulowaniem i realizacją zamówień,
- idempotencją tworzenia zamówienia.

Nie obsługuje płatności ani wysyłki. Te funkcje należałyby do osobnych
mikroserwisów.

## Struktura implementacji

```text
config/                 konfiguracja Django, URL, ASGI i WSGI
inventory/
├── authentication.py  uwierzytelnianie kluczem API
├── exceptions.py      wspólny format błędów
├── models.py          model domeny, indeksy i constraints
├── serializers.py     wejście i wyjście HTTP
├── services.py        transakcje i logika zamówień
├── views.py           ViewSety i healthcheck
└── migrations/        wersjonowany schemat PostgreSQL
tests/                  testy API, idempotencji i współbieżności
Dockerfile              obraz wyłącznie aplikacji referencyjnej
```

Logika transakcyjna znajduje się w `services.py`, a nie w serializerach lub
ViewSetach. Dzięki temu granica transakcji i kolejność blokowania rekordów są
widoczne.

## Model danych

| Model | Znaczenie |
| --- | --- |
| `Product` | produkt identyfikowany unikalnym SKU |
| `Warehouse` | magazyn identyfikowany unikalnym kodem |
| `Stock` | fizyczna i zarezerwowana ilość produktu w magazynie |
| `Order` | zamówienie klienta i jego status |
| `OrderItem` | produkt, magazyn, ilość i cena zapisana w momencie zakupu |
| `Reservation` | powiązanie pozycji zamówienia z zablokowanym zapasem |
| `IdempotencyRecord` | klucz, hash żądania i utworzone zamówienie |

`Stock.available` jest obliczane jako `quantity - reserved`. Krytyczny warunek
`reserved <= quantity` jest chroniony przez constraint bazy, a nie tylko kod
Pythona.

## Najważniejsza transakcja

Tworzenie zamówienia wykonuje następujące kroki w jednym `transaction.atomic`:

1. pobiera transakcyjną blokadę advisory dla klucza idempotencji,
2. zwraca wcześniejszy wynik albo odrzuca ponowne użycie klucza z innym body,
3. blokuje pasujące rekordy `Stock` przez `SELECT ... FOR UPDATE`,
4. sprawdza dostępność już po uzyskaniu blokad,
5. tworzy zamówienie, pozycje i rezerwacje,
6. zwiększa `reserved`,
7. zapisuje wynik idempotencji,
8. zatwierdza wszystko albo wycofuje wszystko.

Rekordy zapasu są blokowane w deterministycznej kolejności klucza głównego,
co ogranicza ryzyko deadlocków. Gdy dwa żądania kupują ostatnią sztukę, tylko
jedno zobaczy wystarczający zapas po uzyskaniu blokady.

Anulowanie zwalnia aktywne rezerwacje. Realizacja pomniejsza jednocześnie
`quantity` i `reserved`. Obie operacje także blokują zamówienie, rezerwacje i
stany magazynowe.

## Maszyna stanów

```text
confirmed ──> completed
     │
     └──────> cancelled
```

Ponowne wykonanie tej samej operacji końcowej jest idempotentne. Przejście z
`completed` do `cancelled` albo z `cancelled` do `completed` zwraca `409`.

## Indeksy i ograniczenia

| Element | Cel |
| --- | --- |
| `Product.sku UNIQUE` | jednoznaczna identyfikacja produktu |
| indeks `(active, name)` | listowanie aktywnego katalogu |
| `Stock(product, warehouse) UNIQUE` | jeden stan dla danej pary |
| `reserved <= quantity CHECK` | ochrona przed oversellingiem |
| indeks `(warehouse, product)` | zapytania magazynowe w odwrotnej kolejności |
| indeks `(status, created_at DESC)` | kolejka i historia zamówień |
| indeks częściowy aktywnych rezerwacji | szybkie operacje zwalniania i realizacji |
| dodatnie ceny i ilości `CHECK` | odrzucanie niepoprawnego stanu niezależnie od API |

Indeksy należy później oceniać na rzeczywistych danych za pomocą `EXPLAIN
ANALYZE`; sama obecność indeksu nie gwarantuje, że planista go użyje.

## Uwierzytelnianie i błędy

Wszystkie endpointy poza `/health/` wymagają nagłówka:

```text
X-API-Key: dev-inventory-api-key
```

Format błędu jest stabilny:

```json
{
  "error": {
    "code": "insufficient_stock",
    "message": "Niewystarczający dostępny zapas.",
    "details": null
  }
}
```

## Endpointy

| Metoda | Ścieżka | Znaczenie |
| --- | --- | --- |
| `GET` | `/health/` | gotowość aplikacji i bazy |
| `GET` | `/api/schema/`, `/api/docs/` | OpenAPI i Swagger UI |
| `GET, POST` | `/api/v1/products/` | lista i tworzenie produktów |
| `GET, PATCH, PUT, DELETE` | `/api/v1/products/{id}/` | szczegóły i modyfikacja produktu |
| `GET, POST` | `/api/v1/warehouses/` | lista i tworzenie magazynów |
| `GET, PATCH, PUT, DELETE` | `/api/v1/warehouses/{id}/` | szczegóły magazynu |
| `GET, POST` | `/api/v1/stocks/` | lista i tworzenie stanów |
| `GET, PATCH, PUT, DELETE` | `/api/v1/stocks/{id}/` | szczegóły i korekta ilości |
| `GET, POST` | `/api/v1/orders/` | lista lub atomowe utworzenie zamówienia |
| `GET` | `/api/v1/orders/{id}/` | zamówienie z pozycjami i rezerwacjami |
| `POST` | `/api/v1/orders/{id}/cancel/` | anulowanie i zwolnienie zapasu |
| `POST` | `/api/v1/orders/{id}/complete/` | realizacja i pomniejszenie stanu |

Listy obsługują paginację `page` i `page_size`. Produkty wspierają `search`,
`active` i `ordering`; magazyny `search` i `ordering`; stany filtry `product`,
`warehouse`; zamówienia filtry `status`, `customer_email` i sortowanie.

Tworzenie zamówienia wymaga `Idempotency-Key`:

```json
{
  "customer_email": "buyer@example.com",
  "items": [
    {
      "product": "UUID",
      "warehouse": "UUID",
      "quantity": 1
    }
  ]
}
```

Powtórzenie identycznego żądania zwraca to samo zamówienie i nagłówek
`Idempotency-Replayed: true`. Ten sam klucz z innym body zwraca `409`.

## Uruchamianie

Lokalne zależności instaluje `uv` na podstawie wspólnego lockfile'a:

```bash
uv sync --package inventory-django
uv run --package inventory-django python reference/inventory-django/manage.py check
```

Do działania endpointów i migracji nadal potrzebny jest PostgreSQL opisany w
`compose.yaml`.

Z katalogu głównego repozytorium:

```bash
docker compose up --build -d inventory-db inventory-api
```

API będzie dostępne pod `http://localhost:8001`, a Swagger UI pod
`http://localhost:8001/api/docs/`.

Migracje są wykonywane automatycznie przed startem Gunicorna. Ręczne komendy:

```bash
docker compose run --rm inventory-api python manage.py migrate
docker compose run --rm inventory-api python manage.py showmigrations
```

## Testy

```bash
docker compose --profile app-tests run --rm inventory-tests
```

Docker buduje wtedy target `test` z `pytest` i `pytest-django`; zwykły obraz
`inventory-api` zawiera tylko zależności uruchomieniowe.

Testy obejmują CRUD, uwierzytelnianie, idempotencję, zwolnienie rezerwacji,
rollback zamówienia wielopozycyjnego i dwie równoległe próby zakupu ostatniej
sztuki. Test współbieżności korzysta z osobnych połączeń i nie powinien być
uruchamiany na SQLite.

## Konfiguracja

| Zmienna | Znaczenie |
| --- | --- |
| `POSTGRES_HOST`, `POSTGRES_PORT` | adres PostgreSQL |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | baza i poświadczenia |
| `INVENTORY_API_KEY` | klucz wymagany przez API |
| `DJANGO_SECRET_KEY` | sekret Django |
| `DJANGO_ALLOWED_HOSTS` | dozwolone hosty |
| `DJANGO_DEBUG` | tryb debugowania, domyślnie wyłączony |

Wartości domyślne są przeznaczone wyłącznie do lokalnego laboratorium.
