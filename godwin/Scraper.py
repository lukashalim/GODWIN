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
import time

import praw
import requests
from lxml import html
from prawcore.exceptions import Forbidden
from tqdm import tqdm

from .Database import Database

cfg = path.join(path.dirname(path.abspath(__file__)),
                '..', 'config.json')
with open(path.abspath(cfg)) as f:
    config = json.load(f)


class Scraper():
    PRAW_DELAY = 60/30 + 0.25  # Rate limit 30 requests per minute
    PS_DELAY = 60/200 + 0.05  # Pushshift rate limit to 200 per minute
    COMMIT_CHUNK = 10

    def __init__(self, db: Database = Database('Godwin.db')):
        self.dbpath = db.path
        self.r = praw.Reddit(client_id=config['client_id'],
                             client_secret=config['client_secret'],
                             user_agent='Godwin\'s law scraper')

        self.subs = self.get_subs()

        # This is aptly named
        self.failure_words = {'nazi', 'ndsap', 'adolf', 'hitler',
                              'fascism', 'fascist', 'goebbels', 'himmler',
                              'eichmann', 'holocaust', 'auschwitz', 'swastika'}

    def scrape_subreddits(self, subs=None, time_filter='month', limit=100):
        if subs is None:
            subs = self.subs
        else:
            if isinstance(subs, str):
                subs = [subs]
        subs = [s.lower() for s in subs]
        n_subs = len(subs)

        # Start with smaller ones first
        for sub_count, sub in enumerate(subs, 1):
            self.scrape_top(subreddit=sub,
                            time_filter=time_filter,
                            limit=limit)
            self.scrape_most_commented(subreddit=sub,
                                       limit=limit)
            print(f'Scraped {sub_count} of {n_subs} subreddits',
                  file=sys.stderr)

        print('Done scraping')

    def scrape_top(self, subreddit='all', time_filter='month', limit=None):
        time.sleep(self.PRAW_DELAY)
        sub = self.r.subreddit(subreddit)
        try:
            posts = list(sub.top(time_filter=time_filter, limit=limit))

        except Forbidden:
            try:
                sub.quaran.opt_in()
                posts = list(sub.top(time_filter=time_filter, limit=limit))
                print(f'Opted in to quarantined /r/{subreddit}')

            except Forbidden:
                print(f'Subreddit /r/{subreddit} top posts forbidden')
                return None

        conn = sqlite3.connect(self.dbpath)
        cursor = conn.cursor()

        try:
            desc = f'Scraping top posts of {time_filter} from /r/{subreddit}'
            for post_count, post in tqdm(enumerate(posts), total=len(posts),
                                         desc=desc):
                self.process_post(post, cursor)
                if post_count and post_count % self.COMMIT_CHUNK == 0:
                    conn.commit()

        except Forbidden:
            print(f'Subreddit /r/{subreddit} top posts forbidden')

        except KeyboardInterrupt:
            self.exit_safely(conn)

        conn.commit()
        conn.close()

    def scrape_most_commented(self, subreddit='all', limit=100):

        posts = self.get_most_commented_post_ids(subreddit=subreddit,
                                                 limit=limit)

        conn = sqlite3.connect(self.dbpath)
        cursor = conn.cursor()

        try:
            desc = f'Scraping most commented posts from /r/{subreddit}'
            for post_count, post in tqdm(enumerate(posts), total=len(posts),
                                         desc=desc):
                self.process_post(post, cursor)
                if post_count and post_count % self.COMMIT_CHUNK == 0:
                    conn.commit()

        except Forbidden:
            print(f'Subreddit /r/{subreddit} top commented posts forbidden')

        except KeyboardInterrupt:
            self.exit_safely(conn)

        conn.commit()
        conn.close()

    def get_most_commented_post_ids(self, subreddit='all', limit=100):
        ids = ['7yd4sz']  # Most commented post ever, for compatibility if fail

        session = requests.Session()  # https://stackoverflow.com/a/45470227/15014819
        session.hooks = {
            'response': lambda r, *args, **kwargs: r.raise_for_status()
        }

        try:
            params = {'limit': limit, 'sort_type': 'num_comments'}
            if subreddit not in ['all', 'popular']:
                params.update({'subreddit': subreddit})

            posts = session.get('https://api.pushshift.io/reddit/search/submission/',
                                params=params)
            posts = posts.json()['data']

            if posts:
                ids = [p['id'] for p in posts]

        except requests.HTTPError:
            print(f'Error getting most commented posts from /r/{subreddit}')

        return ids

    def process_post(self, post, cursor):
        """
        Returns tuple of (post id, comment id, num_previous_comments)
        iff the post being analyzed has a failure. Else returns None
        """
        if isinstance(post, str):
            post = self.r.submission(id=post)
            post_considered = True
        else:
            # If it's already a reddit submission object, doesn't take forever
            # to get the comment count
            post_considered = post.num_comments > 10

        if post_considered:
            cursor.execute('''
                           SELECT COUNT (*) 
                           FROM post 
                           WHERE post_id = ?''',
                           (post.id, ))

            if cursor.fetchone()[0] == 0:  # If post not yet in db
                # This line invokes praw api
                try:
                    posttext = post.title + post.selftext
                except Forbidden:
                    post.subreddit.quaran.opt_in()
                    posttext = post.title + post.selftext

                if self.text_fails(posttext):
                    failure_in_post = 1
                else:
                    failure_in_post = 0

                values = (post.id, failure_in_post, post.subreddit.display_name,
                          post.score, post.num_comments)
                cursor.execute('''
                               INSERT INTO post 
                               (post_id, failure_in_post, subreddit, 
                               post_score, num_comments)
                               VALUES (?,?,?,?,?)
                               ''',
                               values)

                values = self.process_post_comments(post.id)

                if values[1] is not None:
                    cursor.execute('''
                                   INSERT INTO failures 
                                   (post_id, comment_id, num_prev_comments)
                                   VALUES (?,?,?)
                                   ''',
                                   values)

    def process_post_comments(self, postid):
        session = requests.Session()
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

    @staticmethod
    def exit_safely(conn):
        conn.commit()
        conn.close()
        raise KeyboardInterrupt

    @staticmethod
    def get_subs():
        page = requests.get('http://redditlist.com/')
        tree = html.fromstring(page.text)

        active_subs = tree.xpath('//*[@id="listing-parent"]'
                                 '/div[1]/div/span[3]/a')
        popular_subs = tree.xpath('//*[@id="listing-parent"]'
                                  '/div[2]/div/span[3]/a')

        active_subs = [s.text.lower() for s in active_subs
                       if s.text != 'Home'][::-1]
        popular_subs = [s.text.lower()
                        for s in popular_subs][::-1]

        # politics, worldnews, and news already represented
        # This list is for political and political-adjacent subs.
        # Disclaimer that the inclusion of these subs is in no way
        # an endorsement of their content or platform but an attempt to 
        # analyze the prevalent types of speech in their communities.

        political = ['aboringdystopia', 'againsthatesubreddits', 'anarchism',
                     'anarcho_capitalism', 'asktrumpsupporters', 'badeconomics',
                     'breadtube', 'communism', 'communism101', 'completeanarchy',
                     'conservative', 'conservatives', 'conspiracy', 'economics',
                     'enlightenedcentrism', 'feminism', 'firearms', 'fullcommunism',
                     'genzedong', 'guns', 'historyporn', 'kotakuinaction',
                     'latestagecapitalism', 'libertarian', 'libertarianmeme',
                     'mapporn', 'mensrights', 'moderatepolitics', 'neoliberal',
                     'neutralpolitics', 'coronavirus', 'polandball',
                     'politicaldiscussion', 'politicalhumor', 'progressive',
                     'progun', 'protectandserve', 'russialago', 'socialism',
                     'socialism_101', 'subredditdrama', 'theredpill',
                     'topmindsofreddit', 'tumblrinaction', 'ukpolitics',
                     'vexillology']

        # Doing this instead of sets to maintain order
        subs = active_subs + [s for s in popular_subs if s not in active_subs]
        political = [i for i in political if i not in subs]
        subs = subs + political + ['popular', 'all']

        return subs
