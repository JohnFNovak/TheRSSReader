#!/usr/bin/python

# TheReaderWeb.py

# John F. Novak
# Thursday, March 21, 2013, 9:31pm

import feedparser
#import sqlalchelmy
from flask.ext.sqlalchemy import SQLAlchemy
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
import time
from BeautifulSoup import BeautifulSoup
import hashlib # used in guid()
import random

# configuration
DATABASE = '/tmp/flaskr.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'reader'
PASSWORD = 'default'

app = Flask(__name__)
app.config.from_object(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://the_reader:reader_pw@localhost/the_reader'
app.config['SQLALCHEMY_POOL_SIZE'] = 15
db = SQLAlchemy(app)

class Feeds(db.Model):
    __tablename__ = 'Feeds'

    name        = db.Column( db.String(300), primary_key=True ) # User sepcifed Name
    title       = db.Column( db.String(300) )                   # Feed's self-stated title
    url         = db.Column( db.String(500) )                   # rss feed url
    LastChecked = db.Column( db.Integer )
    MostRecent  = db.Column( db.Integer )
    NumArticles = db.Column( db.Integer )
    NumRead     = db.Column( db.Integer )
    GUID        = db.Column( db.String(50) )
    Interest    = db.Column( db.String(100) )

    def __init__( self, name, url ):
        self.name        = name
        self.url         = url
        self.NumArticles = 0
        self.NumRead     = 0
        self.GUID        = guid()
        self.Interest    = True

    def __repr__( self ):
        return "<Feed('%s','%s')>" % (self.name, self.url)

class Articles(db.Model):
    __tablename__ = 'Articles'

    title            = db.Column( db.String(300), primary_key=True )
    feed             = db.Column( db.String(50), db.ForeignKey('Feeds.name') )
    url              = db.Column( db.String(300) )
    raw              = db.Column( db.PickleType )
    summary          = db.Column( db.Text )
    Read             = db.Column( db.Boolean )
    TimeStamp        = db.Column( db.Integer )
    TouchedCount     = db.Column( db.Integer )
    LastRead         = db.Column( db.Integer )
    LastKeyed        = db.Column( db.Integer )
    Keyed            = db.Column( db.Boolean )
    Score            = db.Column( db.Integer )
    Scored           = db.Column( db.Boolean )
    ArchivedHTML     = db.Column( db.Boolean )
    ArchiveHTMLTime  = db.Column( db.Integer )
    HTML             = db.Column( db.Text )
    ArchivedText     = db.Column( db.Boolean )
    ArchiveTextTime  = db.Column( db.Integer )
    TEXT             = db.Column( db.Text )
    FileName         = db.Column( db.String(350) )
    GUID             = db.Column( db.String(50) )
    Good             = db.Column( db.Boolean )
    FailCount        = db.Column( db.Integer )
    Flags            = db.Column( db.Text )

    def __init__( self, title, url, feed, raw ):
        self.title        = title
        self.feed         = feed
        self.url          = url
        self.raw          = raw
        self.Read         = False
        self.TouchedCount = 0
        self.LastRead     = 0
        self.LastKeyed    = 0
        self.Scored       = False
        self.Score        = 0
        self.ArchivedHTML = False
        self.ArchivedText = False
        self.GUID         = guid()
        self.FileName     = feed+'-'+title
        self.Good         = True
        self.FailCount    = 0

    def __repr__( self ):
        return "<Article('%s','%s')>" % (self.title, self.url)

def CleanArticleQuery( cur ):
    entries = [dict(title=row.title,fulltext=row.TEXT,text=row.TEXT,guid=row.GUID,a=row.raw,timeS=row.TimeStamp,feed=row.feed,url=row.url,read=row.Read) for row in cur]
    entries.sort(key = lambda x: x['timeS'], reverse=True)
    for i in entries:
        #i['timeS'] = i['a'].updated
        i['timeS'] = time.ctime(i['timeS'])
        #i['summary'] = BeautifulSoup(i['a'].summary).getText()
        i['summary'] = i['a'].summary
        if '<img' in i['summary']:
            k = i['summary'].split('<img')
            l = k[1].split('>')
            i['summary'] = ' [image removed] '.join([k[0],l[-1]])
        i['fullsummary'] = i['a'].summary
        if i['summary']:
            if len(i['summary']) > 1200:
                i['summary'] = 'I hate it when they put the full text in the summary tag...'
    return entries

def QuickCleanArticleQuery( cur ):
    entries = [dict(title=row.title,guid=row.GUID,a=row.raw,timeS=row.TimeStamp,feed=row.feed,url=row.url,read=row.Read) for row in cur]
    entries.sort(key = lambda x: x['timeS'], reverse=True)
    for i in entries:
        #i['timeS'] = i['a'].updated
        i['timeS'] = time.ctime(i['timeS'])
    return entries

def CleanFeedQuery( feeds ):
    #return [dict(name=r.name,url=r.url,count=r.NumArticles,unread=str(int(r.NumArticles)-int(r.NumRead))) for r in feeds]
    return [dict(name=r.name,url=r.url,count=r.NumArticles,unread=r.NumRead) for r in feeds]

def makeMaster():
    global AllM
    global UnreadM
    global FeedM
    FeedM = {}
    arts = Articles.query.filter(Articles.Read==False).yield_per(200).all()
    UnreadM = CleanArticleQuery( arts )
    arts = Articles.query.all()
    AllM = CleanArticleQuery( arts )
    feeds = Feeds.query.all()
    for i in feeds:
        fName = i.name
        FeedM[fName] = CleanArticleQuery( Articles.query.filter(Articles.feed == fName).yield_per(200).all()[:200] )

def UpdateFeed( feedName ):
    """Updates a specified RSS feed"""
    if not Feeds.query.filter(Feeds.name==feedName).count():
        flash(feedName+' not found in database')
        return False
    F = Feeds.query.filter(Feeds.name==feedName).one()
    feedUrl = F.url
    # Get feed url
    d = feedparser.parse( feedUrl )
    if d.bozo == 1:
        print 'Unable to fetch feed from url', feedUrl
        return False
    for i in d.entries:
        artTitle = i.title.encode('latin-1', 'ignore')[:300]
        if not Articles.query.filter(Articles.title==artTitle).count(): # don't take duplicates
            newArt = Articles( artTitle, i.link, feedName, i )
    F.NumArticles = Articles.query.filter(Articles.feed==feedName).count()
    F.LastChecked = time.time()
    F.MostRecent = time.mktime(d.entries[0].updated_parsed)
    return True

@app.route('/')
def show_new():
    global UnreadM
    entries = UnreadM[:30]
    feeds = Feeds.query.all()
    feeds = CleanFeedQuery( feeds )
    return render_template('show_articles.html', entries=entries, feeds=feeds)

#@app.route('/<path:count>')
#def show_more( count ):
#    arts = Articles.query.filter(Articles.Read==False).all()
#    if int(count) > len(arts)/10:
#        return redirect('/'+str(int(count)-1))
#    entries = CleanArticleQuery( arts )[count*10:(count+1)*10]
#    feeds = Feeds.query.all()
#    feeds = CleanFeedQuery( feeds )
#    return render_template('show_more_articles.html', entries=entries, feeds=feeds)

@app.route('/articles/full')
def show_all():
    global AllM
    #cur = Articles.query.all()
    #entries = CleanArticleQuery( cur )
    return render_template('show_articles.html', entries=AllM)

@app.route('/update_all', methods=['POST'])
def update_all():
    makeMaster()
    return redirect( '/' )

@app.route('/add')
def offer_menu():
    return render_template('add_feed.html')

@app.route('/add/feed', methods=['POST'])
def add_feed():
    feedName = request.form['title']
    url = request.form['url']
    newFeed = Feeds( feedName, url )
    db.session.add(newFeed)
    db.session.commit()
    if Feeds.query.filter(Feeds.name==feedName).count():
        flash('Feed added succesfully')
    else:
        flash('Unable to add feed')
        return redirect('/feeds')
    check = UpdateFeed( feedName )
    if check:
        flash('Feed updated successfully')
        makeMaster()
        return redirect('/feed/'+feedName)
    else:
        flash('Unable to update feed')
        return redirect('/feed/'+feedName)

@app.route('/feeds/')
def show_feeds():
    feed = Feeds.query.all()
    feeds = CleanFeedQuery( feed )
    return render_template('show_feeds.html', feeds=feeds)

@app.route('/feed/<path:feedName>/update', methods=['POST'])
def update_feed( feedName ):
    check = UpdateFeed( feedName )
    if check:
        flash('Feed updated successfully')
        return redirect('/feed/'+feedName)
    else:
        flash('Unable to update feed')
        return redirect('/feed/'+feedName)

@app.route('/feed/<path:feedName>')
def show_feed( feedName ):
    global FeedM
    #cur = Articles.query.filter(Articles.feed==feedName).all()
    feed = Feeds.query.filter(Feeds.name==feedName).all()[0]
    #check = UpdateFeed( feedName )
    #if check:
    #    flash('Feed updated')
    #else:
    #    flash('Feed failed to update')
    #entries = CleanArticleQuery( cur )
    return render_template('show_feed.html', entries=FeedM[feedName], feed=feed)

@app.route('/article/<path:guid>')
def show_article( guid ):
    global AllM
    global UnreadM
    global FeedM
    cur = Articles.query.filter(Articles.GUID==guid).one()
    entries = CleanArticleQuery( [cur] )

    #All = Articles.query.all()
    #All = QuickCleanArticleQuery( All )
    index = map( lambda x: x['title'], AllM)
    Id = index.index(entries[0]['title'])
    Next = Id+1
    Prev = Id-1
    if Prev < 0:
        Prev=0
    if Next > len(AllM):
        Next = len(AllM)
    relative = { 'gnext':AllM[Next]['guid'], 'gprev':AllM[Prev]['guid'] }
    #All = Articles.query.filter(Articles.feed==entries[0]['feed']).all()
    #All = QuickCleanArticleQuery( All )
    index = map( lambda x: x['title'], FeedM[entries[0]['feed']]).index(entries[0]['title'])
    Next = Id+1
    Prev = Id-1
    if Prev < 0:
        Prev=0
    if Next > len(FeedM[entries[0]['feed']]):
        Next = len(FeedM[entries[0]['feed']])
    relative['fnext'] = FeedM[entries[0]['feed']][Next]['guid']
    relative['fprev'] = FeedM[entries[0]['feed']][Prev]['guid']

    cur.Read = True
    #if AllM[Id] in UnreadM:
    #    del UnreadM[UnreadM.index(AllM[Id])]
    AllM[Id]['read'] = True
    #entries[0]['read'] = True
    #FeedM[entries[0]['feed']][FeedM[entries[0]['feed']].index(AllM[Id])]['read'] = True
    cur.LastRead = time.time()
    cur.TouchedCount += 1
    db.session.add(cur)
    db.session.commit()
    feedName = cur.feed
    F = Feeds.query.filter(Feeds.name==feedName).one()
    F.NumRead = Articles.query.filter(Articles.Read==True).filter(Articles.feed==feedName).count()
    db.session.add(F)
    db.session.commit()
    return render_template('show_article.html', entries=entries, relative=relative)

def guid( *args ):
    """
    Generates a universally unique ID.
    Any arguments only create more randomness.
    """
    t = long( time.time() * 1000 )
    r = long( random.random()*100000000000000000L )
    a = random.random()*100000000000000000L
    data = str(t)+' '+str(r)+' '+str(a)+' '+str(args)
    data = hashlib.md5(data).hexdigest()

    return data

if __name__ == '__main__':
    makeMaster()
    app.run(host='0.0.0.0')
