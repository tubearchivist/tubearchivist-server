"""handle postgres integration"""

import psycopg2
import psycopg2.extras
from src.ta_config import get_config


class DatabaseConnect:
    """ handle db """

    CONFIG = get_config()

    def __init__(self):
        self.conn, self.cur = self._db_connect()

    def _db_connect(self):
        """returns connection and curser"""
        # Connect to database
        conn = psycopg2.connect(
            host=self.CONFIG['postgres']['db_host'],
            database=self.CONFIG['postgres']['db_database'],
            user=self.CONFIG['postgres']['db_user'],
            password=self.CONFIG['postgres']['db_password']
        )
        # Open a cursor to perform database operations
        cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        return conn, cur

    def db_execute(self, query):
        """run a query"""
        if isinstance(query, str):
            self.cur.execute(
                query
            )
            rows = self.cur.fetchall()
        elif isinstance(query, tuple):
            self.cur.execute(
                query[0], query[1]
            )
            rows = False

        return rows

    def db_close(self):
        """clean close the conn and curser"""
        self.conn.commit()
        self.cur.close()
        self.conn.close()
