### Media Operations ###
# Functions that deal with video or images

import logging
from PIL import Image # Used for image operations. # Reference: https://pillow.readthedocs.io/en/stable/reference/Image.html

from io import BytesIO, StringIO # Used for storing stuff in memory instead of temporary files where feasible
from contextlib import redirect_stdout, redirect_stderr # Used for wacky bullshit
from yt_dlp import YoutubeDL, DownloadError # yt-dlp used for youtube video download. Reference: https://github.com/yt-dlp/yt-dlp#embedding-yt-dlp

from sys import getsizeof

### concatenate(): Combine two images vertically
# Used for making threads into one big image by concatenating to the same Image object during recursion
# The 'bottom' image is raw bytes which get added below the 'origin' PIL Image object's image
def concatenate(origin: Image, bottom: bytes) -> Image:
    # Open the byte stream as an image to get stats
	bottomImage = Image.open(BytesIO(bottom))
	
	# Create a new image with the height of both and the highest width of boths
	combinedImage = Image.new("RGBA", (max(origin.width, bottomImage.width), (origin.height + bottomImage.height)))
	
    # Paste both images into the new image
	combinedImage.paste(origin, (0, 0))
	combinedImage.paste(bottomImage, (0, origin.height))
    
	bottomImage.close()
	
	return combinedImage

# TODO REMOVE: Not used anymore - but maybe useful later?
### takeVideo(): Download the video to a file and return that filename
# Useful reference: https://github.com/ytdl-org/youtube-dl/tree/master#embedding-youtube-dl
def takeVideo(url: str) -> str:
	handle  = url.split("/")[3]
	tweetid = url.split('/')[5].split('?')[0]
	
	# Create the filename based on the tweet author and ID
	# TODO POLISH: Should file extension be instead based on youtube-dl's documentation?
	# Reference: https://github.com/ytdl-org/youtube-dl#output-template
	outputname = "video_" + handle + "_" + tweetid + ".mp4"

	ydl_opts = {
		'format': 'best',
		'logger': ytdlp_logger(),
		'quiet': True,
		'outtmpl': outputname,
		'progress_hooks': [progresshook]
	}
	with YoutubeDL(ydl_opts) as ydl:
		ydl.download([url])
	
	# Return the name of the file for future manipulation
	return outputname

# TODO FUTURE: optimize
### TakeVideoBytes(): download video from a url to a bytesio object
async def takeVideoBytes(cookiefile, url: str) -> (int, BytesIO):
	# Output to stdout, which we redirect into a BytesIO so that it doesn't touch the filesystem until we're ready
	# Kudos to https://github.com/ytdl-org/youtube-dl/issues/17379#issuecomment-521804927
	log = logging.getLogger(__name__)
	
	if cookiefile is not None:
		log.debug("Attempting video download with cookies")
		ydl_opts = {
			'format': 'best',
			#'logger': ytdlp_logger(),
			'quiet': True,
			'outtmpl': '-',
			'logtostderr': True,
			#'progress_hooks': [progresshook],
			'cookiefile': cookiefile.name # Uses the same cookie file
		}
	else:
		log.debug("Attempting video download without cookies")
		ydl_opts = {
			'format': 'best',
			#'logger': ytdlp_logger(),
			'quiet': True,
			# TODO Optimization: test this
			'logtostderr': True,
			#'verbose': True,
			'outtmpl': '-'
			#'progress_hooks': [progresshook]
		}
	
	video = BytesIO()
	stdouterr = StringIO()
	status = 0
	
	try:
		with redirect_stderr(stdouterr):
			with redirect_stdout(video):
				with YoutubeDL(ydl_opts) as ydl:
					ydl.download([url])
	# TODO FUTURE: better handling of errors?
	except DownloadError as DLError:
		log.error("Search failed due to yt-dlp error")
		log.error("yt-dlp error message: '" + DLError.msg + "'")
		status = 1
	
	# Sometimes, for mysterious reasons, the video is empty without there being a ytdl error
	# This will mean the bytesio object will be 'empty' (80 bytes, with value of "b''")
	# If this happens, report that the download failed
	vidsize = getsizeof(video)
	log.debug("Video size: " + str(vidsize) + " bytes")
	if status == 0 and vidsize == 80:
		if str(video.getvalue()) == "b''":
			log.error("The downloaded video was a failure for unknown reasons (returned empty)")
			status = 1
	
	# TODO FUTURE OPTION
	# Error out if the video is too large for the current settings (also: this is a yt-dlp option)
	
	# Return the BytesIO buffer of the video
	return (status, video)

# TODO FUTURE FEATURES:
### yt-dlp logger
# Useful for logging with youtube-dl
# Basically just copied from their example
# TODO: Right now though, the logger doesn't gel well with directing output to stdout (duh!) so I may just remove this later
class ytdlp_logger:
	def debug(self, msg):
		# For compatibility with youtube-dl, both debug and info are passed into debug
		# You can distinguish them by the prefix '[debug] '
		if msg.startswith('[debug] '):
			pass
		else:
			self.info(msg)

	def info(self, msg):
		pass

	def warning(self, msg):
		pass

	def error(self, msg):
		print(msg)
		
# TODO FUTURE FEATURE: https://github.com/yt-dlp/yt-dlp#adding-logger-and-progress-hook
# See "progress_hooks" in help(yt_dlp.YoutubeDL)
# TODO: Right now though, progress hooks don't gel well with directing output to stdout (duh!) so I may just remove this later
def progresshook(d):
	if d['status'] == 'error':
		print('ERROR during video download')
	if d['status'] == 'downloading':
		print('Downloading video ...')
	if d['status'] == 'finished':
		print('Done downloading, now post-processing ...')
