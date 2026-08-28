# Ściąga z przydatnych komend Dockera

Komendy `docker compose` uruchamiaj w katalogu głównym repozytorium, ponieważ
tam znajduje się plik `compose.yaml`:

```powershell
cd C:\Users\barte\PycharmProjects\django-fastapi-learning
```

Jeżeli wykonasz komendę na przykład w `C:\WINDOWS\system32`, Docker może zwrócić:

```text
no configuration file provided: not found
```

Oznacza to, że Docker nie znalazł pliku `compose.yaml`. Możesz wtedy przejść do
katalogu repozytorium albo jawnie wskazać plik:

```powershell
docker compose -f C:\Users\barte\PycharmProjects\django-fastapi-learning\compose.yaml ps
```

## Uruchamianie środowiska

| Komenda | Znaczenie |
| --- | --- |
| `docker compose up -d` | Uruchamia wszystkie podstawowe usługi w tle. |
| `docker compose up --build -d` | Buduje obrazy ponownie i uruchamia usługi w tle. |
| `docker compose up -d inventory-db appointments-db` | Uruchamia wyłącznie obie bazy. |
| `docker compose up -d inventory-api` | Uruchamia Django i jego zależności. |
| `docker compose up -d appointments-api` | Uruchamia FastAPI i jego zależności. |

Opcja `-d` oznacza uruchomienie w tle. Bez niej logi pozostają w aktualnym
terminalu, a `Ctrl+C` zatrzymuje uruchomiony zestaw usług.

## Sprawdzanie stanu i logów

| Komenda | Znaczenie |
| --- | --- |
| `docker compose ps` | Pokazuje kontenery projektu, ich stan i wystawione porty. |
| `docker compose logs` | Pokazuje logi wszystkich usług. |
| `docker compose logs -f inventory-api` | Śledzi na żywo logi Django. |
| `docker compose logs -f appointments-api` | Śledzi na żywo logi FastAPI. |
| `docker compose logs --tail=100 inventory-api` | Pokazuje ostatnie 100 linii logów Django. |
| `docker compose config` | Sprawdza i wyświetla wynikową konfigurację Compose. |

Przy śledzeniu logów skrót `Ctrl+C` kończy tylko ich podgląd. Kontener działający
w tle nadal pozostaje uruchomiony.

## Zatrzymywanie i ponowne uruchamianie

| Komenda | Znaczenie |
| --- | --- |
| `docker compose stop` | Zatrzymuje usługi bez usuwania kontenerów. |
| `docker compose stop inventory-api appointments-api` | Zatrzymuje tylko oba API. |
| `docker compose start` | Uruchamia ponownie wcześniej zatrzymane kontenery. |
| `docker compose restart inventory-api` | Restartuje wyłącznie Django. |
| `docker compose restart appointments-api` | Restartuje wyłącznie FastAPI. |
| `docker compose down` | Zatrzymuje i usuwa kontenery oraz sieć projektu. |

`docker compose down` nie usuwa danych zapisanych w nazwanych wolumenach baz.
Po kolejnym `docker compose up` wcześniejsze dane nadal będą dostępne.

## Usuwanie danych baz

```powershell
docker compose down -v
```

Opcja `-v` usuwa również wolumeny PostgreSQL, a więc wszystkie lokalne dane z
obu baz. Używaj jej tylko wtedy, gdy świadomie chcesz rozpocząć pracę z pustymi
bazami. Tego działania nie można cofnąć za pomocą Dockera.

## Budowanie obrazów

| Komenda | Znaczenie |
| --- | --- |
| `docker compose build` | Buduje obrazy bez uruchamiania kontenerów. |
| `docker compose build inventory-api` | Buduje tylko obraz Django. |
| `docker compose build appointments-api` | Buduje tylko obraz FastAPI. |
| `docker compose build --no-cache` | Buduje wszystko bez używania cache warstw. |
| `docker compose images` | Pokazuje obrazy używane przez projekt. |

Opcja `--no-cache` przydaje się przy diagnozowaniu problemów z nieaktualną
warstwą obrazu, ale zwykle znacząco wydłuża budowanie.

## Wykonywanie poleceń w kontenerach

Otwarcie powłoki w działającym kontenerze API:

```powershell
docker compose exec inventory-api sh
docker compose exec appointments-api sh
```

Wykonanie migracji bez otwierania powłoki:

```powershell
docker compose exec inventory-api python manage.py migrate
docker compose exec appointments-api alembic upgrade head
```

Połączenie z PostgreSQL wewnątrz kontenera bazy:

```powershell
docker compose exec inventory-db psql -U inventory -d inventory_reference
docker compose exec appointments-db psql -U appointments -d appointments_reference
```

Z klienta `psql` wychodzi się poleceniem `\q`, a z powłoki kontenera poleceniem
`exit`.

## Uruchamianie testów

Testy każdej implementacji:

```powershell
docker compose --profile app-tests run --rm inventory-tests
docker compose --profile app-tests run --rm appointments-tests
```

Testy kontraktowe obu działających API:

```powershell
docker compose --profile tests run --rm contract-tests
```

`run` tworzy jednorazowy kontener dla wskazanej usługi, a `--rm` usuwa go po
zakończeniu. Nie usuwa to baz danych ani ich wolumenów.

## Najczęstszy cykl pracy

Uruchomienie wszystkiego:

```powershell
docker compose up --build -d
docker compose ps
```

Podgląd problemów:

```powershell
docker compose logs --tail=100 inventory-api
docker compose logs --tail=100 appointments-api
```

Zakończenie pracy z zachowaniem danych:

```powershell
docker compose down
```
