#!/usr/bin/env python

# This is a mash-up of two Pimoroni examples. The twitter scroll that used the scroll phat HD mixed with a
# text scroller for the unicorn HD. As both of these are MIT licences, this code is also using the same.

import colorsys
import signal
import time
import unicodedata
import json
try:
    import queue
except ImportError:
    import Queue as queue
from sys import exit

try:
    import tweepy
except ImportError:
    exit("This script requires the tweepy module\nInstall with: sudo pip install tweepy")

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    exit("This script requires the pillow module\nInstall with: sudo pip install pillow")

import unicornhathd

# Use `fc-list` to show a list of installed fonts on your system,
# or `ls /usr/share/fonts/` and explore.

# FONT = ("/usr/share/fonts/truetype/freefont/FreeSansBold.ttf", 12)

# sudo apt install fonts-droid
# FONT = ("/usr/share/fonts/truetype/droid/DroidSans.ttf", 12)

# sudo apt install fonts-roboto
FONT = ("/usr/share/fonts/truetype/roboto/Roboto-Bold.ttf", 10)

# adjust the tracked keyword below to your keyword or #hashtag
keyword = '#tuesdaythoughts'

with open('twitter.json', 'r') as myfile:
   data = json.load(myfile)

# enter your twitter app keys here
# you can get these at apps.twitter.com
consumer_key = data["consumer_key"]
consumer_secret = data["consumer_secret"]

access_token = data["access_token"]
access_token_secret = data["access_token_secret"]

if consumer_key == '' or consumer_secret == '' or access_token == '' or access_token_secret == '':
    print("You need to configure your Twitter API keys! Edit this file for more information!")
    exit(0)

# make FIFO queue
q = queue.Queue()

def scroll_text(text):
    print(text)
    
    width, height = unicornhathd.get_shape()
    text_x = width
    text_y = 2

    font_file, font_size = FONT
    font = ImageFont.truetype(font_file, font_size)

    text_width, text_height = width, 0
    colours = [tuple([int(n * 255) for n in colorsys.hsv_to_rgb(x/float(len(text)), 1.0, 1.0)]) for x in range(len(text))]

    for line in text.splitlines():
        w, h = font.getsize(line)
        text_width += w + width
        text_height = max(text_height,h)

    text_width += width + text_x + 1

    image = Image.new("RGB", (text_width,max(16, text_height)), (0,0,0))
    draw = ImageDraw.Draw(image)

    offset_left = 0

    for index, line in enumerate(text.splitlines()):
        draw.text((text_x + offset_left, text_y), line, colours[index], font=font)
        offset_left += font.getsize(line)[0] + width

    for scroll in range(text_width - width):
        for x in range(width):
            for y in range(height):
                pixel = image.getpixel((x+scroll, y))
                r, g, b = [int(n) for n in pixel]
                unicornhathd.set_pixel(width-1-x, y, r, g, b)

        unicornhathd.show()
        time.sleep(0.01)
    
# define main loop to fetch formatted tweet from queue
def mainloop():
    unicornhathd.rotation(90)
    unicornhathd.brightness(1.0)

    while True:
        # grab the tweet string from the queue
        try:
            # scrollphathd.clear()
            status = q.get(False)
            scroll_text(status)
            q.task_done()

        except queue.Empty:
            time.sleep(1)

class MyStreamListener(tweepy.StreamListener):
    def on_status(self, status):
        if not status.text.startswith('RT'):
            # format the incoming tweet string
            status = u'     >>>>>     @{name}: {text}     '.format(name=status.user.screen_name.upper(), text=status.text.upper())
            try:
                status = unicodedata.normalize('NFKD', status).encode('ascii', 'ignore')
            except BaseException as e:
                print(e)

            # put tweet into the fifo queue
            q.put(status)

    def on_error(self, status_code):
        print("Error: {}".format(status_code))
        if status_code == 420:
            return False


auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

myStreamListener = MyStreamListener()
myStream = tweepy.Stream(auth=api.auth, listener=myStreamListener)

myStream.filter(track=[keyword], stall_warnings=True, async=True)


try:
    mainloop()

except KeyboardInterrupt:
    myStream.disconnect()
    del myStream
    unicornhathd.off()
    print("Exiting!")
