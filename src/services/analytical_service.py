import duckdb
import glob
import json
import os

class AnalyticalService:
    def __init__(self, db_path=None, configs_path: str = "configs"):
        if db_path is None:
            db_url = os.environ.get("DATABASE_URL", "sqlite:///packages.db")
            if db_url.startswith("sqlite:///"):
                self.db_path = os.path.abspath(db_url.replace("sqlite:///", ""))
            else:
                self.db_path = os.path.abspath("packages.db")
        else:
            self.db_path = os.path.abspath(db_path)
        self.configs_path = os.path.abspath(configs_path)
        self.analytics_configs = self._load_analytics_configs()
        self.conn = duckdb.connect(':memory:')
        self.conn.execute("INSTALL sqlite; LOAD sqlite;")
        self.conn.execute(f"ATTACH '{self.db_path}' AS sqlite_db (TYPE SQLITE);")
        self._create_views()

    def _load_analytics_configs(self):
        configs = []
        for config_file in glob.glob(os.path.join(self.configs_path, "*.json")):
            with open(config_file, "r", encoding="utf-8") as handle:
                config = json.load(handle)
            mappings = config.get("analytical_mappings")
            doc_type = config.get("document_type")
            if doc_type and mappings:
                configs.append(
                    {
                        "document_type": doc_type,
                        "summary": mappings.get("summary", {}),
                        "transactions": mappings.get("transactions"),
                    }
                )
        return configs

    def _summary_expression(self, field_config):
        path = field_config["path"]
        field_type = field_config.get("type", "string")
        expr = f"(e.extraction_json::JSON->>'{path}')"
        if field_type == "decimal":
            return f"TRY_CAST({expr} AS DECIMAL(18,2))"
        return expr

    def _transaction_expression(self, field_config):
        path = field_config["path"]
        field_type = field_config.get("type", "string")
        expr = f"(tx->>'{path}')"
        if field_type == "decimal":
            return f"TRY_CAST({expr} AS DECIMAL(18,2))"
        return expr

    def _create_views(self):
        self.conn.execute("DROP VIEW IF EXISTS view_summary")
        self.conn.execute("DROP VIEW IF EXISTS view_transactions")

        summary_queries = []
        transaction_queries = []

        for config in self.analytics_configs:
            summary = config["summary"]
            document_type = config["document_type"].replace("'", "''")
            summary_queries.append(
                f"""
                SELECT
                    e.package_id,
                    p.original_filename AS filename,
                    e.document_type,
                    {self._summary_expression(summary["lender_name"])} AS lender_name,
                    {self._summary_expression(summary["total_amount"])} AS total_amount,
                    {self._summary_expression(summary["document_date"])} AS document_date,
                    e.confidence_score,
                    e.is_reviewed
                FROM sqlite_db.extractions e
                JOIN sqlite_db.packages p ON e.package_id = p.id
                WHERE e.document_type = '{document_type}'
                """
            )

            transactions = config.get("transactions")
            if transactions and transactions.get("path") and transactions.get("fields"):
                tx_path = transactions["path"]
                tx_fields = transactions["fields"]
                transaction_queries.append(
                    f"""
                    WITH raw_tx AS (
                        SELECT
                            e.package_id,
                            unnest(json_extract(e.extraction_json::JSON, '{tx_path}')::JSON[]) AS tx
                        FROM sqlite_db.extractions e
                        WHERE e.document_type = '{document_type}'
                          AND json_extract(e.extraction_json::JSON, '{tx_path}') IS NOT NULL
                    )
                    SELECT
                        package_id,
                        {self._transaction_expression(tx_fields["component"])} AS component,
                        {self._transaction_expression(tx_fields["amount"])} AS amount
                    FROM raw_tx
                    """
                )

        if summary_queries:
            self.conn.execute(f"CREATE OR REPLACE VIEW view_summary AS {' UNION ALL '.join(summary_queries)}")
        else:
            self.conn.execute(
                """
                CREATE OR REPLACE VIEW view_summary AS
                SELECT
                    CAST(NULL AS VARCHAR) AS package_id,
                    CAST(NULL AS VARCHAR) AS filename,
                    CAST(NULL AS VARCHAR) AS document_type,
                    CAST(NULL AS VARCHAR) AS lender_name,
                    CAST(NULL AS DECIMAL(18,2)) AS total_amount,
                    CAST(NULL AS VARCHAR) AS document_date,
                    CAST(NULL AS DOUBLE) AS confidence_score,
                    CAST(NULL AS BOOLEAN) AS is_reviewed
                WHERE FALSE
                """
            )

        if transaction_queries:
            self.conn.execute(f"CREATE OR REPLACE VIEW view_transactions AS {' UNION ALL '.join(transaction_queries)}")
        else:
            self.conn.execute(
                """
                CREATE OR REPLACE VIEW view_transactions AS
                SELECT
                    CAST(NULL AS VARCHAR) AS package_id,
                    CAST(NULL AS VARCHAR) AS component,
                    CAST(NULL AS DECIMAL(18,2)) AS amount
                WHERE FALSE
                """
            )

    def get_summary(self):
        return self.conn.execute("SELECT * FROM view_summary").fetchdf()

    def get_transactions(self):
        return self.conn.execute("SELECT * FROM view_transactions").fetchdf()
