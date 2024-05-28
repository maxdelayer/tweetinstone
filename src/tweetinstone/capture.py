### File to handle capture functions

## Import TIS-specific functions
from tweetinstone.version import __version__
from tweetinstone.media_ops import takeVideoBytes
from tweetinstone.file_ops import saveTxt, saveImage, saveZip, saveZipFile

## Import from libraries
import json # For json.dumps
import math # Used for video compositing
import urllib
import ffmpeg
import logging
import hashlib # For getting sha256 of images
import tempfile
import requests # For getting images

from ssl import SSLError # TODO FUTURE FIX
from datetime import datetime # Used for system-time-based metadata
from bs4 import BeautifulSoup # Used for parsing the html of the tweet text to grab emoji
from io import BytesIO # Used for storing stuff in memory instead of temporary files where feasible
from zipfile import ZipFile # Used for the zips
from sys import getsizeof # For finding video filesize
from copy import copy # Used for managing the json of arguments in a sane way
from playwright.async_api import Page, Locator, expect, TimeoutError as PlaywrightTimeoutError # Used for loading and navigating pages with playwright
from PIL import Image # For handling images

### killshot(): screenshotting what the browser looks like when you have some kind of fatal exception, for debugging purposes
# Naturally this isn't perfect for any race conditions, but it's better than nothing
async def killshot(search, page: Page):
	# Only do this if you're getting verbose/debug output
	if search['args'].verbose:
		log = logging.getLogger(__name__)
		
		errortime = datetime.now().strftime("%Y-%m-%d_%H%M-%S")
		shotname ="killshot_" + errortime + ".png"
		
		log.error("Something went wrong. Saving screenshot at time of error to " + shotname)
		finalscreenshot = await page.screenshot(scale="device")
		saveImage(shotname, finalscreenshot)

### capture_links(): Get all t.co links and what they resolve as
#async def capture_links(tweet: Locator) -> list:
async def capture_links(tweet: Locator, handle: str, id: str) -> list:
	log = logging.getLogger(__name__)
	tweetLinks = []
	
	links = await tweet.get_by_role("link").all()
	for link in links:
		tweetLink = await link.get_attribute('href')
		if tweetLink is not None:
			linkSplit = tweetLink.split('/')
			if len(linkSplit) >= 4:
				if linkSplit[2] == "t.co":
					# Navigate to t.co links and see what they resolve to
					log.debug("Resolving shortened link: " + tweetLink)
					
					linkdata = {'short': tweetLink}
					try:
						# context=ssl._create_unverified_context()
						target = urllib.request.urlopen(tweetLink).geturl()
					except urllib.error.HTTPError as HTTPError:
						# Sometimes, these return 403 errors, but do resolve correctly, so I just jank it together
						target = HTTPError.url
						# For debugging purposes, to show that the resolution had some jank in it (and in case of legit access failures), also attach the fact that the error code was received
						linkdata['error'] = "HTTP Error " + str(HTTPError.code) + ": " + HTTPError.msg
					#except SSLError:
					#	target = "UNKNOWN"
					#	linkdata['error'] = "SSL Error: " + SSLError.reason
					except urllib.error.URLError as URLError:
						target = "UNKNOWN"
						linkdata['error'] = "URL Error: " + str(URLError.reason)
					
					
					# Put THAT url in as the target
					linkdata['target'] = target
					
					# And put this data in the links array
					tweetLinks.append(linkdata)
				# TODO Future feature?:
				# See what other links there are and if they should be saved!
				#elif linkSplit[1] != handle and linkSplit[3] != id:
					#print("Other Link = " + tweetLink)
	# Return the list of links
	return tweetLinks

