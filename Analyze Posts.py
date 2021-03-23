# -*- coding: utf-8 -*-
"""
Created on Fri Dec 12 22:27:52 2014

@author: LukasHalim

2) For each post, determine earliest comparison with Nazis or Hitler
- Sort the comments for each post in ascending order
- Create a variable for the comment number within each post
- In cases where there is a comparison with Nazis or Hitler, identify the first comment where the comparison is made
- In cases where there is not a comparison with Nazis or Hitler, identify the final comment for the post


"""

import pandas as pd
import matplotlib.pyplot as plt
#import csv

import sqlite3
conn = sqlite3.connect("Godwin.db")
    
comments_df = pd.read_sql("select * from comment",conn)
g = comments_df.groupby('post_id')
#Sort the comments for each post in ascending order
comments_df['RN'] = g['comment_created'].rank(method='first')
#Create a variable for the comment number within each post
comments_with_nazi_df = comments_df[comments_df.nazi_in_comment == 1]
#Identify posts where there is a mention of Nazi
nazi_posts = comments_with_nazi_df['post_id'].unique()

#In cases where there is a comparison with Nazis or Hitler, identify the first comment 
#where the comparison is made
mins = comments_with_nazi_df.groupby('post_id')['RN'].idxmin()
first_nazi_comment = comments_with_nazi_df.loc[mins]

right_censored_posts = comments_df[comments_df.post_id.isin(nazi_posts) == False]
maxes = right_censored_posts.groupby('post_id')['RN'].idxmax()
final_comment = right_censored_posts.loc[maxes]

#combine the censored posts with those where a comparison is made
concatenated = pd.concat([first_nazi_comment,final_comment])

T = concatenated['RN']
E = concatenated['nazi_in_comment']

from lifelines import KaplanMeierFitter
kmf = KaplanMeierFitter()
kmf.fit(T, event_observed=E)
kmf.plot()

plt.xlim(0,2000);
plt.title("Reddit Post Lifespan Prior to Mention of Nazi or Hitler");
plt.xlabel("Comments")
plt.ylabel("Fraciton of Posts Without Mention of Hitler or Nazis")