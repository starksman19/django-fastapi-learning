# Django & FastAPI Microservices Learning Lab

Edukacyjne monorepo do równoległej nauki Django REST Framework, FastAPI,
SQLAlchemy i PostgreSQL przez implementowanie tych samych kontraktów HTTP w
dwóch różnych stosach technologicznych.

Repozytorium docelowo będzie zawierać cztery niezależne mikroserwisy: dwie
implementacje referencyjne oraz dwa porty tworzone samodzielnie na podstawie
kontraktu i testów. Na obecnym etapie znajduje się tu wyłącznie struktura
katalogów i dokumentacja. Nie ma jeszcze kodu aplikacji, modeli, endpointów,
migracji ani gotowej konfiguracji Docker Compose.

## Cel edukacyjny

Projekt ma służyć do nauki przez porównanie. Zamiast budować dwa niepowiązane
API, każda domena zostanie zaimplementowana dwukrotnie:

1. najpierw powstanie kompletna implementacja referencyjna,
2. następnie ten sam kontrakt zostanie odtworzony w drugim frameworku,
3. wspólne testy kontraktowe będą wywoływać obie wersje po HTTP,
4. różnice wewnętrzne będą dozwolone, ale zachowanie widoczne dla klienta musi
   pozostać równoważne.

Dzięki temu repozytorium pozwoli ćwiczyć nie tylko składnię frameworków, lecz
także projektowanie API i baz danych, migracje, transakcje, współbieżność,
testowanie, analizę zapytań oraz świadome podejmowanie decyzji
architektonicznych.

## Cztery mikroserwisy

| Domena | Rola | Stos | Lokalizacja |
| --- | --- | --- | --- |
| Inventory & Orders | implementacja referencyjna | Django, Django REST Framework, Django ORM, PostgreSQL | `reference/inventory-django/` |
| Inventory & Orders | samodzielny port | FastAPI, SQLAlchemy, Alembic, PostgreSQL | `ports/inventory-fastapi/` |
| Appointments | implementacja referencyjna | FastAPI, SQLAlchemy, Alembic, PostgreSQL | `reference/appointments-fastapi/` |
| Appointments | samodzielny port | Django, Django REST Framework, Django ORM, PostgreSQL | `ports/appointments-django/` |

Katalog `reference/` jest przeznaczony na kompletne rozwiązania przygotowane
jako materiał wzorcowy. Katalog `ports/` jest przestrzenią do samodzielnej
pracy. Nie należy kopiować do niego gotowej implementacji referencyjnej. Port
może mieć inną strukturę modułów, warstwy i nazewnictwo wewnętrzne, o ile
realizuje dokładnie ten sam publiczny kontrakt HTTP.

## API 1: Inventory & Orders

Pierwsza domena opisuje sprzedaż produktów przechowywanych w magazynach.
Implementacją referencyjną będzie Django REST Framework, a jej odpowiednikiem
port napisany w FastAPI i SQLAlchemy.

Planowane zasoby:

- produkty,
- magazyny,
- stany magazynowe,
- rezerwacje produktów,
- zamówienia,
- pozycje zamówień.

Zakres edukacyjny obejmie CRUD, walidację i serializację, relacje bazodanowe,
filtrowanie, wyszukiwanie, sortowanie, paginację, uwierzytelnianie,
uprawnienia i spójny format błędów. W dalszych etapach dojdą maszyna stanów
zamówienia, idempotencja, ograniczenia bazodanowe, analiza problemu N+1 oraz
optymalizacja zapytań.

Najważniejszy scenariusz współbieżności brzmi: dwóch klientów próbuje kupić
ostatnią sztukę tego samego produktu. System musi atomowo przyznać ją tylko
jednemu klientowi, nie dopuścić do ujemnego stanu i zwrócić przewidywalną
odpowiedź drugiemu. Rozwiązanie będzie wymagało świadomego użycia transakcji,
blokad wierszy i ograniczeń bazy danych, a nie jedynie walidacji w kodzie
aplikacji.

## API 2: Appointments

Druga domena opisuje umawianie wizyt u specjalistów. Implementacją
referencyjną będzie FastAPI z SQLAlchemy i Alembic, a jej odpowiednikiem port w
Django REST Framework.

Planowane zasoby i operacje:

- specjaliści,
- oferowane usługi,
- reguły dostępności,
- wyjątki od dostępności,
- wyznaczanie wolnych terminów,
- rezerwowanie wizyt,
- potwierdzanie wizyt,
- anulowanie wizyt.

Ta część projektu pokaże modele wejściowe i wyjściowe, walidację, OpenAPI,
dependency injection, zarządzanie sesją SQLAlchemy, migracje Alembic,
filtrowanie, sortowanie, paginację, strefy czasowe, zadania wykonywane po
żądaniu, idempotencję i maszynę stanów wizyty.

