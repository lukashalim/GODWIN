# -*- coding: utf-8 -*-
'''
Created on Thu Jan 01 16:00:32 2015

@author: LukasHalim
Forked by @edridgedsouza
'''

import sqlite3
import os
import pandas as pd
from contextlib import closing

class Database():
    def __init__(self, path='Godwin.db'):
        self.path = os.path.abspath(path)
        if not os.path.isfile(self.path):
            self.initialize()

    def initialize(self):
        conn = sqlite3.connect(self.path) # or use :memory: to put it in RAM
        cursor = conn.cursor()
        cursor.execute('DROP TABLE IF EXISTS comment')
        cursor.execute('DROP TABLE IF EXISTS post')
        cursor.execute('''
                       CREATE TABLE post
                       (post_id text, 
                       failure_in_post integer,
                       subreddit text,
                       post_score integer, 
                       num_comments integer);
                       ''')
        cursor.execute('''
                       CREATE TABLE failures
                       (post_id text,
                       comment_id text, 
                       num_prev_comments integer,
                       
                       FOREIGN KEY (post_id)
                       REFERENCES post (post_id)
                       ON DELETE CASCADE);
                       ''')
        conn.commit()
        conn.close()
        return self

    def reset_db(self):
        if os.path.exists(self.path):
            os.remove(self.path)
            try:
                os.remove(f'{self.path}-journal')
            except:
                pass
        self.initialize()
        return self

    def execute_sql(self, sql, params=()):
        with closing(sqlite3.connect(self.path)) as conn:
            with conn:
                cur = conn.cursor()
                cur.execute(sql, params)
                res = cur.fetchall()

                if res:
                    df = pd.DataFrame(res)
                    df.columns = [d[0] for d in cur.description]
                else:
                    df = pd.DataFrame({})
        return df

    def get_data(self):
        qry = '''
              SELECT p.post_id, failure_in_post, subreddit, 
                  post_score, num_comments,
                  f.comment_id, num_prev_comments
              FROM
                  post p
              LEFT JOIN
                  failures f
              ON
                  p.post_id = f.post_id
              '''
        df = self.execute_sql(qry)
        return df