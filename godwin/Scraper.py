# -*- coding: utf-8 -*-
'''
Created on Wed Nov 05 21:49:00 2014

@author: LukasHalim
Forked by @edridgedsouza
'''
import json
import os.path as path
import sqlite3
import time

import praw  # TODO: switch to pushshift API psaw or pmaw
import requests
from lxml import html
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
        self.failure_words = {'nazi', 'ndsap',
                              'adolf', 'hitler',
                              'fascism', 'fascist',
                              'goebbels', 'himmler',
                              'eichmann', 'holocaust',
                              'auschwitz', 'swastika'}

    def scrape(self, subreddit='all', limit=None):
        subreddit = self.r.subreddit(subreddit)
        posts = subreddit.hot(limit=limit)

        conn = sqlite3.connect(self.dbpath)
        cursor = conn.cursor()
        
        for post_count, post in tqdm(enumerate(posts),
                                     desc=f'Scraping from /r/{subreddit}'):
            self.process_post(post, cursor)
            if post_count % 50 == 0:
                conn.commit()
            time.sleep(2.5)  # Rate limit 30 requests per minute

        conn.commit()
        conn.close()

    def process_post(self, post, cursor):
        """
        Returns tuple of (post id, comment id, num_previous_comments)
        iff the post being analyzed has a failure. Else returns None
        """

        if post.num_comments > 10:  # Only allow posts above a certain size
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

                for commentCount, comment in enumerate(flat_comments):
                    if hasattr(comment, 'body'):
                        if self.text_fails(comment.body):
                            values = (post.id,
                                      comment.id,
                                      commentCount)
                            cursor.execute('''
                                       INSERT INTO failures 
                                       (post_id, 
                                       comment_id,
                                       num_prev_comments)
                                       VALUES (?,?,?)''',
                                           values)
                            return values
        return None

    def scrape_top_subreddits(self, limit=100):
        page = requests.get('http://redditlist.com/')
        tree = html.fromstring(page.text)

        #creating list of subreddits
        subs = tree.xpath('//*[@id="listing-parent"]/div[1]/div/span[3]/a')
        subs = [s.text.lower() for s in subs if s.text != 'Home']

        for sub in subs[::-1]:  # Start with smaller ones first
            self.scrape(subreddit=sub, limit=limit)
        print('Done scraping')

    def text_fails(self, text):
        return any(item in text.lower() for item in self.failure_words)
