import psycopg
from config import DB_CONFIG


def connect_db():
    return psycopg.connect(**DB_CONFIG)