Najważniejszy scenariusz współbieżności to dwie równoległe próby zarezerwowania
tego samego terminu. Tylko jedna z nich może się udać. System musi również
wykrywać częściowo nakładające się wizyty i zachować poprawność niezależnie od
tego, czy żądania trafią do jednego, czy do wielu procesów aplikacji.

## Struktura repozytorium

```text
.
├── reference/
│   ├── README.md
│   ├── inventory-django/
│   │   └── README.md
│   └── appointments-fastapi/
│       └── README.md
├── ports/
│   ├── README.md
│   ├── inventory-fastapi/
│   │   └── README.md
│   └── appointments-django/
│       └── README.md
├── contract-tests/
│   ├── inventory/
│   │   └── README.md
│   ├── appointments/
│   │   └── README.md
│   ├── fixtures/
│   │   └── README.md
│   └── README.md
├── infra/
│   ├── docker/
│   │   └── README.md
│   └── README.md
├── docs/
│   ├── architecture/
│   │   └── README.md
│   ├── api-contracts/
│   │   └── README.md
│   └── README.md
├── .gitignore
└── README.md
```

Znaczenie głównych katalogów:

- `reference/` — działające, kompletne implementacje referencyjne;
- `ports/` — samodzielne implementacje tego samego zachowania w przeciwnym
  stosie technologicznym;
- `contract-tests/` — testy uruchamiane bez zmian przeciwko obu wersjom API;
- `infra/` — przyszła orkiestracja, obrazy, bazy danych, healthchecki i komendy
  uruchomieniowe;
- `docs/` — decyzje architektoniczne i wersjonowane kontrakty HTTP.

Każdy pusty dziś obszar ma własny krótki plik `README.md`, dzięki czemu cel
katalogu jest widoczny, a sam katalog może być śledzony przez Git.

## Kontrakt ważniejszy od architektury wewnętrznej

Równoważność implementacji oznacza zgodność zachowania obserwowanego przez
klienta. Dla tej samej sytuacji biznesowej obie wersje powinny uzgadniać:

- metodę i ścieżkę HTTP,
- parametry ścieżki i zapytania,
- wymagane nagłówki,
- strukturę request body,
- kod statusu HTTP,
- strukturę i znaczenie response body,
- reguły walidacji,
- format błędów,
- skutki uboczne zapisane w bazie,
- zasady idempotencji,
- dozwolone przejścia stanów,
- zachowanie przy żądaniach równoległych.

Nie oznacza to porównywania surowego JSON znak po znaku. Losowe identyfikatory,
znaczniki czasu, kolejność pól obiektu czy inne wartości dynamiczne będą
normalizowane albo sprawdzane semantycznie. Przykładowo test może potwierdzić,
że `created_at` jest poprawnym czasem UTC i mieści się w oczekiwanym przedziale,
zamiast wymagać identycznego tekstu w obu bazach.

Kontrakty będą dokumentowane w `docs/api-contracts/`. Gdy kontrakt zostanie
ustalony, zmiana tylko jednej implementacji nie może po cichu zmieniać zachowania
całego systemu. Najpierw należy świadomie zaktualizować dokumentację i testy, a
następnie obie implementacje.

## Izolacja baz danych

Każdy mikroserwis docelowo otrzyma własną bazę PostgreSQL:

1. bazę dla referencyjnego Inventory w Django,
2. bazę dla portu Inventory w FastAPI,
3. bazę dla referencyjnego Appointments w FastAPI,
4. bazę dla portu Appointments w Django.

Dopuszczalną alternatywą jest jednoznaczna izolacja w osobnych schematach, ale
oddzielne bazy lepiej pokazują granice własności danych. Mikroserwis nie
powinien odczytywać ani modyfikować tabel należących do innego mikroserwisu.
Testy kontraktowe przygotują równoważne dane początkowe w obu bazach danej
domeny, a później będą porównywać skutki operacji semantycznie.

PostgreSQL jest istotną częścią laboratorium, ponieważ pozwala ćwiczyć
mechanizmy, których SQLite nie odwzorowuje wystarczająco wiernie:

- transakcje i poziomy izolacji,
- blokady wierszy, w tym `SELECT ... FOR UPDATE`,
- zachowanie równoległych zapisów i możliwość wystąpienia deadlocków,
- indeksy częściowe i złożone,
- ograniczenia `UNIQUE`, `CHECK`, klucze obce i wykluczenia,
- analizę planów zapytań za pomocą `EXPLAIN` i `EXPLAIN ANALYZE`.

Prawdziwe dane dostępowe nie będą trafiały do repozytorium. Konfiguracja będzie
przekazywana przez zmienne środowiskowe, a ewentualne pliki przykładowe będą
zawierały wyłącznie bezpieczne, fikcyjne wartości.