### capture_stats(): Get tweet stats
async def capture_stats(tweet) -> dict:
	log = logging.getLogger(__name__)
	log.debug("### Tweet stats ###")
	tweetStats = {}
	
	num_replies = ""
	num_replies = await tweet.get_by_test_id("reply").inner_text()
	if num_replies != "":
		tweetStats['replies'] = num_replies
		log.debug("# of replies = " + num_replies)
	
	retweets   = await tweet.get_by_test_id("retweet").count()
	unretweets = await tweet.get_by_test_id("unretweet").count()
	num_retweets = ""
	if retweets > unretweets:
		num_retweets = await tweet.get_by_test_id("retweet").inner_text()
	elif retweets < unretweets:
		num_retweets = await tweet.get_by_test_id("unretweet").inner_text()
	if num_retweets != "":
		tweetStats['retweets'] = num_retweets
		log.debug("# of retweets = " + num_retweets)
	
	likes      = await tweet.get_by_test_id("like").count()
	unlikes    = await tweet.get_by_test_id("unlike").count()
	num_likes = ""
	if likes > unlikes:
		num_likes = await tweet.get_by_test_id("like").inner_text()
	elif likes < unlikes:
		num_likes = await tweet.get_by_test_id("unlike").inner_text()
	if num_likes != "":
		tweetStats['likes'] = num_likes
		log.debug("# of likes = " + num_likes)
	
	bookmarks  = await tweet.get_by_test_id("bookmark").count()
	unbookmark = await tweet.get_by_test_id("removeBookmark").count()
	num_bookmarks = ""
	if bookmarks > unbookmark:
		num_bookmarks = await tweet.get_by_test_id("bookmark").inner_text()
	elif bookmarks < unbookmark:
		num_bookmarks = await tweet.get_by_test_id("removeBookmark").inner_text()
	if num_bookmarks != "":
		tweetStats['bookmarks'] = num_bookmarks
		log.debug("# of bookmarks = " + num_bookmarks)
	
	return tweetStats

### capture_text(): get the text in a smarter way that gets emoji
def capture_text(html: str) -> dict:
	log = logging.getLogger(__name__)
	
	# Use beautifulsoup to parse the text and include emojis
	soup = BeautifulSoup(html, 'lxml')
	
	strings = []
	
	# Parse the strings via html to properly grab emoji
	# If it's a string we want to capture, capture it
	for tag in soup.find_all():
		# <a> and <div> live inside of <span> so don't add them to the list of strings, just remove CSS information
		if tag.name == 'a':
			del tag['class']
			tag.unwrap()
		elif tag.name == 'div':
			del tag['class']
			tag.unwrap()
		# <span> has the text inside of it
		elif tag.name == 'span':
			tagtext = tag.get_text()
			# TODO EDGE CASE: this doesn't always capture newlines properly before hashtags
			#if tagtext == "\n":
			#	strings.append("\n\n")
			#else:
			strings.append(tagtext)
			del tag['class']
		# <img> are used for emoji display (lmao)
		elif tag.name == 'img':
			emoji = tag['alt'] # alt text has the real emoji unicode
			
			# Append emoji to previous string if previous string exists
			if len(strings) > 0:
				strings[-1] = strings[-1] + emoji
			else:
				strings.append(emoji)
			#del tag['src']
			del tag['class']
			del tag['draggable']
		elif tag.name != 'body' and tag.name != "html":
			log.error("Unknown tag '" + tag.name + "' in tweet text")
	
	textInfo = {}
	textInfo['html'] = str(soup)
	
	# Useful if you want to view the html content
	#log.debug(soup.prettify())
	
	# Concatenate all relevant strings together to get the text of the tweet
	textInfo['text'] = ''.join(strings)
	
	log.debug("Tweet Text: '" + textInfo['text'] + "'")
	
	return textInfo

