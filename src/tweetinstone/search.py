### Search.py ###
# Functions for initializing a search

import os
import json
import pathlib # used for managing paths to output files
import logging
import argparse

from sys import exit
from io import BytesIO
from PIL import Image # Used for combining images in threads
from copy import copy, deepcopy # Used for managing the json of arguments in a sane way
from zipfile import ZipFile # Used for the zips
from datetime import datetime
from PySide6.QtCore import Signal
from playwright.async_api import async_playwright, Error as PlaywrightError

# Import stuff from TIS files
from tweetinstone.version import __version__
from tweetinstone.text_ops import validURL, commentFilter
from tweetinstone.file_ops import saveZip, saveTxt
from tweetinstone.traversal import detect

### args_setup():
# Create and return arg parser
def parser_setup() -> argparse.ArgumentParser:
	### Manage command line arguments and help menu ###
	# Some of these are commented out - they're features that don't exist yet, but theoretically might someday
	parser = argparse.ArgumentParser(prog='tis', usage='%(prog)s [options] [url]', description="Automatically save screenshots and metadata of tweets", epilog="Good luck and happy archiving, -M")
	
	# TODO POLISH: reconsider making input and urls mutually exclusive
	inputgroup = parser.add_argument_group(title='input options', description='either input an arbitrary number of urls or a file containing urls to search')
	inputgroup.add_argument('urls', metavar='[url] or [url1 url2 ...]', type=str, nargs='*', help='a url (or a group of space-separated urls) of tweet(s)', action='append')
	inputgroup.add_argument('-i','--input', metavar='[file.txt]', type=argparse.FileType('r'), help="the path to a file of line-separated urls", required=False, action='store')
	
	# `--only` and `--thread` are mutually exclusive because, duh!
	#amountgroup = parser.add_mutually_exclusive_group()
	# However, to better sort them I'll just put them in a regular group
	amountgroup = parser.add_argument_group(title='scope options', description='options that restrict or expand how many tweets are grabbed (by default, %(prog)s grabs the tweet and everything it is replying to)')
	amountgroup.add_argument('-o','--only', help="Only grab the specific tweet, not what it is replying to", required=False, action='store_true', default=False)
	amountgroup.add_argument('-t','--thread', help="get every tweet in the user's thread (before and after the tweet)", required=False, action='store_true')
	
	# TODO FUTURE: Add these options?
	#parser.add_argument('-r','--retweet', help="get the tweet a quote retweet is quoting", required=False, action='store_true')
	#parser.add_argument('-a','--all-tweets', help="get ALL tweets visible from the first tweet; 'shotgun mode'", required=False, action='store_true')
	
	customgroup = parser.add_argument_group(title='customization options', description='web browser options that change the appearance of the output images/video')
	
	# Default is dark mode because I'm a gracious human
	customgroup.add_argument('--color', help="set browser color scheme (default: dark)", required=False, action='store', default='dark', choices=['dark','light'])
	
	### DPI Scaling factor
	# 1 is default css, I don't recommend going that low; at least use 2
	# If you're curious about this, you can see the DPI scaling factor for various devices at: https://github.com/microsoft/playwright/blob/main/packages/playwright-core/src/server/deviceDescriptorsSource.json
	customgroup.add_argument('-s','--scale', metavar='[integer]', type=int, help="DPI scaling factor (default: 4)", required=False, action='store', default=4)
	
	### Locale & Time Zone
	# Not everyone lives on the east coast of the US? I'll believe that when I see it... but I'll make it easy for you to change this, if this matters to you
	customgroup.add_argument('-l','--locale', metavar='[string]', type=str, help="set locale of the web browser   (default: en-US)", required=False, action='store', default="en-US")
	customgroup.add_argument('--timezone', metavar='[string]', type=str, help="set time zone of the web browser (default: America/New_York)", required=False, action='store', default="America/New_York")

	# Some basic default options
	parser.add_argument('-v','--verbose', help="print debug information to stdout to see progress", action='store_true', default=False)
	parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
	parser.add_argument('-g','--gui', help="Launch with GUI", required=False, action='store_true')
	
	# TODO FUTURE FEATURE
	#parser.add_argument('-d','--directory', metavar='[path/to/directory]', type=pathlib.Path, help="Save output files to a specific directory", required=False, action='store')
	
	# Not strictly required, but recommended
	parser.add_argument('-c','--cookies', metavar='[file.txt]', type=argparse.FileType('r'), help="A file containing the session token for a user found in browser cookies", required=False, action='store')
	parser.add_argument('--generate', metavar='[file.txt]',type=pathlib.Path, help="Prompts for the auth_token string and create cookiefile from it at the specified file name", required=False, action='store')
	# TODO FUTURE POLISH: implement default cookie usage when a cookie.txt file is present
	#parser.add_argument('-n','--no-cookies', help="Don't use the default 'cookie.txt' file", required=False, action='store_true')

	return parser

### read_input():
# Get tweet urls based on either input methodology
def read_input(args) -> list:
	if args.input:
		# URLs from file
		urls = parse_searchfile(args.input)
	else:
		# URL or URLs via STDIN
		urls = args.urls[0]
		
	return urls

