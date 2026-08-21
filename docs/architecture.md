# Architecture

Cakrawala is built around a simple rule: data cannot become evidence merely because an HTTP
request returned successfully.

```text
approved public source
        |
        v
HTTPS allowlist + timeout + bounded retry + response-size guard
        |
        v
immutable raw bytes + hash + source URL + fetch time
        |
        v
schema and quality gate
    | fail      | pass
    v           v
quarantine   canonical data
                |
                v
         point-in-time features
                |
                v
         model evaluation gate
                |
                v
       versioned predictions
                |
                v
      deterministic signal policy
```

Public Mode exposes only approved public projections. Personal Mode has a separate owner identity
and separate database roles. The language model can explain evidence but cannot create a trading
signal.
