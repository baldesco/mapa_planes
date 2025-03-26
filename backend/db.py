import psycopg2
import os

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    return conn, cursor


def close_db(conn, cursor):
    cursor.close()
    conn.close()
