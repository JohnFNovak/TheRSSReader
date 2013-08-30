#!/usr/bin/python
# coding: utf-8

# TheReader.py
# "One reader to rule them all, and then become skynet"

# (this file) begun
# Monday, March 4, 2013, 3:27pm
# Gutted and redone
# Saturday, March 16, 2013, 12:30pm

# John F. Novak (JFN)

# This an RSS agregator.
# This file is the Reader class. It has the feeds, the feed urls, the articles, and access to the full html and text of everything. There are functions defined on the Reader class which handle most of the logical things you would want to do with it. In principle, you could fire up a python REPL, load a Reader object, and live happily with just that, but this is intended to be interacted with through other programs which maniuplate the Reader object themselves.

# I plan on writing a daemon which fetches new articles, and web and CLI frontends for reading and interacting with the feeds and articels. I also plan on writing a loader which will be able to load in data exported from Google Reader.

import feedparser # handles the RSS feeds
from BeautifulSoup import BeautifulSoup # Parses HTML
import urllib2 # Handles some web requests (except for on sites that block it)
import nltk # Natural Language Text Processing Toolkit
import os
import sys
import subprocess # For accessing command line tools like mkdir and wget
import time
import random
import hashlib # used in guid()
from reporter import Reporter
from sqlalchemy.ext.declarative import declarative_base
#from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, Boolean, select, Text, PickleType
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.orm import sessionmaker

global settings

# FeedList    = { feedName1:{ title:'', url:'', LastChecked:time }, ... }
# ArticleList = { feedName1:{ NumArticles:#, NumRead:#, items:{ article1:{Object:feedparseritem, Read:bool, TouchedCount:#, LastRead:time, LastKeyed:time, Scored:bool, Score:#, KeyWords=[], Archived:bool, ArchiveTime:time, GUID:# }, ... }, ... }
# TextShelve  = { GUID:{ HTML:'', Text:'', WordList:[] }, ... }

# I think we are going to move to using SQL databases. I'm trying to think the bet way to do that...
# FeedList    One table          -> key:feedName, entries:[ title:'', url:'', LastChecked:time, NumArticles:#, NumRead:# ]
# ArticleList One table per feed -> key:article, entries:[Read:bool, TouchedCount:#, LastRead:time, LastKeyed:time, Scored:bool, Score:#, KeyWords=[], Archived:bool, ArchiveTime:time, GUID:# ]
# ArticleRaw  One table per feed -> key:GUID, entries:feedparseritem(mapped to rows)
# TextShelve  One table per feed -> key:GUID, entries:[ HTML:'', Text:'', WordList:''(list as csv string) ]

