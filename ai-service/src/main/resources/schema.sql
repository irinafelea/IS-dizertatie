CREATE TABLE IF NOT EXISTS teacher_availability
(
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id    UUID             NOT NULL,
    semester_id  UUID             NULL,

    teacher_id   UUID             NOT NULL,
    option_id    UUID             NOT NULL,
    day_id       UUID             NOT NULL,
    timeslot_id  UUID             NOT NULL,

    availability SMALLINT         NOT NULL CHECK (availability IN (-1, 0, 1, 2)),
    reason       VARCHAR(1000)      NULL,
    weight       DOUBLE PRECISION NULL,

    created_at   TIMESTAMPTZ      NOT NULL DEFAULT now(),
    version    INT              DEFAULT 0
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_teacher_availability_slot
    ON teacher_availability (
    teacher_id,
    domain_id,
    semester_id,
    day_id,
    timeslot_id
);

CREATE INDEX IF NOT EXISTS idx_ta_teacher
    ON teacher_availability (teacher_id);

CREATE INDEX IF NOT EXISTS idx_ta_domain_semester
    ON teacher_availability (domain_id, semester_id);

CREATE INDEX IF NOT EXISTS idx_ta_day_timeslot
    ON teacher_availability (day_id, timeslot_id);
