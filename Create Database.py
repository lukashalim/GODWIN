# -*- coding: utf-8 -*-
"""
Created on Thu Jan 01 16:00:32 2015

@author: LukasHalim
"""

import sqlite3
conn = sqlite3.connect("Godwin.db") # or use :memory: to put it in RAM
cursor = conn.cursor()
cursor.execute("DROP TABLE COMMENT")
cursor.execute("DROP TABLE POST")
cursor.execute("""
               CREATE TABLE post
               (post_id text, 
               failure_in_post integer,
               subreddit text, 
               num_comments integer);
               """)
cursor.execute("""
               CREATE TABLE comment
               (post_id text,
               comment_url text, 
               failure_in_comment integer,
               
               FOREIGN KEY (post_id)
               REFERENCES post (post_id)
               ON DELETE CASCADE);
               """)