class Reader:
    """ The class which contains the data for the Reader """ 

    Base = declarative_base()

    #class Tablename:
    #    @declared_attr
    #    def __tablename__(cls):
    #        return cls.__name__.lower()

    class Feeds(Base):
        __tablename__ = 'Feeds'

        name        = Column( String(300), primary_key=True ) # User sepcifed Name
        title       = Column( String(300) )                   # Feed's self-stated title
        url         = Column( String(500) )                   # rss feed url
        LastChecked = Column( Integer )
        MostRecent  = Column( Integer )
        NumArticles = Column( Integer )
        NumRead     = Column( Integer )
        GUID        = Column( String(50) )
        Interest    = Column( String(100) )

        def __init__( self, name, url ):
            self.name    = name
            self.url     = url
            self.GUID    = guid()
            self.Interest= 'All'

        def __repr__( self ):
            return "<Feed('%s','%s','%s')>" % (self.name, self.url,self.GUID)

    class Articles(Base):
        __tablename__ = 'Articles'

        title            = Column( String(300), primary_key=True )
        feed             = Column( String(50), ForeignKey('Feeds.name') )
        url              = Column( String(300) )
        summary          = Column( Text )
        #summaryFull      = Column( Text )
        raw              = Column( PickleType )
        Read             = Column( Boolean )
        TimeStamp        = Column( Integer )
        TouchedCount     = Column( Integer )
        LastRead         = Column( Integer )
        LastKeyed        = Column( Integer )
        Keyed            = Column( Boolean )
        Score            = Column( Integer )
        Scored           = Column( Boolean )
        ArchivedHTML     = Column( Boolean )
        ArchiveHTMLTime  = Column( Integer )
        HTML             = Column( Text )
        ArchivedText     = Column( Boolean )
        ArchiveTextTime  = Column( Integer )
        TEXT             = Column( Text )
        FileName         = Column( String(350) )
        GUID             = Column( String(50) )
        Good             = Column( Boolean )
        FailCount        = Column( Integer )
        Flags            = Column( Text )

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
            self.TimeStamp    = time.time()

        def __repr__( self ):
            return "<Article('%s','%s')>" % (self.title, self.url)

    def __init__( self, SQL_version = 'mysql', username = 'the_reader', database = 'the_reader', password = 'reader_pw'):
        self.SQL_version = SQL_version
        self.username = username
        self.database = database
        self.password = password
        self.DB = create_engine(self.SQL_version+'://'+self.username+':'+self.password+'@localhost/'+self.database)
        #self.Feeds.__tablename__ = 'Feeds-'+username
        #self.Articles.__tablename__ = 'Articles-'+username
        self.Base.metadata.create_all( self.DB )
        Session = sessionmaker( bind = self.DB )
        self.session = Session()

    def AddFeed( self, feedName, feedUrl ):
        """ Adds a feed to a Reader Object """
        if not self.session.query(self.Feeds).filter(self.Feeds.name==feedName).count():
            newF = self.Feeds( feedName, feedUrl )
            self.session.add(newF)
        else:
            print 'feed already found in database. We will just update it'
            return self.UpdateFeed( feedName )
        d = feedparser.parse( feedUrl )
        if d.bozo == 1:
            print 'Unable to fetch feed from url', feedUrl
            return False
        for i in d.entries:
            artTitle = i.title.encode('latin-1', 'ignore')[:300]
            if not self.session.query(self.Articles).filter(self.Articles.title==artTitle).count(): # don't take duplicates
                newArt = self.Articles( artTitle, i.link, feedName, i )
                self.session.add(newArt)
                newArt.summary( BeautifulSoup( i.summary ).getText())
                #newArt.summaryFull( i.summary )
        newF.NumArticles = self.session.query(self.Articles).filter(self.Articles.feed==feedName).count()
        newF.LastChecked = time.time()
        newF.title = d.feed.title
        newF.MostRecent = time.mktime(d.entries[0].updated_parsed)
        self.session.commit()

    def DeleteFeed( self, feedName ):
        """ Adds a feed to a Reader Object """
        if not self.session.query(self.Feeds).filter(self.Feeds.name==feedName).count():
            print 'feed',feedName,'not found in database'
            return False
        feed = session.query(self.Feeds).filter(self.Feeds.name==feedName).one()
        self.session.delete(feed)
        return True

    def UpdateFeed( self, feedName ):
        """Updates a specified RSS feed"""
        if not self.session.query(self.Feeds).filter(self.Feeds.name==feedName).count():
            print 'feed,',feedName,'not found in database'
            return False
        F = self.session.query(self.Feeds).filter(self.Feeds.name==feedName).one()
        feedUrl = F.url
        # Get feed url
        d = feedparser.parse( feedUrl )
        if d.bozo == 1:
            print 'Unable to fetch feed from url', feedUrl
            return False
        for i in d.entries:
            artTitle = i.title.encode('latin-1', 'ignore')[:99]
            if not self.session.query(self.Articles).filter(self.Articles.title==artTitle).count(): # don't take duplicates
                newArt = self.Articles( artTitle, i.link, feedName, i )
                self.session.add(newArt)
        F.NumArticles = self.session.query(self.Articles).filter(self.Articles.feed==feedName).count()
        F.NumRead = self.session.query(self.Articles).filter(self.Articles.feed==feedName).filter(self.Articles.Read==True).count()
        F.LastChecked = time.time()
        F.MostRecent = time.mktime(d.entries[0].updated_parsed)
        self.session.commit()
        return True

    def ListFeeds( self ):
        """ Prints list of feed names"""
        Feeds = self.session.query(self.Feeds)
        return map( lambda x: x.name, Feeds )

    def ListArticles( self, feedName='All' ):
        """ Prints list of article titles"""
        if feedName != 'All':
            Articles = self.session.query(self.Articles).filter(self.Articles.feed==feedName)
        else:
            Articles = self.session.query(self.Articles)
        return map( lambda x: x.title, Articles )

    def ListNotArchived( self, feedName = 'All', version = 'html' ):
        """ Prints list of un archived article titles"""
        if version == 'html':
            if feedName != 'All':
                Articles = self.session.query(self.Articles).filter(self.Articles.feed==feedName).filter(self.Articles.ArchivedHTML==False)
            else:
                Articles = self.session.query(self.Articles).filter(self.Articles.ArchivedHTML==False)
        if version == 'text':
            if feedName != 'All':
                Articles = self.session.query(self.Articles).filter(self.Articles.feed==feedName).filter(self.Articles.ArchivedText==False)
            else:
                Articles = self.session.query(self.Articles).filter(self.Articles.ArchivedText==False)
        return map( lambda x: x.title, Articles )

    def ArchiveArticleHTML( self, title, thickheaded = False ):
        """Tries to archive the HTML for a specifed article"""
        if not self.session.query(self.Articles).filter(self.Articles.title==title).count():
            print 'Article',title,'not found in database'
            return False
        Artdata = self.session.query(self.Articles).filter(self.Articles.title==title).one()
        if not Artdata.Good:
            if not thickheaded:
                print 'Article',title,'has failed too many times'
                return False
        url = Artdata.url
        filename = Artdata.FileName
        try: # we are going to try and do this with urllib, but not all sites play well and the backup will be to use wget
            req = urllib2.Request(url)
            response = urllib2.urlopen(req)
            html = response.read()
            with open( '.Articles/'+filename+'.html', 'w') as f:
                f.write( html )
            f.close()
        except urllib2.HTTPError:
            check = subprocess.call(["wget","-O",'.Articles/'+filename+'.html',"-q",url])
            if not check:
                print 'hugh, both urllib and wget failed'
                Artdata.FailCount += 1
                if Artdata.FailCount == 10:
                    Artdata.Good = False
                self.session.commit()
                return False
        Artdata.ArchivedHTML = True
        Artdata.ArchiveHTMLTime = time.time()
        self.session.commit()
        return True

    def ExtractArticleText( self, title ):
        """Tries to extract the text from an archived acticles HTML"""
        if not self.session.query(self.Articles).filter(self.Articles.title==title).count():
            print 'Article',title,'not found in archive database'
            return False
        Artdata = self.session.query(self.Articles).filter(self.Articles.title==title).one()
        if not Artdata.ArchivedHTML:
            #print 'Article',title,'HTML not archived, attempting to archive now'
            #check = self.ArchiveArticleHTML( title )
            #if not check:
            #    print 'Failed to archive article HTML.'
            print 'Article',title,'HTML not archived, oh well...'
        url = Artdata.url
        reporter = Reporter()
        reporter.read( url = url )
        try:
            Artdata.TEXT = reporter.report_news().encode('latin-1', 'ignore')
        except UnicodeDecodeError:
            print 'there is something gross in thier text...'
            return False
        Artdata.ArchivedText = True
        Artdata.ArchiveTextTime = time.time()
        self.session.commit()
        return True

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

def get_int(p):
    c = raw_input(str(p))
    try:
        int(c)
    except ValueError:
        return -1
    else:
        return int(c)

def interact():
    import code
    code.InteractiveConsole(locals=globals()).interact()
    return True

if __name__ == '__main__':
    interact()
