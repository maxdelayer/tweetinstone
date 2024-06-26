### file_ops.py
# File operation functions for tweetinstone
# I wanted to have these be wrapper functions so that I could have options to switch between writing to the filesystem or writing to something else like S3

import logging
import asyncio
import time
from PySide6.QtCore import Signal
from zipfile import ZipFile # Used for the zips
# TODO FUTURE: import boto3?

# TODO FUTURE FEATURE: have all of these specify a different output directory if that directory is specified as argument!!!
# TODO FUTURE: maybe have a new func for this?
#def concatpath

### saveTxt(): Generalized wrapper function for saving text files
# Because *where* the file is saved could change based on some settings
def saveTxt(filename: str, text: str) -> None:
	#if args.directory:
		# TODO FUTURE FEATURE: figure out how to do this https://docs.python.org/3/library/os.path.html
	#	dir = args.directory 
	#	location = dir + "/" + filename
	#else:
	#	location = filename

	if True:
		open(filename, 'w').write(text)
	#else:
		### TODO FUTURE FEATURE: Save to S3 instead

### saveImage(): Generalized wrapper function for saving an image to file
# Because *where* the file is saved could change based on some settings
def saveImage(filename: str, bytes) -> None:
	if True:
		open(filename, 'wb').write(bytes)
	#else:
		### TODO FUTURE FEATURE: Save to S3 instead

### SaveZip(): Write data to zip at 'filename'
def saveZip(zip: ZipFile, filename: str, data) -> None:
	zip.writestr(filename, data)

### saveZipFile(): Write already existing file to zip at 'filename'
def saveZipFile(zip: ZipFile, filename: str, file) -> None:
	zip.write(file, arcname=filename)

### gen_cookie(): Generate a cookie file from an auth_token string
def gen_cookie(auth_token: str, filename):
	log = logging.getLogger(__name__)
	
	cookietext = "# Netscape HTTP Cookie File"
	cookietext += "\n# This cookie file '" + str(filename) + "' was automatically generated by TweetInStone"
	cookietext += "\n\n### WARNING WARNING WARNING ###"
	cookietext += "\n# DO NOT SHARE THIS FILE!!!\n"
	
	# The actual cookie text
	cookietext += "\n.twitter.com\tTRUE\t/\tTRUE\t0\tauth_token\t" + auth_token
	
	saveTxt(filename, cookietext)
	log.debug("Generated cookie file at '" + str(filename) + "'")

### check_progress_file(): asynchronous function to repeatedly check the last lines of an ffmpeg progress file
# TODO FUTURE: consider optimizing this with the exponential search algorithm in https://www.geeksforgeeks.org/python-reading-last-n-lines-of-a-file/ ?
async def check_progress_file(filename: str, progress_callback: Signal):	
	# Specify 3 of the progress values up front as variables
	frame = "0"
	fps = "0"
	progress="continue"
	
	# Loop checking the progress file continuously to report ffmpeg progress
	while True:
		# Exit loop if last read of progress file indicated ffmpeg was complete
		if progress == "end":
			break
	
		try:
			values = []
		
			with open(filename) as file:
				# loop to read iterate 
				# last 12 lines (since the progress has 12 repeating keys. I don't think order would matter)
				for line in (file.readlines() [-12:]):
					values.append(line[:-1]) # remove last line of string since it is a newline
			
			# capture frame and fps, the two values we care about
			for key in progress:
				key = key.split('=')
				if key[0] == 'frame':
					frame = key[1]
				elif key[0] == 'fps':
					fps = key[1]
				elif key[0] == 'progress':
					fps = key[1]
					
			progress_callback.emit((0, 1, "Frame: " + frame + " / FPS: " + fps, 1, None))
			
			# ffmpeg by default only outputs progress every .5 seconds so no reason to be faster (or slower for that matter)
			time.sleep(0.5)
		except FileNotFoundError:
			# If the file no longer exists, the process is done!
			progress_callback.emit((0, 1, "end", 1, None))
			return