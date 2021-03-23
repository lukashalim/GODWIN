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
cursor.execute("""CREATE TABLE post
                  (post_title text, 
                  post_id text, 
                  post_text blob, 
                  nazi_in_post integer,
                  subreddit text, 
                  comment_num integer, 
                  post_created float)
                  """)
cursor.execute("""CREATE TABLE comment
                  (post_title text, 
                  post_id text, 
                  post_text blob, 
                  nazi_in_post integer,
                  subreddit text,  
                  comment_num integer, 
                  comment_url text, 
                  comment_body blob,
                  nazi_in_comment integer,
                  comment_created float)
                  """)