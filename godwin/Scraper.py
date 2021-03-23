# -*- coding: utf-8 -*-
'''
Created on Wed Nov 05 21:49:00 2014

@author: LukasHalim
Forked by @edridgedsouza
'''
import json
import os.path as path
import sqlite3
import sys
import requests
import time

import praw
import requests
from lxml import html
from tqdm import tqdm

from .Database import Database

cfg = path.join(path.dirname(path.abspath(__file__)),
                '..', 'config.json')
with open(path.abspath(cfg)) as f:
    config = json.load(f)


class Scraper():
    PRAW_DELAY = 60/30 + 0.25  # Rate limit 30 requests per minute
    PS_DELAY = 60/200 + 0.05  # Pushshift rate limit to 200 per minute

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

    def scrape_top_subreddits(self, limit=100):
        page = requests.get('http://redditlist.com/')
        tree = html.fromstring(page.text)

        # creating list of subreddits
        subs = tree.xpath('//*[@id="listing-parent"]/div[1]/div/span[3]/a')
        subs = [s.text.lower() for s in subs if s.text != 'Home']
        n_subs = len(subs)

        # Start with smaller ones first
        for sub_count, sub in enumerate(subs[::-1], 1):
            self.scrape(subreddit=sub, limit=limit)
            print(f'Scraped {sub_count} of {n_subs} subreddits',
                  file=sys.stderr)

        print('Done scraping')

    def scrape(self, subreddit='all', time_filter='month', limit=None):
        time.sleep(self.PRAW_DELAY)
        subreddit = self.r.subreddit(subreddit)
        posts = subreddit.top(time_filter=time_filter, limit=limit)

        conn = sqlite3.connect(self.dbpath)
        cursor = conn.cursor()

        for post_count, post in tqdm(enumerate(posts),
                                     desc=f'Scraping from /r/{subreddit}'):
            self.process_post(post, cursor)
            if post_count and post_count % 25 == 0:
                conn.commit()

        conn.commit()
        conn.close()

    def process_post(self, post, cursor):
        """
        Returns tuple of (post id, comment id, num_previous_comments)
        iff the post being analyzed has a failure. Else returns None
        """

        post_considered = post.num_comments > 10
        if post_considered:
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

                values = self.process_comments(post.id)

                if values[1] is not None:
                    cursor.execute('''
                                    INSERT INTO failures 
                                    (post_id, 
                                    comment_id,
                                    num_prev_comments)
                                    VALUES (?,?,?)''',
                                   values)

    def process_comments(self, postid):
        session = requests.Session()  # https://stackoverflow.com/a/45470227/15014819
        session.hooks = {
            'response': lambda r, *args, **kwargs: r.raise_for_status()
        }

        block_size = 20000
        comment_index = 0
        after = 0

        while block_size == 20000:
            try:
                params = {'link_id': postid, 'limit': 20000,  # `limit` lets you use 20k, `size` only gives 100
                          'sort': 'asc', 'after': after}
                comments = session.get('https://api.pushshift.io/reddit/comment/search',
                                       params=params)
                results = comments.json()['data']
                block_size = len(results)

                if results:
                    for comment in results:
                        comment_index += 1
                        if self.text_fails(comment['body']):
                            return (postid, comment['id'], comment_index)

                    after = results[-1]['created_utc']
                
                # time.sleep(self.PS_DELAY)  # Honestly probably unnecessary

            except requests.HTTPError:
                print(f'Error with comments from post {postid}')

        return (None, None, None)

    def text_fails(self, text):
        return any(item in text.lower() for item in self.failure_words)
