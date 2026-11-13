# synthetic-ward

A healthcare data pipeline built on synthetic patient records. A simulator replays [Synthea](https://github.com/synthetichealth/synthea) patient histories into a Postgres database as if it were a live EHR: patients are admitted, discharged, charted and pass away over simulated time. From there the data is synced into a warehouse and modeled with dbt.

This is a learning and portfolio project. All patient data is synthetic, so there is no PHI anywhere in the repo or the pipeline.

**Status:** the EHR source and simulator are working. Fivetran, MotherDuck and dbt are in progress.

## Architecture

```mermaid
flowchart LR
    S["Synthea<br/>synthetic patients"] --> CSV[("CSV files")]
    CSV --> H["load_history.py<br/>everything before the cutoff"]
    CSV --> SIM["simulator.py<br/>replays events after the cutoff"]
    H --> N[("Neon Postgres<br/>ehr schema")]
    SIM --> N
    N -. planned .-> F["Fivetran CDC"]
    F -.-> M[("MotherDuck")]
    M -.-> D["dbt models"]