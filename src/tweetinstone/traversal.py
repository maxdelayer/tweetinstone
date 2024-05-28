### Traversal.py ###
# Functions for traversing tweets in a page using Playwright

import logging
from copy import copy # Used for managing the json of arguments in a sane way
from playwright.async_api import Page, Locator, expect, TimeoutError as PlaywrightTimeoutError

## Import TIS-specific functions
from tweetinstone.capture import capture, killshot
from tweetinstone.text_ops import validURL
from tweetinstone.media_ops import concatenate

# TODO RELEASE CRIT: when at end of the original list, instead of cutting off, stay on that tweet, and restart loop with the new list of tweets, ignoring already captured
### detect(): decide what parts of the page to capture()
# Decide what parts of the page to capture from a URL based on command line arguments
# The logic for iterating through threads, grabbing QRTs, replies, etc. exists here
# Returns the number of tweets that were checked
async def detect(search: dict, page: Page, progress_callback):
	log = logging.getLogger(__name__)

	# Used for tracking what tweet is currently being processed
	search['current_tweet_iterator'] = 0
	
	if not validURL(search['target']):
		search['num_tweets'] = 0
		return search
	
	print("Search #" + str(search['current_search_num']) + " of " + str(search['num_searches']) + ": '" + search['target'] + "'")
	
	# TODO Optimization: clean up this given fullwait() does most of it later
	# Catch potential page loading error
	retrylimit = 3
	for retries in range(retrylimit):
		try:
			await page.goto(search['target'], wait_until="load");
			
			# No need to retry loading if there was no problem
			break
		except PlaywrightTimeoutError:
			if retries == (retrylimit - 1):
				log.error("Timeout on initial page loading")
				await killshot(search, page)

				# TODO RELEASE: make this give gui callbacks
				
				#raise
				search['num_tweets'] = 0
				return search
			else:
				log.warning("timeout on initial page loading. Trying again...")
	
	### Wait for the element that shows that the page is truly loaded
	loaded = await fullwait(search, page, progress_callback)
	
	# If this fails after retries, then return that the tweet wasn't captured
	if not loaded:
		search['num_tweets'] = 0
		return search
	
	# TODO RELEASE: have timeouterror for any searches in the page
	try:
		# First, grab all tweets on the current page:
		# TODO RELEASE: getting by test id 'cellInnerDiv' will grab "this tweet has been deleted" so make handling for that
		# Or use it for role = article
		# This Post was deleted by the Post author. 
		# https://help.twitter.com/rules-and-policies/notices-on-twitter
		# GRAB THE "Learn more" within an <a>
		
		#tweets = await page.get_by_test_id("tweet").all()
		tweets = await page.get_by_role("article").all()
		originaltweets = copy(tweets)
		
		# Exit early if no tweets
		if len(tweets) == 0:
			log.warning("No tweets found - the tweet '" + search['target'] + "' may be private/age-restricted/deleted")
			search['num_tweets'] = 0
			return search
	
		# TODO RELEASE FINISH
		#print("visible tweets")
		#iterator = 0
		#for tweet in tweets:
			# Grab the link to the current tweet from the tweet itself
			#tweetUrl = await tweet.get_by_role("link").last.get_attribute('href')
			
			# Make sure the tweet is real
			#if tweetUrl is not None:
				#iterator += 1
				#print("#" + str(iterator) + ': "' + tweetUrl +'"')
				
				# Assign the user handle and tweet ID to variables for readability
				#handle  = tweetUrl.split("/")[1]
				#tweetid = tweetUrl.split('/')[3]		
	except PlaywrightTimeoutError:
		log.error("Timeout occured when finding elements of tweet '" + search['target'] + "'")
		search['num_tweets'] = 0
		return search
	
	search['current_tweet_iterator'] = 0
	previous_tweet_valid = True
	for tweet in originaltweets:
		try: 
			# Grab the link to the current tweet from the tweet itself
			tweetUrl = await tweet.get_by_role("link").last.get_attribute('href')
		except PlaywrightTimeoutError:
			log.error("Timeout occured when finding elements of tweet '" + search['target'] + "'")
			search['num_tweets'] = 0
			return search
		
		# Make sure the tweet is real
		if tweetUrl is not None:
			search['current_tweet_iterator'] += 1
			 
			# Make sure this isn't just a placeholder for banned/suspended tweet
			if tweetUrl == "https://help.twitter.com/rules-and-policies/notices-on-twitter":
				tweetreason = await tweet.inner_text()
				
				# Use special function to capture the not-tweet for threads
				# TODO REVIEW: is this using the right url?
				captured = await deleted_capture(search, tweet, search['target'], tweetreason)
				search['image'] = concatenate(search['image'], captured['screenshot'])
				# This will update the preview image to the latest thread concatenation
				progress_callback.emit((0, 0, "", 0, search['image']))
				previous_tweet_valid = False
				continue
		
			log.debug("Checking tweet #" + str(search['current_tweet_iterator']) + ': "' + tweetUrl +'"')
		
			# Assign the user handle and tweet ID to variables for readability
			handle  = tweetUrl.split("/")[1]
			tweetid = tweetUrl.split('/')[3]
			
			# 'page.url' is the url that the page is currently on
			# whereas 'search['target'].' is the original search url
			if tweetid == search['target'].split('/')[5].split("?")[0]:
				# The tweet being observed is the tweet originally specified
				
				# Capture the tweet
				captured = await capture(search, tweet, handle, tweetid, progress_callback)
				if not captured['successful']:
					search['num_tweets'] = 0
					return search
				
				search['image'] = concatenate(search['image'], captured['screenshot'])
				# This will update the preview image to the latest thread concatenation
				progress_callback.emit((0, 0, "", 0, search['image']))
				search['json']['tweets'].append(captured['json'])
				
				if search['args'].thread != True:
					# Since we're not grabbing the thread, break from loop as soon as we've found it
					if search['args'].only == True:
						log.debug("Ending detection (SINGLE mode) and returning [1] tweets")
					else:
						log.debug("Ending detection (DEFAULT mode) and returning [" + str(search['current_tweet_iterator']) + "] tweets")
					search['num_tweets'] = search['current_tweet_iterator']
					return search
			elif search['args'].thread == True:
				# We're grabbing the whole thread
				
				if handle == search['target'].split('/')[3]:
					# The current tweet is from the original tweet author, so grab it
					### TODO RELEASE THIS IS THE PROBLEMATIC PART
					# TODO RELEASE TEST
					oldid = deepcopy(tweetid)
					# Click on the next tweet, being careful to not accidentally click on an image
					await tweet.click(position={'x': 1,'y': 1})
					try:
						await page.wait_for_url('https://twitter.com/' + handle + '/status/' + tweetid, wait_until="load")
					except PlaywrightTimeoutError:
						log.error("Timeout occured when finding elements of tweet '" + search['target'] + "'")
						search['num_tweets'] = 0
						return search
					
					loaded = await fullwait(search, page, progress_callback)
					if not loaded:
						search['num_tweets'] = 0
						return search
					# Paranoia
					await page.wait_for_load_state()
					await page.wait_for_load_state('domcontentloaded')
					#await page.wait_for_load_state('networkidle')
					await page.reload()
					
					loaded = await fullwait(search, page, progress_callback)
					if not loaded:
						search['num_tweets'] = 0
						return search
					#currenttweets = await page.get_by_test_id("tweet").all()
					# Make sure this tweet is actually in the thread - sometimes the tweet's position can change on the page
					# Edge case is one thread that also has another reply to the original tweet from the original author
					#for extweet in currenttweets:
						# Grab the link to the current tweet from the tweet itself
					#	extweetUrl = await extweet.get_by_role("link").last.get_attribute('href')

						# Make sure the tweet is real
					#	if extweetUrl is not None:
					#		print('#: "' + extweetUrl +'"')
					
					#for currenttweet in currenttweets:
						# Grab the link to the current tweet from the tweet itself
					#	currentTweetUrl = await currenttweet.get_by_role("link").last.get_attribute('href')
						
						# Make sure the tweet is real
					#	if currentTweetUrl is not None:
					#		print(oldid + " != " + tweetid + " ?= " + currentTweetUrl)
					#		print("page = " + page.url)
					#		if tweetid == currentTweetUrl.split('/')[3]:
					#			await killshot(page)
					#			print("sending  '" + currentTweetUrl + "' to capture")
					#			captured = await capture(currenttweet, handle, tweetid)
					#			thread = await concatenate(thread, captured['screenshot'])
					#			threadjson['tweets'].append(captured['json'])
					#			break
					
					for currenttweet in tweets:
						currentTweetUrl = await currenttweet.get_by_role("link").last.get_attribute('href')
						currentTweetlinks = await currenttweet.get_by_role("link").all()
						for link in currentTweetlinks:
							href = await link.get_attribute('href')
							#print("link: " + href)
							#await killshot(currenttweet)
						if currentTweetUrl is not None:
							#print("TEST " + currentTweetUrl)
							#print("tweetid = " + tweetid)
							#await killshot(page)
							#await killshot(currenttweet)
							if currentTweetUrl.split('/')[3] == tweetid:
								captured = await capture(search, currenttweet, handle, tweetid, progress_callback)
								if not captured['successful']:
									search['num_tweets'] = 0
									return search
								
								search['image'] = concatenate(search['image'], captured['screenshot'])
								# This will update the preview image to the latest thread concatenation
								progress_callback.emit((0, 0, "", 0, search['image']))
								
								search['json']['tweets'].append(captured['json'])
								break
					#await killshot(page)
					
					# Return to previous page (the original tweet)
					await page.go_back()
					loaded = await fullwait(search, page, progress_callback)
					if not loaded:
						search['num_tweets'] = 0
						return search
					# Paranoia
					await page.wait_for_load_state()
					await page.wait_for_load_state('domcontentloaded')
					
					await page.reload()
					
					loaded = await fullwait(search, page, progress_callback)
					if not loaded:
						search['num_tweets'] = 0
						return search
					#await page.wait_for_load_state('networkidle')
				else:
					# Tweet isn't from the original author. This means we reached the end of the thread - time to die
					log.debug("Ending detection (THREAD mode) and returning [" + str(search['current_tweet_iterator']) + "] tweets")
					
					# Decrement iterator to give accurate tweet count since the last one wasn't captured
					search['current_tweet_iterator']-=1
					
					search['num_tweets'] = search['current_tweet_iterator']
					return search
			elif search['args'].only == False: 
				# We're not grabbing a whole thread
				# And, we're not grabbing the single tweet
				# So: grab everything until you reach the original tweet
				
				# TODO: Remove possibly?
				# TODO EDGE CASE: if we've grabbed this one before, don't bother
				#log.debug("checking previous tweets")
				#for done_tweet in threadjson['tweets']:
				#	log.debug(" # " + done_tweet['url'])
				#	if done_tweet == :
				#		continue
				
				# Tweet is occuring after a deleted/inaccessable tweet
				# AND
				# Tweet isn't from the original author
				if not previous_tweet_valid and handle != search['target'].split('/')[3]:
					log.debug("Next tweet occurs after an invalid tweet. Time to die")
					search['current_tweet_iterator']-=1
					
					# If we only got one tweet, we'll save that to file
					if search['current_tweet_iterator'] == 1:
						image = BytesIO()
						search['image'].save(image, format='PNG')
						
						# Get filename based off of the base url
						handle =  search['target'].split('/')[3]
						id = search['target'].split('/')[5].split('?')[0]
						name = handle + "_" + id
						
						saveZip(search['zip'], "capture_" + name + ".png", image.getvalue())
								
						# TODO RELEASE: do the json here too???
						#saveZip(search['zip'], filename + ".json", json.dumps(threadjson, indent=2))
					search['num_tweets'] = search['current_tweet_iterator']
					return search
				
				log.debug("Grabbing tweet because its before the one being searched for")
				
				# Click on the next tweet, being careful to not accidentally click on an image
				await tweet.click(position={'x': 1,'y': 1})
				try:
					await page.wait_for_url('https://twitter.com/' + handle + '/status/' + tweetid, wait_until="load")
				except PlaywrightTimeoutError:
					log.error("Timeout occured when finding elements of tweet '" + search['target'] + "'")
					search['num_tweets'] = 0
					return search
					
				loaded = await fullwait(search, page, progress_callback)
				if not loaded:
					search['num_tweets'] = 0
					return search
				
				captured = await capture(search, tweet, handle, tweetid, progress_callback)
				if not captured['successful']:
					search['num_tweets'] = 0
					return search
				
				search['image'] = concatenate(search['image'], captured['screenshot'])
				
				# This will update the preview image to the latest thread concatenation
				progress_callback.emit((0, 0, "", 0, search['image']))
				
				search['json']['tweets'].append(captured['json'])
				
				# Return to previous page (the original tweet) so search remains consistent
				await page.go_back()
				loaded = await fullwait(search, page, progress_callback)
				if not loaded:
					search['num_tweets'] = 0
					return search