### parse_searchfile(): Parse a file to search, returning an array of urls
def parse_searchfile(file) -> list:
	urls = []
	
	# Iterate through list of tweets in file
	with file as f:
		# Iterate line by line
		lines = f.read().splitlines()
		for line in lines:
			# Filter out comments from that line
			url = commentFilter(line)
			if url != "":
				# Append the 'real' url to the list
				urls.append(url)
				
	# Return this filtered list
	return urls

### read_cookies(): Read and add cookies
# Intent: similar end functionality to https://github.com/ytdl-org/youtube-dl/tree/master#how-do-i-pass-cookies-to-youtube-dl
def parse_cookies(args) -> list:
	log = logging.getLogger(__name__)
	cookies = []
	
	print("Reading cookies from '" + args.cookies.name + "'")
	
	# Check each line in the cookie file
	lines = args.cookies.readlines()
	
	linenum = 0
	for line in lines:
		# Increment line iterator for better error messaging
		linenum += 1
		
		# Ignore comments and empty lines in the cookiefile
		line = commentFilter(line)
		if line == "":
			continue
			
		cookieValues = line.split('\t')

		# The netscape cookie file format expects 7 tab-separated fields per line
		if len(cookieValues) != 7:
			log.error("Unexpected cookie format at line " + str(linenum) + " of " + args.cookies.name)
			continue
		
		# Fill in the important values of the cookie from the cookiefile line
		cookie = {
			'domain': cookieValues[0],
			'path': cookieValues[2],
			'httpOnly': True,
			'secure': True,
			'sameSite':'None',
			# TODO CONSIDER: expiry?
			'name': cookieValues[5],
			'value': cookieValues[6]
		}
		
		cookies.append(cookie)
		log.debug("Loading cookie '" + cookieValues[5] + "' for '" + cookieValues[0] + "'")
	
	### Add in CSRF cookies that are necessary for yt-dlp to grab private videos
	# HUGE shoutout to this fucking guy right here: https://stackoverflow.com/questions/43814283/this-request-requires-a-matching-csrf-cookie-and-header-353-code-error-on-twitt
	# you're a lifesaver and prevented much brain damage on my part
	csrfoauth = {
		'name':'x-twitter-auth-type',
		'value': 'OAuth2Session',
		'domain':".twitter.com",
		'path':'/',
		'httpOnly':True,
		'secure':True,
		'sameSite':'None'
	}
	cookies.append(csrfoauth)
	
	csrfyes = {
		'name':'X-Twitter-Active-User',
		'value': 'yes',
		'domain':".twitter.com",
		'path':'/',
		'httpOnly':True,
		'secure':True,
		'sameSite':'None'
	}
	cookies.append(csrfyes)
	
	return cookies

### tweet_search():
async def tweet_search(args, page, url: str, currenttweet: int, num_searches: int, progress_callback):
	# Set up the metadata for the current scrape
	tisInfo = {}
	tisInfo['version'] = __version__
	tisInfo['target']  = url
	tisInfo['retrieval_time'] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z" 
	
	# Reference/context: https://stackoverflow.com/questions/19210971/python-prevent-copying-object-as-reference
	tisInfo['arguments'] = vars(copy(args))
	
	# Remove potentially sensitive arguments from the metadata that could give into on what else was scraped
	del tisInfo['arguments']['urls']
	del tisInfo['arguments']['input']
	
	# TODO FUTURE FEATURE: fix this since video needs to know
	# We still need to know whether or not cookies were used
	if args.cookies:
		del tisInfo['arguments']['cookies']
		tisInfo['arguments']['cookies'] = True
	else:
		del tisInfo['arguments']['cookies']
	
	# Get author and ID information for file naming
	tweetAuthor = url.split('/')[3]
	tweetID     = url.split('/')[5].split('?')[0]
	
	# Create object that holds data for the tweets
	search = {}
	search['args'] = args # We have this in the search object since it's not saved to the json at the end and we need the cookie file name
	search['target'] = url # Move this to just a variable and not in the object?
	search['num_searches'] = num_searches
	search['current_search_num'] = currenttweet
	search['num_tweets'] = 0
	search['json'] = {'tis': {}, 'tweets': []}
	search['json']["tis"] = tisInfo
	search['image'] = Image.new("RGBA", (0,0))
	
	# Create the zip file that capture will save to
	if args.thread == True:
		search['zip'] = ZipFile("archive_thread_" + tweetAuthor + "_" + tweetID + ".zip", 'w')
	elif args.only == True:
		search['zip'] = ZipFile("archive_single_" + tweetAuthor + "_" + tweetID + ".zip", 'w')
	else:
		search['zip'] = ZipFile("archive_" + tweetAuthor + "_" + tweetID + ".zip", 'w')
	
	# Do the thing! Returns the number of tweets captured
	search = await detect(search, page, progress_callback)
	
	if search['num_tweets'] == 0:
		# No tweets, so we delete the empty zip that was created
		search['zip'].close()
		if os.path.isfile(search['zip'].filename):
			os.remove(search['zip'].filename)
		
		# The search didn't capture anything, so we let the user know it failed by returning the URL
		return search['target']
	else:	
		### Save the results from the detection + capture ###
		# Logic for the filename of the output image and metadata
		if args.thread == True:
			filename = "capture_" + tweetAuthor + "_thread_" + tweetID
		elif args.only == True:
			# Screenshot is the term for a single tweet, such as the files for individual tweets
			filename = "capture_" + tweetAuthor + "_" + tweetID
		else:
			filename = "capture_full_" + tweetAuthor + "_" + tweetID
		
		# Only save the 'thread' buffer if you're just doing a single tweet or have multiple tweets in your default capture
		# This is so we don't make duplicates - see the logic inside of capture()
		if search['num_tweets'] > 1 or args.only == True:
			image = BytesIO()
			search['image'].save(image, format='PNG')
			saveZip(search['zip'], filename + ".png", image.getvalue())
		
		# Only save the overall json if we're not just grabbing one tweet
		if search['num_tweets'] > 1 and args.only == False:
			saveZip(search['zip'], filename + ".json", json.dumps(search['json'], indent=2))
		
		# Close the ZipFile because that's probably smart
		search['zip'].close()
		
		# Return that the search was successful
		return ""

