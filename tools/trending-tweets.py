import tweepy, json
from textwrap import TextWrapper

CONSUMER_KEY = 'uCItgeEfBLySlIQEmdoFZbzYq'
CONSUMER_SECRET = 'fcEpWt6wxK0nMAU4QwwjhoyqGCg7ZPLPgCMoFh7cQDvVMdPR1e'
ACCESS_KEY = '2603000106-9o1aQtSNAZqdnwPHK3IaCJiTybhaMCzRhMfpCcZ'
ACCESS_SECRET = '8xdisZJrOQ4IzZ55g6g05b09BXgvr9Cixsw2kD7UMGpqy'


class StreamWatcherListener(tweepy.StreamListener):
    status_wrapper = TextWrapper(width=60, initial_indent='    ', subsequent_indent='    ')

    def on_status(self, status):
        try:
            print self.status_wrapper.fill(status.text)
            print '\n %s  %s  via %s\n' % (status.author.screen_name, status.created_at, status.source)
        except:
            # Catch any unicode errors while printing to console
            # and just ignore them to avoid breaking application.
            pass

    def on_error(self, status_code):
        print 'An error has occured! Status code = %s' % status_code
        return True  # keep stream alive

    def on_timeout(self):
        print 'Snoozing Zzzzzz'

def show_trending(api):
    trends1 = api.trends_place(1)

    print 'currently trending: '
    trending = [x['name'] for x in trends1[0]['trends'] if x['name'].find('#') == 0]
    for i in trending:
        print i


def main():
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
    api = tweepy.API(auth)

    show_trending(api)

    stream = tweepy.Stream(auth, StreamWatcherListener(), timeout=None)

    track_list = ('$SPY', '$IBM', '$AAPL', '$TSLA', '$EZA', '$MU', '$ARMH')
    stream.filter(None, track_list)

if __name__ == '__main__':
    main()