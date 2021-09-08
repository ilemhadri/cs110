import csv, glob, os, sqlite3

import gen, course, ui
from datetime import datetime, timedelta
from repos import Repo

def init_tables(con):
    cur = con.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS
        completion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sunet TEXT NOT NULL,
            code TEXT NOT NULL,
            survey_name TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(sunet, survey_name)
        )
    ''')
    con.commit()

def set_progress(con, code, sunet):
    survey = SURVEYS[code]
    cur = con.cursor()
    cur.execute('''
        INSERT OR REPLACE INTO completion (sunet, code, survey_name)
        VALUES (?, ?, ?)
    ''', [sunet, code, survey.name])
    con.commit()

def get_surveys(con, sunet):
    """
    Returns [
        [survey name: string, completed: 1 or 0],
        ...
    ]
    """
    cur = con.cursor()
    query = cur.execute('''
        SELECT survey_name, EXISTS(
            SELECT sunet FROM completion WHERE sunet=? AND survey_name=all_surveys.survey_name
        ) AS completed
        FROM (
            SELECT DISTINCT survey_name, MIN(timestamp) AS timestamp
            FROM completion
            GROUP BY survey_name
        ) AS all_surveys
        ORDER BY all_surveys.timestamp ASC
    ''', [sunet])
    return query.fetchall()
