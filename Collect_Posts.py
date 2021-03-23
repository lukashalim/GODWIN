# -*- coding: utf-8 -*-
"""
Created on Wed Nov 05 21:49:00 2014

@author: LukasHalim
"""
import praw
import time
import sqlite3

r = praw.Reddit('Comment Scraper 1.0 by Lukas_Halim')
subreddit = r.get_subreddit('all')

post_count = 0
comment_count = 0
godwin_count = 0
nazi_in_post = 0
#get_new or get_top
posts = subreddit.get_top(limit=None)
NoMorePosts = False

conn = sqlite3.connect("Godwin.db")
cursor = conn.cursor()
while post_count < 5000 and not NoMorePosts:
    post_count = post_count + 1
    try:
        time.sleep(2.5)
        post = next(posts)
        if post.num_comments > 100:
            cursor.execute(
                "SELECT COUNT (*) FROM post WHERE post_id = ?", (post.id, ))
            if cursor.fetchone()[0] == 0 and post.num_comments > 1000:
                post.replace_more_comments(limit=None, threshold=10)
                flat_comments = praw.helpers.flatten_tree(post.comments)
                for comment in flat_comments:
                    comment_count = comment_count + 1
                    if "NAZI" in post.title.upper() or "NAZI" in post.selftext.upper() or "HITLER" in post.title.upper() or "HITLER" in post.selftext.upper():
                        nazi_in_post = 1
                    else:
                        nazi_in_post = 0
                    if hasattr(comment, 'body'):
                        if "NAZI" in comment.body.upper() or "HITLER" in comment.body.upper():
                            godwin_count = godwin_count + 1
                            cursor.execute("INSERT INTO comment VALUES (?,?,?,?,?,?,?,?,?,?)", (post.title, post.id, post.selftext, nazi_in_post,
                                                                                                post.subreddit.display_name, str(post.num_comments), comment.permalink, comment.body, 1, comment.created_utc))
                            conn.commit()
                        else:
                            cursor.execute("INSERT INTO comment VALUES (?,?,?,?,?,?,?,?,?,?)", (post.title, post.id, post.selftext, nazi_in_post,
                                                                                                post.subreddit.display_name, str(post.num_comments), comment.permalink, comment.body, 0, comment.created_utc))
                cursor.execute("INSERT INTO post VALUES (?,?,?,?,?,?,?)", (post.title, post.id, post.selftext,
                                                                           nazi_in_post, post.subreddit.display_name, str(post.num_comments), post.created_utc))
                conn.commit()
                print("post added")
            else:
                print("already in db")
        else:
            print("skipping because fewer than 100")
    except Exception as e:
        print(e)
        NoMorePosts = True

#comments_df = pd.read_sql("select * from comment",conn)
#g = comments_df.groupby('post_id')
#comments_df['RN'] = g['comment_created'].rank(method='first')
#comments_with_nazi_df = comments_df[comments_df.nazi_in_comment == 1]
#comments_with_nazi_df.to_csv("out.csv", sep=',', encoding='utf-8')
