# Połączenie z bazami danych w DBeaver

Repozytorium uruchamia dwie niezależne bazy PostgreSQL. Możesz połączyć się z
nimi bezpośrednio z systemu Windows, ponieważ Docker Compose wystawia każdą z
nich na osobnym porcie.

## Uruchomienie baz

Otwórz PowerShell w katalogu głównym repozytorium:

```powershell
cd C:\Users\barte\PycharmProjects\django-fastapi-learning
docker compose up -d inventory-db appointments-db
docker compose ps
```

Obie bazy powinny mieć status `healthy`.

## Konfiguracja połączeń

W DBeaver wybierz **New Database Connection**, a następnie sterownik
**PostgreSQL**. Przy pierwszym użyciu DBeaver może poprosić o pobranie
sterownika PostgreSQL.

### Inventory — Django DRF

| Ustawienie | Wartość |
| --- | --- |
| Host | `localhost` |
| Port | `5433` |
| Database | `inventory_reference` |
| Username | `inventory` |
| Password | `inventory-dev-password` |
| Schema | `public` |

### Appointments — FastAPI

| Ustawienie | Wartość |
| --- | --- |
| Host | `localhost` |
| Port | `5434` |
| Database | `appointments_reference` |
| Username | `appointments` |
| Password | `appointments-dev-password` |
| Schema | `public` |

Dla obu lokalnych połączeń SSL może pozostać wyłączony. Po uzupełnieniu pól
użyj przycisku **Test Connection**, a następnie **Finish**.

Tabele znajdziesz w drzewie połączenia pod:

```text
Databases → nazwa bazy → Schemas → public → Tables
```

## Własne hasła z pliku `.env`

Wartości w tabelach są domyślnymi hasłami developerskimi z `compose.yaml`.
Jeżeli utworzyłeś `.env` i zmieniłeś hasła, w DBeaver użyj wartości:

- `INVENTORY_DB_PASSWORD` dla bazy Inventory,
- `APPOINTMENTS_DB_PASSWORD` dla bazy Appointments.

## Zatrzymanie baz

```powershell
docker compose down
```

Polecenie zatrzymuje kontenery, ale zachowuje dane w wolumenach. Dodanie opcji
`-v` usuwa również wolumeny i zapisane w nich dane, dlatego nie używaj jej, jeśli
chcesz zachować zawartość baz.
