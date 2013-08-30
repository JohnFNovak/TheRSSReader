#!/usr/bin/python

# ForceUpdate.py

# John F. Novak
# Friday, March 22, 2013, 3:17pm

# This is just a quick script to force the RSS agregator to update

from TheReader import Reader

def main():
    reader = Reader()
    feeds = reader.ListFeeds()
    for i in feeds:
        check = reader.UpdateFeed(i)
    Articles = reader.ListNotArchived( version = 'text' )
    for i in Articles:
        check = reader.ExtractArticleText(i)
    Articles = reader.ListNotArchived( version = 'html' )
    for i in Articles:
       #check = reader.ArchiveArticleHTML(i, thickheaded=True)
       check = reader.ArchiveArticleHTML(i)

if __name__ == '__main__':
    main()
