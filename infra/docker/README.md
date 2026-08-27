# Docker — plan

W przyszłości znajdą się tu elementy potrzebne do budowania czterech aplikacji
i uruchamiania ich z czterema odizolowanymi bazami PostgreSQL.

Docelowy przepływ ma wykonywać migracje, czekać na prawdziwą gotowość usług,
uruchamiać wspólne testy kontraktowe i zwracać kod `0` tylko przy równoważnym
zachowaniu obu par API.

Dockerfile i Docker Compose nie zostały jeszcze utworzone celowo.
