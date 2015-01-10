# GODWIN'S LAW ON REDDiT

Godwin's Law states that, "As an online discussion grows longer, the probability of a comparison involving Nazis or Hitler approaches 1." Godwin explained, "Although deliberately framed as if it were a law of nature or of mathematics, its purpose has always been rhetorical and pedagogical: I wanted folks who glibly compared someone else to Hitler or to Nazis to think a bit harder about the Holocaust." [Source](http://jewcy.com/jewish-arts-and-culture/i_seem_be_verb_18_years_godwins_law#sthash.kLqPt6EY.dpuf) 

Despite Godwin's admonition regarding the rhetorical and pedogogical purpose of the law, I thought it would be an interesting exercise to treat Godwin's law as if it were a law of nature, and subject it to some statistical scrutiny. If an online discussion includes 100 or 200 or 500 posts, how likely is a Hitler or Nazi comparison? 

Since Reddit has a [convenient API](http://www.reddit.com/dev/api) for scraping, I decided to use Reddit as a data source. Python's [lifelines package](http://lifelines.readthedocs.org/en/latest/Intro%20to%20lifelines.html#estimating-the-survival-function-using-kaplan-meier) implements a number of statistical techniques related to "survival analysis." Survival analysis gets is so named because the techniques were created to study time until a death, but it is useful in understanding time until other events. In this case, we want to know how long a discussion with "survive" until a Hitler or Nazi comparison.

I collected over 10,000 posts and analyzed them with LifeLines. This is the resulting Kaplan-Meier survival function:

![Kaplan-Meier survival function for Reddit](Kaplan-Meier-Godwin.png)

So, for example, as an Reddit discussion approaches 2000 posts, the probability of a comparison involving Nazis or Hitler is around 60%.

## Running the Code
You will need python, with [praw](https://praw.readthedocs.org/en/v2.1.19/), [lifelines](http://lifelines.readthedocs.org/en/latest/Quickstart.html), [pandas](http://lifelines.readthedocs.org/en/latest/Quickstart.html).
First run the "Create Database.py," then "Collect_Posts.py" and finally 
Also, you will be able to data more quickly by editing the [praw.ini file](http://praw.readthedocs.org/en/latest/pages/configuration_files.html?highlight=ini)
