# Data Flow Diagram (DFD)

## Основная схема

```mermaid
flowchart TD
    subgraph Client["Trust Boundary: Клиент"]
        U[User Browser / App]
    end

    subgraph API["Trust Boundary: Public API"]
        A[FastAPI Service]
        RL[Rate Limiter]
    end

    subgraph Core["Trust Boundary: Core Systems"]
        DB[(PostgreSQL)]
        AUTH[(Auth Module)]
        LOG[(Centralized Logs)]
    end

    subgraph Infra["Trust Boundary: Infrastructure"]
        CI[CI/CD]
        MON[Monitoring]
    end

    U -->|F1: POST /auth/register| A
    A -->|F2: Argon2id hash| AUTH
    A -->|F3: Write user record| DB
    U -->|F4: GET /features| A
    A -->|F5: SQL SELECT| DB
    A -->|F6: POST /vote| DB
    A -->|F7: Emit log| LOG
    CI -->|F8: Dependency scan| A
    MON -->|F9: Collect metrics| A
