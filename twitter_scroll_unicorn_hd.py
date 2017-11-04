#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This is a mash-up of two Pimoroni examples. The twitter scroll that used the scroll phat HD mixed with a
# text scroller for the unicorn HD. As both of these are MIT licences, this code is also using the same.

import colorsys
import signal
import time
import json
import argparse

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
# Examples:
# sudo apt install fonts-droid
# "font" : { "name" : "/usr/share/fonts/truetype/droid/DroidSans.ttf", "size" : 12 }
# sudo apt install fonts-roboto
# "font" : { "name" : "/usr/share/fonts/truetype/roboto/Roboto-Bold.ttf", "size" : 10 }

col_max = 32
col_index = 0
colours = [tuple([int(n * 255) for n in colorsys.hsv_to_rgb(x/float(col_max), 1.0, 1.0)]) for x in range(col_max)]

# make FIFO queue
q = queue.Queue()

def scroll_text(text):
    print(text)
    
    width, height = unicornhathd.get_shape()
    text_x = width
    text_y = 2

    font = ImageFont.truetype(*FONT)
    text_width, text_height = width, 0

    for line in text.splitlines():
        w, h = font.getsize(line)
        text_width += w + width
        text_height = max(text_height,h)

    text_width += width + text_x + 1

    image = Image.new("RGB", (text_width,max(16, text_height)), (0,0,0))
    draw = ImageDraw.Draw(image)

    offset_left = 0

    global col_index

    for index, line in enumerate(text.splitlines()):
        draw.text((text_x + offset_left, text_y), line, colours[col_index], font=font)
        offset_left += font.getsize(line)[0] + width
        col_index += 1
        if col_index >= col_max:
            col_index = 0

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

            # put tweet into the fifo queue
            q.put(status)

    def on_error(self, status_code):
        print("Error: {}".format(status_code))
        if status_code == 420:
            return False


try: 
    parser = argparse.ArgumentParser(description='Scan for keywords on Twitter and scroll on Unicorn Hat HD.')
    parser.add_argument('--keyword', help="Keyoard to search for can be a hashtag or a word (default 'cool')", nargs='?', type=str, default="cool")
    parser.add_argument('--config', help="Config file to load", nargs='?', type=str, default="default.json")
    args = parser.parse_args()
                        
    with open(args.config, 'r') as myfile:
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

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)

    myStreamListener = MyStreamListener()
    myStream = tweepy.Stream(auth=api.auth, listener=myStreamListener)

    myStream.filter(track=[args.keyword], stall_warnings=True, async=True)

    FONT = (data["font"]["name"], data["font"]["size"])

    mainloop()

except KeyboardInterrupt:
    myStream.disconnect()
    del myStream
    unicornhathd.off()
    print("Exiting!")
