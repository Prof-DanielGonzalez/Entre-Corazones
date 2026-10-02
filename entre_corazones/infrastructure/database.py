import os
import threading

import psycopg
from flask import current_app, jsonify

DATABASE_SCHEMA_READY = False

DATABASE_SCHEMA_LOCK = threading.Lock()

METRICS_WARNING_LOGGED = False

def conectar_base_datos():
    dsn = os.getenv("DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("Configura DATABASE_URL con una conexión PostgreSQL persistente.")
    if dsn.startswith("postgres://"):
        dsn = "postgresql://" + dsn[len("postgres://"):]
    conexion = psycopg.connect(dsn, connect_timeout=4)
    global DATABASE_SCHEMA_READY
    if not DATABASE_SCHEMA_READY:
        try:
            with DATABASE_SCHEMA_LOCK:
                if not DATABASE_SCHEMA_READY:
                    with conexion.cursor() as cursor:
                        cursor.execute("""
                            CREATE TABLE IF NOT EXISTS daily_metrics (
                                metric_date date PRIMARY KEY,
                                matches bigint NOT NULL DEFAULT 0,
                                score_total bigint NOT NULL DEFAULT 0,
                                readings bigint NOT NULL DEFAULT 0
                            )
                        """)
                        cursor.execute("""
                            CREATE TABLE IF NOT EXISTS daily_feedback (
                                metric_date date NOT NULL,
                                mode text NOT NULL,
                                rating smallint NOT NULL CHECK (rating IN (-1, 1)),
                                total bigint NOT NULL DEFAULT 0,
                                PRIMARY KEY (metric_date, mode, rating)
                            )
                        """)
                        cursor.execute("""
                            CREATE TABLE IF NOT EXISTS community_votes (
                                pair_id text NOT NULL,
                                voter_hash char(64) NOT NULL,
                                vote boolean NOT NULL,
                                created_at timestamptz NOT NULL DEFAULT now(),
                                PRIMARY KEY (pair_id, voter_hash)
                            )
                        """)
                    conexion.commit()
                    DATABASE_SCHEMA_READY = True
        except psycopg.Error:
            conexion.close()
            raise
    return conexion

def registrar_metrica(match=False, score=None):
    global METRICS_WARNING_LOGGED
    if not os.getenv("DATABASE_URL"):
        if not METRICS_WARNING_LOGGED:
            current_app.logger.warning("Las métricas anónimas están desactivadas: falta DATABASE_URL.")
            METRICS_WARNING_LOGGED = True
        return
    try:
        with conectar_base_datos() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO daily_metrics (metric_date, matches, score_total, readings)
                VALUES (CURRENT_DATE, %s, %s, %s)
                ON CONFLICT (metric_date) DO UPDATE SET
                    matches = daily_metrics.matches + EXCLUDED.matches,
                    score_total = daily_metrics.score_total + EXCLUDED.score_total,
                    readings = daily_metrics.readings + EXCLUDED.readings
                """,
                (1 if match else 0, int(score or 0) if match else 0, 0 if match else 1),
            )
    except (psycopg.Error, RuntimeError):
        current_app.logger.exception("No se pudo registrar una métrica agregada y anónima.")

def respuesta_base_datos_no_disponible(error):
    current_app.logger.exception("No se pudo completar la operación de PostgreSQL.", exc_info=error)
    return jsonify({"error": "La función compartida no está disponible. Revisa la conexión PostgreSQL del servidor e inténtalo más tarde."}), 503