### fullwait(): waits for the page to fully load and present tweets
# Used in detect()
async def fullwait(search, page: Page, progress_callback):
	log = logging.getLogger(__name__)
	# Catch potential page loading error
	# Waits until we can see the elements we need that prove that the page didn't just load, but loaded correctly
	progress_callback.emit((0, 0, "", 2, None))
	
	retrylimit = 3
	for retries in range(retrylimit):
		# Attempt to fully load the tweets multiple times
		try:
			timeline = page.get_by_label("Home timeline").last
			await timeline.wait_for()
		except PlaywrightTimeoutError:
			# TODO RELEASE GET THIS RIGHT TIMEOUTERROR
			if retries == (retrylimit - 1):
				log.error("Page failed to load timeline.")
				return False
			else:
				log.warning("WARNING: Page failed to load timeline. Reloading..")
				await page.reload()
				continue
		# Check if there is a tweet *or* an error waiting for us
		tweetloaded = page.get_by_test_id("reply").last
		tweeterror = page.get_by_test_id("error-detail").last
		
		# Expect either having tweets or message saying no tweets, raise exception if not
		try:
			await expect(tweetloaded.or_(tweeterror), "Page failed to load necessary elements. Possibly a race condition/network issue").to_be_visible(timeout=15000)
			
			# No need to retry loading if there was no problem
			break
		except AssertionError as exception:
			if retries == (retrylimit - 1):
				log.error("Page failed to load necessary elements. Possibly a race condition/network issue")
				await killshot(search, page)
				# Naturally with a lot of these, the extra time to take the screenshot won't be representative of what was at the exact time of error
				
				# Instead of raising the exception, return that it failed so we can move on to the next search
				#raise
				return False
			else:
				log.warning("WARNING: Page failed to load necessary elements. Trying again...")
				
				# Click the retry button instead of loading the page. More reliable but doesn't always work
				buttons = await timeline.get_by_role("button").all()
				for button in buttons:
					buttontext = await button.text_content()
					
					if buttontext == "Retry":
						await button.click()
						log.debug("Pushed 'retry' button")
						break
	
	progress_callback.emit((0, 0, "", 3, None))
	# Return successful loading
	return True

##### END PLAYWRIGHT FUNCTIONS

##### BEGIN TRAVERSAL FUNCTIONS

# TODO FUTURE: make function 'traverse' with up and down to simplify and make easier to understand and more reliable
async def traverse(page: Page, direction: str, id: str):
	log = logging.getLogger(__name__)
	# Basics:
	# based on current url

	if direction == "up":
		print("traversing UP")
	elif direction == "down":
		print("traversing DOWN")

##### END TRAVERSAL FUNCTIONS