import backend.api.database


class Psycopg2Recorder:
    def __init__(self):
        self.calls = []

    def connect(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return "connection"


def test_backend_postgres_connection_uses_supabase_database_url(monkeypatch):
    recorder = Psycopg2Recorder()
    monkeypatch.setattr(backend.api.database, "psycopg2", recorder)
    monkeypatch.setenv(
        "SUPABASE_DATABASE_URL",
        "postgresql://postgres.example:secret@aws-1.pooler.supabase.com:5432/postgres",
    )
    monkeypatch.delenv("DATABASE_URL", raising=False)

    connection = backend.api.database.get_postgres_connection()

    assert connection == "connection"
    assert recorder.calls == [
        (
            (
                "postgresql://postgres.example:secret@aws-1.pooler.supabase.com:5432/postgres",
            ),
            {"sslmode": "require"},
        )
    ]


def test_backend_postgres_connection_uses_local_postgres_env(monkeypatch):
    recorder = Psycopg2Recorder()
    monkeypatch.setattr(backend.api.database, "psycopg2", recorder)
    monkeypatch.delenv("SUPABASE_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_HOST", "postgres")
    monkeypatch.setenv("POSTGRES_DB", "postgres")
    monkeypatch.setenv("POSTGRES_USER", "postgres")
    monkeypatch.setenv("POSTGRES_PASSWORD", "postgres")
    monkeypatch.setenv("POSTGRES_PORT", "5432")

    backend.api.database.get_postgres_connection()

    assert recorder.calls == [
        (
            (),
            {
                "host": "postgres",
                "database": "postgres",
                "user": "postgres",
                "password": "postgres",
                "port": 5432,
            },
        )
    ]