## Migracje, indeksy i ograniczenia

Każda aplikacja będzie miała własną historię migracji zgodną ze swoim stosem:

- Django migrations dla obu aplikacji Django,
- Alembic dla obu aplikacji FastAPI/SQLAlchemy.

Migracje będą częścią kodu i zostaną wykonane przed startem testów. Zmiana
modelu bez odpowiadającej jej migracji będzie traktowana jako niekompletna.
Rollback migracji będzie ćwiczony tam, gdzie jest bezpieczny i ma sens, ale nie
każda zmiana schematu musi być automatycznie odwracalna.

Indeksy nie będą dodawane wyłącznie intuicyjnie. Każdy ważniejszy indeks
powinien odpowiadać konkretnemu wzorcowi zapytania i zostać oceniony na planie
wykonania. Projekt obejmie:

- indeksy pojedyncze dla często filtrowanych kolumn,
- indeksy złożone z kolejnością kolumn dobraną do zapytań,
- indeksy częściowe dla podzbiorów takich jak aktywne rezerwacje,
- ograniczenia unikalności chroniące reguły biznesowe,
- ograniczenia `CHECK` wykluczające niepoprawne stany danych.

Walidacja aplikacyjna ma dostarczać czytelne błędy, ale krytyczne niezmienniki
muszą być chronione także przez bazę. Dzięki temu pozostają prawdziwe przy
równoległych żądaniach i niezależnie od ścieżki zapisu.

## Transakcje i współbieżność

Operacje obejmujące kilka zapisów — na przykład utworzenie zamówienia,
utworzenie pozycji i rezerwację zapasu — muszą być atomowe. Błąd w dowolnym
etapie ma wycofać całą operację, bez pozostawiania częściowego stanu.

Planowane ćwiczenia obejmują:

- jawne granice transakcji,
- blokowanie odpowiednich rekordów przed decyzją biznesową,
- konsekwentną kolejność blokad w celu ograniczenia deadlocków,
- rozpoznawanie konfliktów ograniczeń i mapowanie ich na odpowiedź HTTP,
- ponawianie operacji tylko wtedy, gdy jest to bezpieczne,
- testowanie faktycznej równoległości przy użyciu osobnych połączeń do bazy,
- rollback po kontrolowanym błędzie,
- ochronę przed oversellingiem i podwójną rezerwacją terminu.

Klucz idempotencji pozwoli bezpiecznie powtórzyć żądanie po utracie odpowiedzi.
Powtórzenie z tym samym kluczem i tym samym payloadem powinno zwrócić wynik
wcześniejszej operacji bez tworzenia duplikatu. Użycie tego samego klucza z
innym payloadem powinno zakończyć się jednoznacznym błędem kontraktowym.

## Strategia testów

Projekt rozróżnia cztery poziomy testów:

### Testy jednostkowe

Sprawdzają mały fragment logiki w izolacji, bez prawdziwego serwera HTTP i
zwykle bez bazy danych. Są szybkie i pomagają precyzyjnie lokalizować błędy, ale
nie dowodzą poprawności integracji frameworka z PostgreSQL.

### Testy integracyjne

Sprawdzają współpracę komponentów jednej implementacji, na przykład warstwy
API, ORM i prawdziwej bazy PostgreSQL. Obejmują migracje, transakcje,
ograniczenia oraz zachowanie zapytań.

### Testy kontraktowe

Traktują usługę jak czarną skrzynkę i wywołują publiczne API po HTTP. Ten sam
zestaw scenariuszy zostanie uruchomiony raz przeciwko implementacji
referencyjnej i raz przeciwko portowi. To główny mechanizm potwierdzania, że
dwa różne stosy realizują ten sam kontrakt.

### Testy end-to-end

Uruchamiają cały wymagany zestaw usług i infrastruktury tak jak środowisko
docelowe. Potwierdzają, że obrazy, migracje, healthchecki, sieć, konfiguracja i
API działają razem. Są najdroższe w utrzymaniu, dlatego będą uzupełnieniem, a
nie zamiennikiem testów z niższych poziomów.

Najważniejsze przyszłe scenariusze testowe:

- dwie równoległe próby zakupu ostatniej sztuki produktu,
- ponowienie żądania z tym samym kluczem idempotencji,
- konflikt klucza idempotencji użytego z innym payloadem,
- anulowanie zamówienia i zwolnienie rezerwacji,
- dwie równoległe próby rezerwacji tego samego terminu,
- wykrywanie częściowo i całkowicie nakładających się wizyt,
- odrzucanie niedozwolonych przejść stanów,
- rollback wszystkich zmian po błędzie w środku operacji,
- równoważny format walidacji i błędów domenowych,
- brak efektu N+1 dla wskazanych zapytań listujących.

