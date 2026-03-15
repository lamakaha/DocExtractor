import duckdb
import os

class AnalyticalService:
    def __init__(self, db_path=None):
        if db_path is None:
            db_url = os.environ.get("DATABASE_URL", "sqlite:///packages.db")
            if db_url.startswith("sqlite:///"):
                self.db_path = os.path.abspath(db_url.replace("sqlite:///", ""))
            else:
                self.db_path = os.path.abspath("packages.db")
        else:
            self.db_path = os.path.abspath(db_path)
        self.conn = duckdb.connect(':memory:')
        self.conn.execute("INSTALL sqlite; LOAD sqlite;")
        self.conn.execute(f"ATTACH '{self.db_path}' AS sqlite_db (TYPE SQLITE);")
        self._create_views()

    def _create_views(self):
        # View for Summary Data
        self.conn.execute("""
            CREATE OR REPLACE VIEW view_summary AS
            SELECT 
                e.package_id,
                p.original_filename as filename,
                e.document_type,
                (e.extraction_json::JSON->>'$.lender_name.value') as lender_name,
                (e.extraction_json::JSON->>'$.total_amount.value')::DECIMAL(18,2) as total_amount,
                (e.extraction_json::JSON->>'$.effective_date.value') as effective_date,
                e.confidence_score,
                e.is_reviewed
            FROM sqlite_db.extractions e
            JOIN sqlite_db.packages p ON e.package_id = p.id
        """)

        # View for Transactions (Unnesting JSON arrays)
        # Cast JSON array to JSON[] list for unnesting
        self.conn.execute("""
            CREATE OR REPLACE VIEW view_transactions AS
            WITH raw_tx AS (
                SELECT 
                    package_id,
                    unnest(json_extract(extraction_json::JSON, '$.transactions.value')::JSON[]) as tx
                FROM sqlite_db.extractions
                WHERE json_extract(extraction_json::JSON, '$.transactions.value') IS NOT NULL
            )
            SELECT 
                package_id,
                (tx->>'$.component.value') as component,
                (tx->>'$.amount.value')::DECIMAL(18,2) as amount
            FROM raw_tx
        """)

    def get_summary(self):
        return self.conn.execute("SELECT * FROM view_summary").fetchdf()

    def get_transactions(self):
        return self.conn.execute("SELECT * FROM view_transactions").fetchdf()
