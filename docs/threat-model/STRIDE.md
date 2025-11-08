# STRIDE Threat Analysis

| ID  | Поток / Компонент       | STRIDE                  | Угроза                                      | Контроль (мера защиты)                         | Связанный NFR | Проверка | Комментарий |
|-----|------------------------|------------------------|---------------------------------------------|------------------------------------------------|----------------|-----------|-------------|
| F1  | POST /auth/register     | Spoofing               | Подделка личности при регистрации          | HTTPS, проверка email, JWT                     | NFR-08         | pytest    | Проверка корректности регистрации |
| F2  | Argon2id hashing        | Tampering              | Изменение пароля или хэша                  | Использование Argon2id с солью                | NFR-01         | unit-test | Проверка алгоритма Argon2id |
| F3  | SQL INSERT user         | Repudiation            | Отказ от факта регистрации                  | Логирование с user_id и IP                     | NFR-06         | pytest logs | Проверка логов POST/PUT/DELETE |
| F4  | GET /features           | Information Disclosure | Утечка ошибок с PII                         | Формат RFC7807 без stacktrace                  | NFR-02         | e2e test  | Ошибки безопасны |
| F5  | SQL SELECT /features    | Elevation of Privilege | Доступ к чужим голосам и данным пользователей | RBAC на уровне ORM                              | NFR-10         | integration test | Проверка фильтрации по user_id |
| F6  | POST /vote              | Denial of Service      | Перегрузка API голосами                     | Rate limit: 10 RPS/IP, 100 RPS/user          | NFR-07         | pytest rate-limit | Тест ограничения RPS |
| F7  | Logs / audit trail      | Repudiation            | Отказ от действий пользователя             | Подпись логов, централизованное хранилище     | NFR-06         | pytest log format | Проверка форматирования логов |
| F8  | CI: Dependabot / Snyk   | Tampering              | Вредоносные зависимости                     | CI: Dependabot + Snyk, исправление CVE ≤ 7 дней | NFR-05       | CI build  | Проверка исправления уязвимостей |
| F9  | Monitoring / Metrics    | Information Disclosure | Утечка внутренних метрик                     | Доступ по VPN/токену, авторизация             | NFR-09         | uptime CI | Метрики защищены |
