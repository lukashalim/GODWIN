# -*- coding: utf-8 -*-
'''
Created on Wed Nov 05 21:49:00 2014

@author: LukasHalim
Forked by @edridgedsouza
'''
import os.path as path
import json
import sqlite3
import time

import praw
from tqdm import tqdm

from .Database import Database

cfg = path.join(path.dirname(path.abspath(__file__)),
                '..', 'config.json')
with open(path.abspath(cfg)) as f:
    config = json.load(f)


class Scraper():
    def __init__(self, db: Database = Database('Godwin.db')):
        self.dbpath = db.path
        self.r = praw.Reddit(client_id=config['client_id'],
                             client_secret=config['client_secret'],
                             user_agent='Godwin\'s law scraper')
        
        # This is aptly named
        self.failure_words = ['nazi', 'ndsap',
                              'adolf', 'hitler',
                              'fascism', 'fascist']

    def scrape(self, subreddit='all', t='year', limit=5000):
        subreddit = self.r.subreddit(subreddit)
        posts = subreddit.top(t, limit=None)
        NoMorePosts = False

        post_count = 0

        conn = sqlite3.connect(self.dbpath)
        cursor = conn.cursor()
        while post_count < limit and not NoMorePosts:
            try:
                for post in tqdm(posts,
                                desc=f'Scraping from /r/{subreddit}'):
                    post_count += 1
                    self.process_post(post, cursor)
                    if post_count % 100 == 0:
                        conn.commit()
                    time.sleep(2.5)  # Rate limit 30 requests per minute

            except Exception as e:
                print(e)
                NoMorePosts = True
        conn.commit()
        conn.close()

    def process_post(self, post, cursor):
        if post.num_comments > 100:  # Only allow posts above a certain size
            cursor.execute('''
                           SELECT COUNT (*) 
                           FROM post 
                           WHERE post_id = ?''',
                           (post.id, ))

            if cursor.fetchone()[0] == 0:  # If post not yet in db
                if self.text_fails(post.title + post.selftext):
                    failure_in_post = 1
                else:
                    failure_in_post = 0

                cursor.execute('''
                               INSERT INTO post 
                               (post_id, 
                               failure_in_post, 
                               subreddit, 
                               post_score,
                               num_comments)
                               VALUES (?,?,?,?,?)
                               ''',
                               (post.id, failure_in_post,
                                post.subreddit.display_name,
                                post.score,
                                post.num_comments))

                post.comments.replace_more(limit=None)
                post.comment_sort = 'old'  # Ensure chronological order
                flat_comments = post.comments.list()

                for comment in flat_comments:
                    if hasattr(comment, 'body'):
                        if self.text_fails(comment.body):
                            failure_in_comment = 1
                        else:
                            failure_in_comment = 0

                        cursor.execute('''
                                       INSERT INTO comment 
                                       (post_id, 
                                       comment_id, 
                                       failure_in_comment,
                                       comment_score)
                                       VALUES (?,?,?,?)''',
                                       (post.id,
                                        comment.id,
                                        failure_in_comment,
                                        comment.score))

    def text_fails(self, text):
        return any(item in text.lower() for item in self.failure_words)
