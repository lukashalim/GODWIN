# -*- coding: utf-8 -*-
"""
Created on Wed Nov 05 21:49:00 2014

@author: LukasHalim
"""
import praw
import time
import sqlite3


class Scraper():
    def __init__(self, subreddit='all', db='Godwin.db'):
        self.db = db
        self.r = praw.Reddit('Comment Scraper 1.0 by Lukas_Halim')
        self.subreddit = self.r.get_subreddit(subreddit)
        self.failure_words = ['nazi', 'hitler', 'fascism', 'fascist']

    def scrape(self):
        post_count = 0

        #get_new or get_top
        posts = self.subreddit.get_top(limit=None)
        NoMorePosts = False

        conn = sqlite3.connect(self.db)
        cursor = conn.cursor()
        while post_count < 5000 and not NoMorePosts:
            try:
                for post in posts:
                    post_count += 1
                    self.process_post(post, conn, cursor)
            except Exception as e:
                print(e)
                NoMorePosts = True

    def process_post(self, post, conn, cursor):
        time.sleep(1)
        if post.num_comments > 100:
            cursor.execute('''SELECT COUNT (*) 
                                  FROM post 
                                  WHERE post_id = ?''', (post.id, ))
            if cursor.fetchone()[0] == 0 and post.num_comments > 1000:
                post.replace_more_comments(limit=None, threshold=10)
                flat_comments = praw.helpers.flatten_tree(
                            post.comments)
                if self.text_fails(post.title + post.text):
                    nazi_in_post = 1
                else:
                    nazi_in_post = 0
                cursor.execute('''INSERT INTO post 
                            (post_title, post_id, post_text, 
                            nazi_in_post, subreddit, comment_num, 
                            post_created)
                            VALUES (?,?,?,?,?,?,?)''',
                                       (post.title, post.id, post.selftext,
                                        nazi_in_post, post.subreddit.display_name,
                                        str(post.num_comments), post.created_utc))
                for comment in flat_comments:
                    if hasattr(comment, 'body'):
                        if self.text_fails(comment.body):
                            failure_in_comment = 1
                        else:
                            failure_in_comment = 0
                        cursor.execute('''
                                INSERT INTO comment 
                                (post_title, post_id, post_text, 
                                    nazi_in_post, subreddit, comment_num, 
                                    comment_url, comment_body, nazi_in_comment,
                                    comment_created)
                                    VALUES (?,?,?,?,?,?,?,?,?,?)''',
                                               (post.title, post.id, post.selftext,
                                                nazi_in_post, post.subreddit.display_name, str(
                                                    post.num_comments),
                                                comment.permalink,
                                                comment.body, failure_in_comment,
                                                comment.created_utc))
                conn.commit()
                print("post added")
            else:
                print("already in db")
        else:
            print("skipping because fewer than 100")

    def text_fails(self, text):
        return any(item in text.lower() for item in self.failure_words)
