import duckdb
import glob
import json
import os
import pandas as pd

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

    def _table_exists(self, table_name: str) -> bool:
        result = self.conn.execute(
            f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table_name}'"
        ).fetchone()
        return bool(result and result[0])

    def _load_package_logs(self):
        if not self._table_exists("package_logs"):
            return pd.DataFrame(columns=["package_id", "timestamp", "stage", "level", "message", "details"])
        return self.conn.execute(
            """
            SELECT package_id, timestamp, stage, level, message, details
            FROM sqlite_db.package_logs
            ORDER BY timestamp DESC, id DESC
            """
        ).fetchdf()

    def _load_latest_jobs(self):
        if not self._table_exists("extraction_jobs"):
            return pd.DataFrame(
                columns=["package_id", "status", "attempts", "max_attempts", "last_error", "updated_at", "created_at"]
            )
        return self.conn.execute(
            """
            WITH ranked_jobs AS (
                SELECT
                    package_id,
                    status,
                    attempts,
                    max_attempts,
                    last_error,
                    updated_at,
                    created_at,
                    ROW_NUMBER() OVER (
                        PARTITION BY package_id
                        ORDER BY COALESCE(updated_at, created_at) DESC, id DESC
                    ) AS row_num
                FROM sqlite_db.extraction_jobs
            )
            SELECT package_id, status, attempts, max_attempts, last_error, updated_at, created_at
            FROM ranked_jobs
            WHERE row_num = 1
            """
        ).fetchdf()

    def _parse_details(self, details):
        if not details:
            return {}
        try:
            parsed = json.loads(details)
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, json.JSONDecodeError):
            return {}

    def _extract_latency_ms(self, details):
        latency = self._parse_details(details).get("latency_ms")
        try:
            return float(latency)
        except (TypeError, ValueError):
            return None

    def _extract_total_tokens(self, details):
        usage = self._parse_details(details).get("usage")
        if not isinstance(usage, dict):
            return None
        tokens = usage.get("total_tokens")
        try:
            return float(tokens)
        except (TypeError, ValueError):
            return None

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

    def get_observability_summary(self):
        logs = self._load_package_logs()
        latest_jobs = self._load_latest_jobs()

        latency_values = logs["details"].apply(self._extract_latency_ms) if not logs.empty else pd.Series(dtype=float)
        token_values = logs["details"].apply(self._extract_total_tokens) if not logs.empty else pd.Series(dtype=float)

        retrying_jobs = latest_jobs[
            (latest_jobs["attempts"] > 0)
            & (latest_jobs["attempts"] < latest_jobs["max_attempts"])
            & (~latest_jobs["status"].isin(["COMPLETED", "FAILED"]))
        ] if not latest_jobs.empty else latest_jobs

        summary = pd.DataFrame(
            [
                {
                    "total_logs": int(len(logs)),
                    "error_logs": int((logs["level"] == "ERROR").sum()) if not logs.empty else 0,
                    "warning_logs": int((logs["level"] == "WARNING").sum()) if not logs.empty else 0,
                    "failed_jobs": int((latest_jobs["status"] == "FAILED").sum()) if not latest_jobs.empty else 0,
                    "retrying_jobs": int(len(retrying_jobs)) if not latest_jobs.empty else 0,
                    "avg_latency_ms": float(latency_values.dropna().mean()) if not latency_values.dropna().empty else None,
                    "avg_total_tokens": float(token_values.dropna().mean()) if not token_values.dropna().empty else None,
                    "classification_runs": int((logs["stage"] == "CLASSIFICATION").sum()) if not logs.empty else 0,
                    "extraction_runs": int((logs["stage"] == "EXTRACTION").sum()) if not logs.empty else 0,
                }
            ]
        )
        return summary

    def get_recent_failures(self, limit: int = 10):
        logs = self._load_package_logs()
        latest_jobs = self._load_latest_jobs()

        if logs.empty:
            return pd.DataFrame(
                columns=["timestamp", "package_id", "stage", "level", "message", "job_status", "attempts", "max_attempts", "last_error"]
            )

        failures = logs[logs["level"].isin(["ERROR", "WARNING"])].copy()
        if failures.empty:
            return pd.DataFrame(
                columns=["timestamp", "package_id", "stage", "level", "message", "job_status", "attempts", "max_attempts", "last_error"]
            )

        if not latest_jobs.empty:
            failures = failures.merge(latest_jobs, on="package_id", how="left")
        else:
            failures["status"] = None
            failures["attempts"] = None
            failures["max_attempts"] = None
            failures["last_error"] = None

        failures["parsed_details"] = failures["details"].apply(self._parse_details)
        failures["last_error"] = failures.apply(
            lambda row: row["parsed_details"].get("last_error")
            or row["parsed_details"].get("error")
            or row.get("last_error"),
            axis=1,
        )

        return (
            failures.rename(columns={"status": "job_status"})[
                ["timestamp", "package_id", "stage", "level", "message", "job_status", "attempts", "max_attempts", "last_error"]
            ]
            .head(limit)
            .reset_index(drop=True)
        )
