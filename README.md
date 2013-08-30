#TheRSSReader

##A RSS aggregator in Python

###John Novak

####What is this?
This is a RSS aggregator/reader written in python. The original intent was to make a system which would be amenable to Natural Language Processing (NLP). It uses the feedparser module to handle RSS feeds, and BeautifulSoup to handle the wab pages. The full HTML of every article is retreived and stored in an SQL database. The text of each page is also extracted and stored.

A daemon is included so that the aggregator can be run in the background. It uses the daemon module: https://pypi.python.org/pypi/python-daemon/

There is a web interface included which is written in flask.

####Required modules:
feedparser - https://pypi.python.org/pypi/python-daemon/<br />
BeautifulSoup - http://www.crummy.com/software/BeautifulSoup/<br />
sqlalchemy - http://www.sqlalchemy.org/<br />
NLTK - http://nltk.org/<br />
daemon - https://pypi.python.org/pypi/python-daemon/<br />
flask - http://flask.pocoo.org/<br />

You will also obviously need to have some version of SQL on your system.

####State of the project:
This project has been on hold for a few months now because I am finishing my PhD. I am putting it out there right now so that other people can use what I've done so far and it wont die a sad death in a back corner of my hard drive.