### run_playwright(): sets up playwright and calls tweet_search()
async def run_playwright(args, urls, progress_callback: Signal):
	log = logging.getLogger(__name__)

	failedsearch = [] # Track what searches failed for output at the end of a large amount of searches
	
	progress_callback.emit((0, 0, "", 1, None))

	# Set up the web browser using playwright
	async with async_playwright() as p:
		### Firefox and chrome break in different ways
		# - on chrome, videos don't load properly to allow for differentiating GIFs from videos
		# - on firefox, the browser context isn't able to set up properly with the options
		
		try:
			browser = await p.chromium.launch()
			#browser = await p.firefox.launch()
		except PlaywrightError as browser_error:
			log.error("Playwright Install Error\nPlaywright needs to install or update the web browsers it uses for TweetInStone to work\nPlease run the command `playwright install --with-deps` in order to get Playwright functional\nFor more information on what this does, visit https://playwright.dev/python/docs/browsers\n")
			# Show the original playwright error message (b/c it's hella cute)
			#print(browser_error.name + ": " + browser_error.message)
			exit(1)
		
		### Create browser context with proper settings ###
		# Viewport is a (vertical) 4K resolution
		# With the default 4x DPI scaling, tweet width is 2396px
		# TODO POLISH: perhaps set a user agent to be polite about it?
		context = await browser.new_context(
			viewport={ 'width': 2160, 'height': 3840 },
			device_scale_factor=args.scale,
			color_scheme=args.color,
			locale=args.locale,
			timezone_id=args.timezone,
		)
		
		# Import user session cookie into browser session
		if args.cookies:
			cookies = parse_cookies(args)
			
			# Reference: https://playwright.dev/python/docs/api/class-browsercontext#browser-context-add-cookies
			await context.add_cookies(cookies)
		
		# Create the page we'll be passing to all future functions
		page = await context.new_page()
		
		# Mention the search mode for feedback to the user on what's being grabbed
		if args.thread == True:
			if args.cookies:
				print("Search mode: thread")
			else:
				print("Search mode: single tweet (due to no cookies)")
				log.warning("Thread capture is unavailable without using the --cookie option to view as a logged in user")
		elif args.only == True:
			print("Search mode: single tweet")
		else: # Default search mode
			if args.cookies:
				print("Search mode: tweet + previous tweets")
			else:
				print("Search mode: single tweet (due to no cookies)")
				log.warning("Reply capture is unavailable without using the --cookie option to view as a logged in user")
		
		currenttweet=0
		
		num_searches = len(urls)
		
		### Regardless of which method of getting urls, run the same process to detect and capture them
		for url in urls:
			currenttweet+=1
			
			# Ignore comments and empty lines
			url = commentFilter(url)
			if url == "":
				continue
			
			# Ensure that the URL is valid or not
			if not validURL(url):
				failedsearch.append(url)
				continue
		
			# Run the tweet search for that url
			progress_callback.emit((currenttweet, 0, "", 3, None))
			search_result = await tweet_search(args, page, url, currenttweet, num_searches, progress_callback)
			if search_result != "":
				failedsearch.append(search_result)
		
		# Clean up
		await page.close()
		await context.close()
		await browser.close()
		
		# Save information on failed searches
		# Useful to track failures when doing large searches
		if len(failedsearch) > 0:
			log.warning("The following searches failed:")
			for search in failedsearch:
				log.warning(" - " + search)
			
			# Save this info to a file for future use
			capturetime = datetime.now().strftime("%Y-%m-%d_%H%M-%S")
			failedfile = "failed_capture_" + capturetime + ".txt"
			saveTxt(failedfile, '\n'.join(failedsearch))
			
			log.warning("List of failed searches saved at '" + failedfile + "'")
			
			# Return these for the GUI to log them
			return (failedsearch, failedfile)
		else: # No failed searches, return empty list
			return []