### capture_images(): get the images from a tweet
# Moved this here to make capture() a bit easier on the eyes
# Buuuuuut mainly because I want to call it even if we've composited a video
# For example, a QRT that has a video, QRTing an image
# Or a QRT with an image that is QRTing a video
async def capture_images(zip: ZipFile, tweet: Locator, tweetInfo, directory):
	log = logging.getLogger(__name__)
	log.debug("### IMAGE CAPTURE ###")
	
	# TODO EDGE CASE: have it so that it checks that the <a> link wrapped around the image has an href of the current tweet - and then grab the rest on the quote	
	imageArray = []
	
	tweetPhoto = tweet.get_by_test_id("tweetPhoto")
	
	images = await tweetPhoto.all()
	
	imageiterator = 0
	for image in images:
		# Increment iterator that's used for file name strings
		imageiterator += 1
		
		# Make sure this image isn't just a video thumbnail
		try:
			videoPlayer = image.get_by_test_id("videoPlayer")
			await expect(videoPlayer).to_have_count(0)
		except AssertionError as exception:
			# There is a video player in this tweetPhoto, so exit
			continue
		
		# We'll have to clean up the url, but this will give us what we need
		imageUrl = await image.get_by_role("img").get_attribute("src")
		
		# Get the name and the format of the image from that thumbnail link
		imageName   = imageUrl.split('/')[4].split('?')[0]
		imageFormat = imageUrl.split('/')[4].split('?')[1].split('&')[0].split('=')[1]
		
		# Okay so, sometimes it 'says' it's webp, but that doesn't actually fucking work (???)
		# jpg tends to work in this edge case though
		if imageFormat == 'webp':
			imageFormat = 'jpg'
		
		# Reconstruct the link to download the best quality version of the image
		image_original = "https://pbs.twimg.com/media/" + imageName + "?format=" + imageFormat + "&name=orig"
		
		log.debug("Image #" + str(imageiterator) + ": " + imageUrl + imageFormat)
		
		# TODO OPTIMIZATION: potentially use asyncio for this more directly?
		# Reference: https://likegeeks.com/downloading-files-using-python/
		imageData = requests.get(image_original)
		# TODO EDGE CASE: in the future, just check if the returned image is zero bytes and then do the request again?
		
		# Returns 'image' for images without alt text
		imageAlt = await image.get_by_role("img").get_attribute("alt")
		
		# Write image to file
		image_filename = "image_" + tweetInfo['author'] + "_" + tweetInfo['id'] + "_n" + str(imageiterator) + "_id_" + imageName + "." + imageFormat
		saveZip(zip, directory + image_filename, imageData.content)
		
		# Reference: https://docs.python.org/3/library/hashlib.html
		imageHash = hashlib.sha256()
		imageHash.update(imageData.content)
		
		imageArray.append({'url': image_original, 'alt': imageAlt, 'sha256': imageHash.hexdigest()})
	return imageArray

