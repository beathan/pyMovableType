import MySQLdb
import MySQLdb.cursors
import os

from config import *


class MTConnection(object):

    def __init__(self):
        """
        self.conn uses a DictCursor, which returns rows in dictionary form.
        This allows for accessing rows by column name rather than numeric
        indexes.
        """
        self.conn = MySQLdb.connect(host="localhost",
                                    user=MT_DB_USER,
                                    passwd=MT_DB_PASSWD,
                                    db=MT_DB_NAME,
                                    cursorclass=MySQLdb.cursors.DictCursor)
        self.cursor = self.conn.cursor()

    def execute(self, query):
        """
        Simple wrapper that returns a tuple with 2 items:
        (number of rows impacted by query, fetched rows)

        Example usage:
        rows, results = self.conn.execute(query)
        rows is an int, results is a dict with keys matching the
        names of columns from the queried tables
        """
        rows = self.cursor.execute(query)
        return (rows, self.cursor.fetchall())

    def last_inserted_id(self):
        """
        Useful for determining the id of the last item inserted,
        e.g. you create and store a new entry.
        """
        return self.cursor.lastrowid

    def close(self):
        self.conn.close()


if __name__ == '__main__':
    mt = MTConnection()
