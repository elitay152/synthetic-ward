CREATE SCHEMA IF NOT EXISTS ehr;

-- Reference tables
CREATE TABLE IF NOT EXISTS ehr.organizations (
    id          uuid PRIMARY KEY,
    name        text NOT NULL,
    address     text,
    city        text,
    state       text,
    zip         text,
    lat         double precision,
    lon         double precision,
    phone       text,
    revenue     numeric(14, 2),
    utilization integer,
    npi         text
);

CREATE TABLE IF NOT EXISTS ehr.providers (
    id           uuid PRIMARY KEY,
    organization uuid REFERENCES ehr.organizations (id),
    name         text NOT NULL,
    gender       text,
    speciality   text,
    address      text,
    city         text,
    state        text,
    zip          text,
    lat          double precision,
    lon          double precision,
    encounters   integer,
    procedures   integer,
    npi          text
);

CREATE TABLE IF NOT EXISTS ehr.payers (
    id                      uuid PRIMARY KEY,
    name                    text NOT NULL,
    ownership               text,
    address                 text,
    city                    text,
    state_headquartered     text,
    zip                     text,
    phone                   text,
    amount_covered          numeric(14, 2),
    amount_uncovered        numeric(14, 2),
    revenue                 numeric(14, 2),
    covered_encounters      integer,
    uncovered_encounters    integer,
    covered_medications     integer,
    uncovered_medications   integer,
    covered_procedures      integer,
    uncovered_procedures    integer,
    covered_immunizations   integer,
    uncovered_immunizations integer,
    unique_customers        integer,
    qols_avg                double precision,
    member_months           integer
);

-- Patients
CREATE TABLE IF NOT EXISTS ehr.patients (
    id                  uuid PRIMARY KEY,
    birthdate           date NOT NULL,
    deathdate           date,
    ssn                 text,
    drivers             text,
    passport            text,
    prefix              text,
    first               text,
    middle              text,
    last                text,
    suffix              text,
    maiden              text,
    marital             text,
    race                text,
    ethnicity           text,
    gender              text,
    birthplace          text,
    address             text,
    city                text,
    state               text,
    county              text,
    fips                text,
    zip                 text,
    lat                 double precision,
    lon                 double precision,
    healthcare_expenses numeric(14, 2),
    healthcare_coverage numeric(14, 2),
    income              numeric(14, 2),
    updated_at          timestamptz NOT NULL DEFAULT now()
);

-- Encounters: the simulator inserts them as in-progress and updates them on discharge
CREATE TABLE IF NOT EXISTS ehr.encounters (
    id                  uuid PRIMARY KEY,
    start               timestamptz NOT NULL,
    stop                timestamptz,
    patient             uuid NOT NULL REFERENCES ehr.patients (id),
    organization        uuid REFERENCES ehr.organizations (id),
    provider            uuid REFERENCES ehr.providers (id),
    payer               uuid REFERENCES ehr.payers (id),
    encounterclass      text NOT NULL,
    code                text,
    description         text,
    base_encounter_cost numeric(12, 2),
    total_claim_cost    numeric(12, 2),
    payer_coverage      numeric(12, 2),
    reasoncode          text,
    reasondescription   text,
    status              text NOT NULL DEFAULT 'finished'
                        CHECK (status IN ('in-progress', 'finished')),
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS encounters_patient_idx ON ehr.encounters (patient);
CREATE INDEX IF NOT EXISTS encounters_start_idx ON ehr.encounters (start);

-- Clinical events. Synthea gives these no ID, so each gets an identity key.
CREATE TABLE IF NOT EXISTS ehr.conditions (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    start       date NOT NULL,
    stop        date,
    patient     uuid NOT NULL REFERENCES ehr.patients (id),
    encounter   uuid REFERENCES ehr.encounters (id),
    system      text,
    code        text NOT NULL,
    description text
);

CREATE TABLE IF NOT EXISTS ehr.medications (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    start             timestamptz NOT NULL,
    stop              timestamptz,
    patient           uuid NOT NULL REFERENCES ehr.patients (id),
    payer             uuid REFERENCES ehr.payers (id),
    encounter         uuid REFERENCES ehr.encounters (id),
    code              text NOT NULL,
    description       text,
    base_cost         numeric(12, 2),
    payer_coverage    numeric(12, 2),
    dispenses         integer,
    totalcost         numeric(12, 2),
    reasoncode        text,
    reasondescription text
);

CREATE TABLE IF NOT EXISTS ehr.observations (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date        timestamptz NOT NULL,
    patient     uuid NOT NULL REFERENCES ehr.patients (id),
    encounter   uuid REFERENCES ehr.encounters (id),
    category    text,
    code        text NOT NULL,
    description text,
    value       text,   -- numeric or text, cast in dbt
    units       text,
    type        text
);

CREATE TABLE IF NOT EXISTS ehr.procedures (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    start             timestamptz NOT NULL,
    stop              timestamptz,
    patient           uuid NOT NULL REFERENCES ehr.patients (id),
    encounter         uuid REFERENCES ehr.encounters (id),
    system            text,
    code              text NOT NULL,
    description       text,
    base_cost         numeric(12, 2),
    reasoncode        text,
    reasondescription text
);

CREATE TABLE IF NOT EXISTS ehr.immunizations (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date        timestamptz NOT NULL,
    patient     uuid NOT NULL REFERENCES ehr.patients (id),
    encounter   uuid REFERENCES ehr.encounters (id),
    code        text NOT NULL,
    description text,
    base_cost   numeric(12, 2)
);

CREATE TABLE IF NOT EXISTS ehr.allergies (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    start        date NOT NULL,
    stop         date,
    patient      uuid NOT NULL REFERENCES ehr.patients (id),
    encounter    uuid REFERENCES ehr.encounters (id),
    code         text NOT NULL,
    system       text,
    description  text,
    type         text,
    category     text,
    reaction1    text,
    description1 text,
    severity1    text,
    reaction2    text,
    description2 text,
    severity2    text
);

CREATE INDEX IF NOT EXISTS conditions_encounter_idx    ON ehr.conditions (encounter);
CREATE INDEX IF NOT EXISTS medications_encounter_idx   ON ehr.medications (encounter);
CREATE INDEX IF NOT EXISTS observations_encounter_idx  ON ehr.observations (encounter);
CREATE INDEX IF NOT EXISTS procedures_encounter_idx    ON ehr.procedures (encounter);
CREATE INDEX IF NOT EXISTS immunizations_encounter_idx ON ehr.immunizations (encounter);
CREATE INDEX IF NOT EXISTS allergies_encounter_idx     ON ehr.allergies (encounter);

-- simulator bookkeeping
CREATE SCHEMA IF NOT EXISTS sim;

CREATE TABLE IF NOT EXISTS sim.state (
    id  integer PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    sim_time timestamptz NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);