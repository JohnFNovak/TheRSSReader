#!/usr/bin/env python

import sys, time
from daemon import Daemon
#from TheReader import Reader
import subprocess

class MyDaemon(Daemon):
    def run(self):
        #reader = Reader()
        while True:
            #feeds = reader.ListFeeds()
            #for i in feeds:
            #    check = reader.UpdateFeed(i)
            #for i in reader.ListNotArchived( version = 'text' ):
            #    check = reader.ExtractArticleText(i)
            check = subprocess.call(['python','/home/john/TheReader/ForceUpdate.py'])
            time.sleep(600)

if __name__ == "__main__":
    daemon = MyDaemon('/tmp/daemon-example.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)