Testy współbieżności nie będą udawać równoległości przez dwie operacje
wykonywane kolejno w jednej sesji. Użyją niezależnych klientów i połączeń,
synchronizując moment rozpoczęcia konfliktujących operacji.

## Przyszła rola Dockera

Dockerfile i plik Docker Compose są celowo nieobecne na tym etapie — ich
samodzielne przygotowanie jest częścią nauki. Docelowo infrastruktura powinna
zapewnić powtarzalne środowisko bez zależności od lokalnej konfiguracji
Pythona.

Jedna komenda Docker Compose ma ostatecznie:

1. zbudować cztery obrazy aplikacji,
2. uruchomić cztery odizolowane instancje lub bazy PostgreSQL,
3. poczekać na gotowość baz,
4. wykonać migracje każdej aplikacji,
5. uruchomić aplikacje i poczekać na ich healthchecki,
6. wykonać wspólne testy kontraktowe,
7. zakończyć się kodem `0` tylko wtedy, gdy obie pary API zachowują się
   równoważnie.

Healthcheck ma potwierdzać gotowość do obsługi żądań, a nie jedynie istnienie
procesu. Start aplikacji powinien zależeć od gotowości bazy, a start testów od
gotowości wszystkich testowanych API.

## Plan realizacji

### Etap 0 — struktura i zasady

- utworzenie monorepo i dokumentacji,
- opis granic aplikacji, baz danych i odpowiedzialności katalogów,
- brak implementacji biznesowej i infrastruktury uruchomieniowej.

### Etap 1 — kontrakt Inventory & Orders

- opis zasobów, schematów, błędów i maszyny stanów,
- ustalenie reguł rezerwacji zapasu i idempotencji,
- przygotowanie scenariuszy kontraktowych przed portowaniem.

### Etap 2 — referencyjne Inventory w Django

- modele, migracje, endpointy i uprawnienia,
- transakcje, blokady, indeksy i optymalizacja zapytań,
- testy jednostkowe oraz integracyjne.

### Etap 3 — port Inventory do FastAPI

- samodzielne odtworzenie kontraktu przy użyciu SQLAlchemy i Alembic,
- uruchomienie tego samego zestawu testów kontraktowych przeciwko obu wersjom,
- analiza i usunięcie różnic w zachowaniu.

### Etap 4 — kontrakt Appointments

- opis dostępności, stref czasowych i maszyny stanów wizyty,
- ustalenie reguł kolizji terminów oraz idempotencji,
- przygotowanie scenariuszy kontraktowych.

### Etap 5 — referencyjne Appointments w FastAPI

- modele, migracje, endpointy i dependency injection,
- transakcje oraz ochrona przed podwójną rezerwacją,
- testy jednostkowe i integracyjne.

### Etap 6 — port Appointments do Django

- samodzielne odtworzenie kontraktu w Django REST Framework,
- porównanie obu wersji wspólnymi testami,
- usunięcie rozbieżności semantycznych.

### Etap 7 — pełna infrastruktura i pomiary

- Dockerfile dla każdej aplikacji i wspólny Docker Compose,
- migracje, healthchecki oraz automatyczne testy end-to-end,
- pomiary zapytań, plany wykonania i dokumentacja wniosków.

## Kryteria ukończenia projektu

Projekt można uznać za ukończony, gdy:

- istnieją cztery uruchamialne, niezależne mikroserwisy,
- każdy mikroserwis ma własną konfigurację, migracje, testy i healthcheck,
- każda z czterech aplikacji korzysta z odizolowanej bazy PostgreSQL,
- oba kontrakty HTTP są jawnie opisane i wersjonowane,
- porty nie zależą od kodu implementacji referencyjnych,
- wspólne testy kontraktowe przechodzą bez zmian dla obu implementacji każdej
  domeny,
- dynamiczne wartości są porównywane semantycznie,
- testy dowodzą odporności na overselling i podwójną rezerwację,
- idempotencja, rollback i maszyny stanów są pokryte testami,
- krytyczne reguły są chronione przez transakcje oraz ograniczenia bazy,
- ważne indeksy mają uzasadnienie i zostały ocenione na planach zapytań,
- jedna komenda Docker Compose buduje środowisko, migruje bazy, czeka na
  gotowość usług i uruchamia testy,
- komenda kończy się sukcesem wyłącznie przy równoważnym zachowaniu obu par
  implementacji,
- repozytorium nie zawiera sekretów ani prawdziwych danych dostępowych.

## Stan bieżący

Zrealizowany jest wyłącznie etap 0: szkielet monorepo i dokumentacja. Kolejnym
krokiem powinno być zaprojektowanie pierwszej wersji kontraktu Inventory &
Orders — jeszcze przed rozpoczęciem implementacji endpointów.
