import pipelines.utils.db


class Psycopg2Recorder:
    def __init__(self):
        self.calls = []

    def connect(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return "connection"


def test_get_postgres_connection_uses_supabase_database_url(monkeypatch):
    recorder = Psycopg2Recorder()
    monkeypatch.setattr(pipelines.utils.db, "psycopg2", recorder)
    monkeypatch.setenv(
        "SUPABASE_DATABASE_URL",
        "postgresql://postgres.example:secret@aws-1.pooler.supabase.com:5432/postgres",
    )

    connection = pipelines.utils.db.get_postgres_connection()

    assert connection == "connection"
    assert recorder.calls == [
        (
            (
                "postgresql://postgres.example:secret@aws-1.pooler.supabase.com:5432/postgres",
            ),
            {"sslmode": "require"},
        )
    ]


def test_get_postgres_connection_preserves_url_sslmode(monkeypatch):
    recorder = Psycopg2Recorder()
    monkeypatch.setattr(pipelines.utils.db, "psycopg2", recorder)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://postgres:secret@db.example.supabase.co:5432/postgres?sslmode=verify-full",
    )

    pipelines.utils.db.get_postgres_connection()

    assert recorder.calls[0][1] == {}


def test_get_postgres_connection_uses_local_postgres_env(monkeypatch):
    recorder = Psycopg2Recorder()
    monkeypatch.setattr(pipelines.utils.db, "psycopg2", recorder)
    monkeypatch.delenv("SUPABASE_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_DB", "government_project")
    monkeypatch.setenv("POSTGRES_USER", "postgres")
    monkeypatch.setenv("POSTGRES_PASSWORD", "postgres")
    monkeypatch.setenv("POSTGRES_PORT", "5433")

    pipelines.utils.db.get_postgres_connection()

    assert recorder.calls == [
        (
            (),
            {
                "host": "localhost",
                "database": "government_project",
                "user": "postgres",
                "password": "postgres",
                "port": 5433,
            },
        )
    ]
