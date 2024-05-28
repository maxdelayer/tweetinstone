### text_ops ###
# Helper functions for text operations

### validURL(): Double checking that a string is a valid twitter url
def validURL(url: str) -> None:
	# I do the double check for the sake of preventing unexpected behavior if you point this at other websites
	# If you want to tinker with this and see how it breaks on other sides then by all means just have this always return True and proceed to fuck around and find out
	
	split = url.split("/")
	
	if len(split) >= 2:
		domain = split[2]

		if domain == "twitter.com" or domain == "www.twitter.com":
			return True
		# TODO FUTURE: review and test this
		elif domain == "x.com" or domain == "www.x.com":
			url = xToTwitter(url)
			return True
		else:
			# TODO POLISH: use proper logging library to print this instead of print
			print("WARNING: cancelled capture of '" + url + "' because it's not a valid twitter URL")
			return False
	else:
		# If there aren't even enough /'s to include the 'https://domain.name' then it's invalid
		print("WARNING: cancelled capture of '" + url + "' because it's not a valid URL")
		return False
		
### commentFilter(): make sure strings with comments are ignored
# So nice that I use it twice (for cookie file interpreter and link file interpreter)
def commentFilter(string: str) -> str:
	# Only consider parts before the '#' for comments in cookie files and input files
	string = string.split('#')[0]

	if string.isspace():
		string = ""
	if string == "":
		return string
		
	# remove leading whitespace
	string = string.lstrip(" ")
	
	### Spooky looking edge case divined from 'python3.8/http/cookiejar.py'
	# last field may be absent, so keep any trailing tab
	if string.endswith("\n"): 
		string = string[:-1]
	### End stuff from 'python3.8/http/cookiejar.py'
	else:
		# Remove trailing spaces from the pre-comment string, which can fuck with urls
		string = string.rstrip(" ")
	
	return string

### xToTwitter(): change 'x.com' urls to 'twitter.com'
def xToTwitter(url: str):
	split = url.split("/")
	split[2] = "twitter.com"
	string = '/'.join(split)
	
	return string