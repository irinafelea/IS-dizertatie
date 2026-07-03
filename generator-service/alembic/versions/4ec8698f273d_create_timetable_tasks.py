"""create tasks

Revision ID: ---
Revises:
Create Date: 2026-03-24 13:24:25.554210
"""

from alembic import op

revision = "---"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            module_ids JSONB NOT NULL,
            number_of_modules INT NOT NULL DEFAULT 1;
            
            domain_id UUID NOT NULL,
            semester_id UUID NOT NULL,

            category VARCHAR(32) NOT NULL,
            duration_hours INT NOT NULL,
            
            common BOOLEAN NOT NULL DEFAULT FALSE,

            optional BOOLEAN NOT NULL DEFAULT FALSE,
            pack INT NULL,

            group_index INT NULL,
            group_span INT NULL,

            number_of_students INT NOT NULL,
            number_of_groups INT NOT NULL,

            study_years_ids JSONB NOT NULL,
            study_years_labels VARCHAR(500) NOT NULL,

            pair_group_key VARCHAR(500) NULL,
            module_targets JSONB NULL;

            online BOOLEAN NOT NULL DEFAULT FALSE,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)

    op.execute("""
            CREATE TABLE IF NOT EXISTS timetables (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

                semester_id UUID NOT NULL,
                domain_id UUID NOT NULL,

                version INT NOT NULL,

                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)

    op.execute("""
            CREATE TABLE IF NOT EXISTS timetable_modules (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

                timetable_id UUID NOT NULL,

                module_id UUID NOT NULL,
                room_id UUID NOT NULL,
                day_id UUID NOT NULL,
                hour_id UUID NOT NULL,
                study_year_id UUID NOT NULL,

                row_index INT NOT NULL,
                column_index INT NOT NULL,
                number_of_columns INT NOT NULL,

                even_week BOOLEAN NOT NULL DEFAULT FALSE,
                odd_week BOOLEAN NOT NULL DEFAULT FALSE,
                online BOOLEAN NOT NULL DEFAULT FALSE,

                show_discipline_title VARCHAR(500) NULL,
                show_teacher VARCHAR(500) NULL,

                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)

    op.execute("""
            CREATE INDEX IF NOT EXISTS idx_timetables_semester_domain_version
            ON timetables (semester_id, domain_id, version);
        """)

    op.execute("""
            CREATE INDEX IF NOT EXISTS idx_timetable_modules_timetable_id
            ON timetable_modules (timetable_id);
        """)

def downgrade():
    op.execute("DROP TABLE IF EXISTS tasks;")
    op.execute("DROP TABLE IF EXISTS timetable_modules;")
    op.execute("DROP TABLE IF EXISTS timetables;")