### capture_video()
# Lots of insane ffmpeg magic
# Beware ye who enter here
async def capture_video(args, zip: ZipFile, tweet: Locator, directory: str, name: str, progress_callback):
	log = logging.getLogger(__name__)
	log.debug("### VIDEO CAPTURE ###")
	
	# TODO FUTURE FEATURE: REPLACE WITH WORKER PROGRESS FROM GUI
	print(" - Downloading and compositing video (this may take some time)")
	# Send signal that we're downloading the video
	progress_callback.emit((0, 0, "", 5, None))
	
	#args = search['args']
	
	tweetVideo = tweet.get_by_test_id("videoPlayer")
	
	vidcount = await tweetVideo.count()
	if vidcount > 1:
		tweetVideo = tweet.get_by_test_id("videoPlayer").first
	
	### TODO RELEASE INVESTIGATE: yt.dl for these multiple video links to grab each instead of tweet?
	# TODO RELEASE TEST: test clicking on video to play it, seeing the network activity, and using youtube-dl on it
	# the link that starts with https://video.twimg.com/ext_tw_video/ 
	# https://playwright.dev/python/docs/api/class-request
	# request = tweet.page.on("request", handler)
	
	# get its a get request
	# request.method
	
	# check its the m3u8 by using 
	# request.resource_type (should bne x-mpegurl?)
	# NO WAIT THIS MAY BE ON RESPONSE
	
	# then we can get the url of the request
	#https://playwright.dev/python/docs/api/class-request#request-url
	# request.url
	### End multi-video investigation
	
	### Get the requisite files for the composite ###
	# Take a screenshot masking out the video portion
	screenshot = await tweet.screenshot(scale="device", mask=[tweetVideo])
	
	# Write the 'mask' screenshot to a temporary file for FFMPEG to use
	imagefile = tempfile.NamedTemporaryFile()
	imagefile.write(screenshot)
	
	# Use yt-dlp to grab the video
	download = await takeVideoBytes(args.cookies, tweet.page.url)
	if download[0] != 0:
		# The yt-dlp download failed. Safely exit the capture and mark the search as failed to fail safely
		return (False, screenshot)
	
	videoBytes = download[1]
	
	# TODO FUTURE OPTION
	# Error out if the video is too large for the current settings (also: this is a yt-dlp option)
	vidsize = getsizeof(videoBytes)
	print("Vid size = " + str(vidsize))
	
	# TODO FUTURE FEATURE: move this over to multi-video capture?
	# Save the original video to zip
	videoBytes.seek(0)
	saveZip(zip, directory + "video_" + name + ".mp4", videoBytes.read())
	
	# Save the video to a temporary file that FFMPEG can easily see because getting ffmpeg-python to take two separate inputs through stdin would cost me sanity points that I cannot afford to lose
	# Reference: https://docs.python.org/3/library/tempfile.html
	vidfile = tempfile.NamedTemporaryFile()
	videoBytes.seek(0)
	vidfile.write(videoBytes.read())
	
	### Composite the video together ###
	# Bounding boxes of the page's elements are used to calculate sizes and offsets for ffmpeg magic
	tweetbox = await tweet.bounding_box()
	vidbox   = await tweetVideo.bounding_box()
	
	# I do multiple pads on the clip; the second pad is purely to blend in with the background of the tweet, which is small but scales with the DPI
	# This sets the color of the second pad:
	if args.color == 'light':
		bordercolor = 'white'
	else:
		bordercolor = 'black'
	
	# Size of the border pad. Just needs to be big enough to handle any minor misalignments
	bordersize = args.scale * 5
		
	# The third pad is the full pad which sizes it to the full tweet for the overlay. 
	# it's magenta because it will fill in the keyed out parts of a user's avatar that had the exact same magenta color in the png mask
	
	# Overall the scaling/offsets seem to break at non-even resolution scales?
	
	# The x/y size of the tweet image, grabbed from that image itself
	probe = ffmpeg.probe(imagefile.name)
	video_streams = [stream for stream in probe["streams"] if stream["codec_type"] == "video"]
	tweetWidth  = video_streams[0]['width']
	tweetHeight = video_streams[0]['height']
	
	# The x/y size of the box the video is embedded in
	videoBoxWidth    = vidbox["width"]  * args.scale
	videoBoxHeight   = vidbox["height"] * args.scale
	
	# Grab the TRUE video size from the video file itself
	probe = ffmpeg.probe(vidfile.name)
	# Kudos to https://stackoverflow.com/a/58896685 for keeping it simple & easy
	video_streams = [stream for stream in probe["streams"] if stream["codec_type"] == "video"]
	
	# Make sure this uses the height if it was scaled accurated with the DPI of the tweet
	videoWidth = video_streams[0]['width']
	videoHeight = video_streams[0]['height']
	
	### Calculation of black bar crop size to preserve aspect ratio
	# Get the videoBoxHeight divided by videoHeight
	heightratio = videoBoxHeight/videoHeight
	# Multiple the videoWidth by that ratio
	cropwidth = videoWidth * heightratio
	# Subtract that from the videoBoxWidth, divide by 2 (since we pad it on each side)
	croppad = (videoBoxWidth - cropwidth)/2
	# Round up to an even number
	croppad = math.ceil(croppad)

	# If the pad is under a pixel (according to DPI scale) then just set it to 0
	# All of this croppad math is for vertical videos that have horizontal black bars in twitter's view, so if it's insignificant let's not worry about any warping
	# TODO OPTIMIZATION: perhaps one day double check the perfection of the 'true' original screenshot INSTEAD of doing this
	if croppad < args.scale:
		croppad = 0
		
	# Add extra horizontal padding based on that number
	
	# TODO POLISH EDGE CASE: what if these get negative or weird? should I just absolute value them?
	# The +2 here just helps align... wonky but works. Maybe not neede if the aspect ratio black bars were always around but I'm paranoid at this point
	# xoffset and yoffset are the offsets of the 'video box' inside the wider tweet
	xoffset = (round(vidbox["x"]) - round(tweetbox["x"]) + 2)*args.scale - bordersize
	yoffset = (vidbox["y"] - tweetbox["y"])*args.scale - bordersize
	
	videoin    = ffmpeg.input(vidfile.name)
	tweetaudio = videoin['a?'] # The '?' is in case the video has no audio
	tweetpng   = ffmpeg.input(imagefile.name)
	videoOut   = tempfile.NamedTemporaryFile()
	
	# No, I don't want to talk about it. It just works now.
	tweetvideo = (
		ffmpeg
		# Scale vid up to the box size BUT preserve aspect ratio by reducing width by black bar size
		.filter(videoin.video, 'scale', str(videoBoxWidth - (croppad * 2)), str(videoBoxHeight))
		# Pad in black bars by padding to box size with black bar as x offset
		.filter('pad', w=str(videoBoxWidth), h=0, x=str(croppad), y=0, color='black')
		# Pad a border around the video in case of edge case misalignment because paranoia
		.filter('pad', w=str(videoBoxWidth + (bordersize * 2)), h=str(videoBoxHeight + (bordersize * 2)), x=str(bordersize), y=str(bordersize), color=bordercolor)
		# Pad to place this output where the video box is inside the wider tweet
		.filter('pad', w=str(tweetWidth), h=str(tweetHeight), x=str(xoffset), y=str(yoffset), color='magenta')
		.overlay(tweetpng.filter('colorkey', 'magenta', 0.01, 0))
	)
	# TODO FUTURE OPTIMIZATION: use colorkey_opencl for GPU-acceleration as an option, but you have to do hwupload and hwdownload and shit, see ffmpeg filter documentation in the opencl section
	
	# Random semi-related link: https://curiosalon.github.io/blog/ffmpeg-alpha-masking/#alpha-manipulation-with-ffmpeg
	# Thank you, you ffmpeg wizard; this isn't what i used but it blew my mind
	
	log.debug("Beginning composite via ffmpeg")
	
	progressfile = tempfile.NamedTemporaryFile()
	try:
		progress_callback.emit((0, 0, progressfile.name, 5, None))
		vidprocess = (
			ffmpeg
			#.output(tweetaudio, "video_" + videoFilename, v='info', progress=True, nostats=True)
			.output(tweetvideo, tweetaudio, videoOut.name, format='mp4', progress=progressfile.name)
			.run(quiet=(not args.verbose), overwrite_output=True)
			#.output(tweetvideo, tweetaudio, "pipe:", format='rawvideo', pix_fmt='rgb24')
			#.run_async(pipe_stdout=True)
		)
	except ffmpeg._run.Error as ffmpegError:
		log.error("ffmpeg error output:" + ffmpegError.stderr.decode("utf-8"))
		sys.exit(1) # TODO RELEASE: DO SIMILAR ERROR HANDLING AS THE YT DL OUTPUT ERROR SO IT DOESNT KILL ALL SEARCHES
	
	# TODO OPTIMIZATION: release progressfile?
	
	# TODO POLISH: investigate ffmpeg's `-metadata` flag to add title and other metadata to video
	
	# Save the composited video to zip
	saveZipFile(zip, directory + "capture_" + name + ".mp4", videoOut.name)
	
	### Generate a png out of the first frame of the video we just made ###
	log.debug("Grabbing thumbnail via ffmpeg")
	try:
		thumbprocess = (
			ffmpeg.input(videoOut.name)
			.output(imagefile.name, vframes=1, format='apng')
			#.run(capture_stdout=False, capture_stderr=False, overwrite_output=True)
			.run(quiet=(not args.verbose), overwrite_output=True)
		)
	except ffmpeg._run.Error as ffmpegError:
		log.error("ffmpeg error output:" + ffmpegError.stderr.decode("utf-8"))
		sys.exit(1) # TODO RELEASE: DO SIMILAR ERROR HANDLING AS THE YT DL OUTPUT ERROR
	
	# Read the image into memory for the thread image buffer
	vidThumb = Image.open(imagefile.name)
	image = BytesIO()
	vidThumb.save(image, format='PNG')
	screenshot = image.getvalue()
	
	# Save this composited image to the zip
	saveZip(zip, directory + "capture_" + name + ".png", screenshot)
	
	#log.debug("Testing link printout")
	# TODO FUTURE FEATURE: get links to every video, like with images
	#mediaInfo['videos']
	#vids = await tweetVideo.all()
	#vidsJSON = {}
	#for vid in vids:
	#	# We'll have to clean up the url, but this will give us what we need
	#	log.debug("\n\tall vids:")
	#	vidtext = await vid.text_content()
	#	print(vid)
	#	print(vidtext)
	#	print("----")
	#	for vi in await vid.all():
	#		log.debug("\n\tvi:")
	#		print(vi)
	#		vidURL = await vi.get_attribute("src")
	#		if vidURL is not None:
	#			log.debug("src = " + vidURL)
	
	# TODO future feature: better video metadata
	#mediaInfo['video2'] = []
	#mediaInfo['videos'].append('')
	
	### TODO CRIT RELEASE: test getting links
	#vids = await tweetPhoto.all()
	#imagesJSON = {}
	# TODO: see; what I do in the image link grabber
	#for image in images:
	
	# TODO FUTURE FEATURE:
	### GIF detection & processing
	# For the sake of making a gif tweet just exist as a gif, let's cut the bullshit and do it for you
	# This can also be accomplished via some ffmpeg wizardry
	# TODO POLISH: toggle-able algorithm to optimize GIF for a target file size for sharing on platforms such as discord
	videotext = await tweetVideo.text_content()
	if videotext == "GIF": # This is broken in chrome! it works in firefox but there are other problems with firefox in playwright!
		print("This tweet is a GIF! tweetinstone cannot auto-convert GIFs at this time")
		
		# TODO FUTURE: do this ffmpeg magic but in python
		#ffmpeg -loglevel quiet -i input.mp4 -vf "fps=$FRAMERATE,scale=$WIDTH:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" -loop 0 output.mp4
		
		# TODO POLISH: have support for and options for gif optimization techniques
		#gifsicle -O3 --lossy=$LOSSYLEVEL -o temporary-lossy.gif input.mp4
		
		# TODO OPTION: have some sort of timeout option based on video length/size?
	
	log.debug("Video capture done")
	return (True, screenshot)

