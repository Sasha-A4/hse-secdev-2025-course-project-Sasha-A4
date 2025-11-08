Feature: Безопасное хранение паролей
  Scenario: Проверка, что используется Argon2id
    Given зарегистрирован новый пользователь
    When создаётся запись в базе
    Then поле password хранится как Argon2id-хэш, не как plain text

Feature: Производительность API
  Scenario: p95 времени ответа на GET /features при 30 RPS
    Given API запущен в staging окружении
    When выполняется нагрузочный тест с 30 RPS в течение 5 минут
    Then p95 времени ответа ≤ 250 мс

Feature: Ограничение частоты запросов
  Scenario: Превышение лимита IP
    Given один IP отправляет более 10 запросов в секунду
    When лимит превышен
    Then возвращается 429 Too Many Requests

Feature: Формат ошибок API
  Scenario: Ошибка не содержит личных данных
    Given запрос к /features/999 с несуществующим ID
    When сервер возвращает ошибку
    Then тело ответа имеет поля type, title, detail и не содержит stacktrace

Feature: Негативный сценарий — Уязвимость зависимостей
  Scenario: Появление Critical уязвимости в пакете
    Given CI обнаружил CVE уровня Critical
    When прошло более 7 дней без фикса
    Then пайплайн сборки должен завершиться с ошибкой

Feature: Негативный сценарий — Перегрузка сервиса
  Scenario: 150 RPS без горизонтального масштабирования
    Given на сервис подана нагрузка 150 RPS
    When CPU > 90% и p99 > 400 мс
    Then сервис должен деградировать с graceful shutdown, без 5xx всплеска
