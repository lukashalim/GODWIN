# -*- coding: utf-8 -*-
"""
Created on Wed Nov 05 21:49:00 2014

@author: LukasHalim
"""
import praw
import time
import sqlite3
from tqdm import tqdm


class Scraper():
    def __init__(self, subreddit='all', db='Godwin.db'):
        self.db = db
        self.r = praw.Reddit('Comment Scraper 1.0 by Lukas_Halim')
        self.subreddit = self.r.get_subreddit(subreddit)
        self.failure_words = ['nazi', 'hitler', 'fascism', 'fascist']

    def scrape(self, limit=5000):
        post_count = 0

        #get_new or get_top
        posts = self.subreddit.get_top(limit=None)
        NoMorePosts = False

        conn = sqlite3.connect(self.db)
        cursor = conn.cursor()
        while post_count < limit and not NoMorePosts:
            try:
                for post in tqdm(posts,
                                 desc=f'Scraping from /r/{self.subreddit}'):
                    post_count += 1
                    self.process_post(post, conn, cursor)
            except Exception as e:
                print(e)
                NoMorePosts = True
        conn.commit()
        conn.close()

    def process_post(self, post, conn, cursor):
        time.sleep(1)
        if post.num_comments > 100:  # Only allow posts above a certain size
            cursor.execute('''SELECT COUNT (*) 
                            FROM post 
                            WHERE post_id = ?''',
                           (post.id, ))
            if cursor.fetchone()[0] == 0:  # If post not yet in db
                post.replace_more_comments(limit=None)
                flat_comments = praw.helpers.flatten_tree(post.comments)

                if self.text_fails(post.title + post.text):
                    failure_in_post = 1
                else:
                    failure_in_post = 0

                cursor.execute('''INSERT INTO post 
                                  (post_id, 
                                  failure_in_post, 
                                  subreddit, 
                                  num_comments)
                                  VALUES (?,?,?,?)''',
                               (post.id, failure_in_post,
                                post.subreddit.display_name,
                                post.num_comments))

                for comment in flat_comments:
                    if hasattr(comment, 'body'):
                        if self.text_fails(comment.body):
                            failure_in_comment = 1
                        else:
                            failure_in_comment = 0

                        cursor.execute('''
                                       INSERT INTO comment 
                                       (post_id, 
                                       comment_url, 
                                       failure_in_comment)
                                       VALUES (?,?,?)''',
                                       (post.id,
                                        comment.permalink,
                                        failure_in_comment))
                conn.commit()
                print("post added")

    def text_fails(self, text):
        return any(item in text.lower() for item in self.failure_words)