# TODO FUTURE: POLISH with metadata on single
# Captures the blank boxes that indicate deleted/inaccessable tweets
async def deleted_capture(search: dict, tweet: Locator, url: str, errormessage: str) -> dict:
	log = logging.getLogger(__name__)
	
	# Since the tweet doesn't have data in it, guess based on the url
	handle =  url.split('/')[3]
	id = url.split('/')[5].split('?')[0]
	name = handle + "_" + id

	print(' - Capturing tweet #' + str(search['current_tweet_iterator']) + ' (Deleted with message: "' + errormessage + '")')

	# Just grab the screenshot of the error message
	screenshot = await tweet.screenshot(scale="device")

	# Return the screenshot bytes (for potential concatenation) and json metadata (for thread-wide metadata)
	log.debug("Tweet capture complete for deleted tweet")
	
	# TODO FUTURE: get json saying the errormessage
	output = {}
	#output['json'] = tweetInfo
	output['screenshot'] = screenshot
	return output

### capture(): take the screenshot and relevant metadata of an individual tweet
# This also includes calling any other functions for formatting these tweets
async def capture(search: dict, tweet: Locator, handle: str, id: str, progress_callback) -> dict:
	log = logging.getLogger(__name__)
	name = handle + "_" + id
	imageFilename = "capture_" + name + ".png"
	
	progress_callback.emit((0, search['current_tweet_iterator'], handle + "/status/" + id, 4, None))
	
	# Directory for where we save files in the zip
	if search['current_tweet_iterator'] == 1 and search['args'].thread == False and search['target'].split('/')[5].split('?')[0] == id:
		# If this is the first tweet being captured 
		# AND we aren't grabbing a thread
		# AND it matches the tweet at the very beginning of the search
		# Then we want to just save any files from it at the root directory of the zip
		directory = ""
	elif search['args'].only == True:
		# if we're only grabbing a single tweet, set directory as the root directory
		directory = ""
	else:
		# Set the directory to be a folder for this specific tweet
		# Author coming after ID makes more logical sense to me, but ID before author means that the folder structure will automatically sort into chronological order. Elegance over style.
		directory = id + "_" + handle + "/"
	
	print(' - Capturing tweet #' + str(search['current_tweet_iterator']) + ' (' + handle + '/status/' + id + ')')
	
	### Scrape tweet text/metadata: ###
	# Create fresh objects for final JSON:
	tisInfo   = {}
	tweetInfo = {}
	mediaInfo = {}
	
	# Metadata on when this tweet was snapshotted
	tisInfo['version']        = __version__
	tisInfo['retrieval_time'] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
	tisInfo['arguments']      = vars(copy(search['args']))
	
	# Remove potentially sensitive arguments from the metadata that could give into on what else was scraped
	del tisInfo['arguments']['urls']
	del tisInfo['arguments']['input']
	del tisInfo['arguments']['cookies']
	
	tweetInfo['author'] = handle
	tweetInfo['id']     = id
	tweetInfo['url']    = "https://twitter.com/" + tweetInfo['author'] + "/status/" + tweetInfo['id']
	
	try:
		translated = False
		
		# Detect and click the buttons to view content and/or translate posts
		buttons = await tweet.get_by_role("button").all()
		for button in buttons:
			if button is not None:
				# Sometimes the last button disappears and causes the search to bug out
				# Ignore this
				try:
					buttontext = await button.text_content(timeout=3000)
				except PlaywrightTimeoutError:
					break
				
				# Translate tweets
				# Translations only work when you have cookies
				#if hasattr(search['args'], 'cookie'):
				if search['args'].cookies:
					if buttontext == "Translate post":
						await button.click()
						log.debug("Pushed 'Translate post' button")
						translated = True
						#break
				
				if buttontext == "View":
					await button.click()
					log.debug("Pushed 'view sensitive content' button")
					#break
				
				# Detect content warning
				if buttontext == "Show":
					# for content warning reason, compare before/after clicking button
					# jank but it works since the actual text of the reason isn't easily addressible
					beforetext = await tweet.inner_text()
					
					await button.click()
					log.debug("Pushed 'view content warning' button")
					
					aftertext = await tweet.inner_text()
					
					beforelines = beforetext.splitlines()
					afterlines = aftertext.splitlines()
					
					for before, after in zip(beforelines, afterlines):
						if before != after:
							# For the content warning label, the text that is in its place instead is the text of the hide button
							# Maybe there's an edge case here with alt text button? But this is good enough
							if after == "Hide":
								# Removing prefix to just get the reason
								contentwarning = before.replace('Content warning: ','', 1)
								# TODO OPTIMIZATION: replace with this after I'm using >=3.9
								#contentwarning = before.removeprefix('Content warning: ')
								
								log.debug("Content warning: " + contentwarning)
								mediaInfo['content_warning'] = contentwarning
								break
					#break
		
		# Use the 'last' time because QRTs have the inner tweet's time first
		tweetInfo['time']   = await tweet.get_by_role("time").last.get_attribute('datetime')
		
		# Grab the raw text from the tweet too, which may or may not exist
		textSearch      = tweet.get_by_test_id("tweetText")
		tweetTextCount  = await textSearch.count()
		if tweetTextCount > 0:
			# These are the old way of grabbing text info:
			#tweetInfo['text'] = await textSearch.first.text_content()
			#tweetInfo['text'] = await textSearch.first.inner_text()
			
			# Grab the HTML from playwright
			# Must be first because QRTs have text of both
			tweetHTML = await textSearch.first.inner_html()
			
			cleanedText = capture_text(tweetHTML)
			
			# Save the 'clean' html and text to the json
			tweetInfo['text'] = cleanedText['text']
			tweetInfo['html'] = cleanedText['html']
			
			# Attempt to fetch translation
			if translated:
				tweetHTML = await textSearch.nth(1).inner_html()
				
				cleanedText = capture_text(tweetHTML)
				
				# Save the 'clean' html and text to the json
				tweetInfo['translation'] = {'text': cleanedText['text'], 'html': cleanedText['html']}
		
		# Get all t.co links
		tweetInfo['links'] = await capture_links(tweet, handle, id)
		
		### QRT Metadata Capture ###
		# Detect if it's a QRT and grab relevant QRT metadata
		tweetAuthorCount  = await tweet.get_by_test_id("User-Name").count()
		tweetArticleCount = await tweet.get_by_role("article").count()
		
		quoteInfo = {}
		if tweetAuthorCount > 1:
			quoteInfo['author'] = (await tweet.get_by_test_id("User-Name").last.text_content()).split('@')[1].split(u'\u00b7')[0]
			
			# Grab the URL by going to the page since a real 'link' doesnt exist in the html
			await tweet.get_by_test_id("User-Name").last.click(position={'x': 1,'y': 1}) 
			await tweet.page.wait_for_load_state("domcontentloaded")
			
			quoteURL = copy(tweet.page.url)

			# TODO FUTURE POLISH: GRAB IMAGES FROM THE THING BEING QRTed
			# TODO FUTURE POLISH: while we're here, grab more data from the quoted tweet itself such as images?
			# TODO EDGE CASE: grab text from QRT page itself (here) in case of long text that gets cut off?
			# TODO POLISH: grab images based on the link in the QRT
			
			# TODO POLISH: grab links of a quoted tweet
			#quoteInfo['links'] = await capture_links(tweet)
			
			# Return to our original tweet
			await tweet.page.go_back(wait_until='domcontentloaded')
			
			quoteInfo['id']   = quoteURL.split('/')[5].split('?')[0]
			quoteInfo['url']  = "https://twitter.com/" + quoteInfo['author'] + "/status/" + quoteInfo['id']
			quoteInfo['time'] = await tweet.get_by_role("time").first.get_attribute('datetime')
			
			# TODO FUTURE POLISH: do I need to do better parsing with html for quote tweets?
			quoteInfo['text'] = await textSearch.last.text_content()
			
			# Put this quote tweet info into the tweet's metadata
			tweetInfo['quoting'] = quoteInfo
		elif tweetArticleCount > 0: # Detect deleted, suspended, or private tweets
			articles = await tweet.get_by_role("article").all()
			for article in articles:
				articletext = await article.text_content()
				if articletext == "This post is unavailable.":
					quoteInfo['id'] = 'unavailable'
					quoteInfo['text'] = articletext
					tweetInfo['quoting'] = quoteInfo
				# TODO EDGE CASE POLISH: show a QRT of a private tweet
				#elif articletext == "This post is unavailable.":
				#	quoteInfo['id'] = 'private'
				#	quoteInfo['text'] = articletext
				#	tweetInfo['quoting'] = quoteInfo
		
		# TODO FUTURE POLISH?
		# Detect the type of inner article that shows up with the learn more box
		
		### Media detection and capture ###
		tweetPhoto = tweet.get_by_test_id("tweetPhoto")
		tweetVideo = tweet.get_by_test_id("videoPlayer") # Detect if there is a video (Also used to mask it out of the screenshot with this locator)
		tweetVideoCount = await tweetVideo.count()
		tweetPhotoCount = await tweetPhoto.count()
		
		log.debug("### MEDIA DETECTION ###")
		log.debug("Videos detected: " + str(tweetVideoCount))
		log.debug("Images detected: " + str(tweetPhotoCount-tweetVideoCount))
		
		# TODO FUTURE READABILITY: separate component steps into functions for comprehension?
		# If there's a SINGLE video, composite the video into the tweet
		#if tweetVideoCount > 0: # TODO FUTURE FEATURE: change back to this when video + image and multivideo works
		if tweetVideoCount == 1:
			video_output = await capture_video(search['args'], search['zip'], tweet, directory, name, progress_callback)
			
			# TODO FUTURE OPTIMIZATION: any files needed to clean up?
			if video_output[0] == False:
				output = {}
				output['successful'] = False
				
				return output
			screenshot = video_output[1]
			
			# TODO FUTURE FEATURE: better video metadata
			mediaInfo['video'] = True
			#mediaInfo['videos'] = []
			#mediaInfo['videos'].append('')
			
			# Also capture images just in case there is one via QRTing
			# TODO CRIT FUTURE FEATURE TEST AND POLISH
			#if tweetPhotoCount > tweetVideoCount:
			#	mediaInfo['images'] = await capture_images(search['zip'], tweet, tweetInfo, directory)
		elif tweetPhotoCount > tweetVideoCount:
			# There are more (# of photos + videos) than (# of videos), so capture all photos
			mediaInfo['images'] = await capture_images(search['zip'], tweet, tweetInfo, directory)
			
			screenshot = await tweet.screenshot(scale="device")
			
			# As long as we don't want JUST this tweet, save the image to file
			# This is because the 'thread' image will be effectively the same for a single tweet
			if search['args'].only == False:
				saveZip(search['zip'], directory + "capture_" + name + ".png", screenshot)
			
			log.debug("Image capture done")
		else:
			# No media detected
			# Just grab the screenshot and no other files
			screenshot = await tweet.screenshot(scale="device")
			
			# As long as we don't want JUST this tweet, save the image to file
			# This is because the 'thread' image will be effectively the same
			if search['args'].only == False:
				saveZip(search['zip'], directory + "capture_" + name + ".png", screenshot)
		
		# Write media metadata to json object
		tweetInfo['media'] = mediaInfo
		
		# Get stats
		tweetInfo['stats'] = await capture_stats(tweet)
		
		# Put all tweet metadata in one object
		tweetMetadata = {"tis": tisInfo, "tweet": tweetInfo}
		
		saveZip(search['zip'], directory + "data_" + name + ".json", json.dumps(tweetMetadata, indent=2))

		# Return the screenshot bytes (for potential concatenation) and json metadata (for thread-wide metadata)
		output = {}
		output['json'] = tweetInfo
		output['screenshot'] = screenshot		
		output['successful'] = True
		
		log.debug("Tweet capture complete for '" + name + "'")
		
		return output
	except PlaywrightTimeoutError:
		print("ERROR: Timeout during capture of '" + handle + "/status/" + id + "'")
		await killshot(search, tweet.page)
		
		output = {}
		output['successful'] = False
		
		# TODO RELEASE: consider?
		raise
		
		return output