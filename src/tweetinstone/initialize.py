from __future__ import unicode_literals # Required for yt-dl

# Import standard libraries
import asyncio
import logging
from sys import exit # I only need exit from sys
from PySide6.QtWidgets import QApplication # Used because the GUI setup happens here regardless

# Import tweetinstone-specific functions
from tweetinstone.file_ops import gen_cookie
from tweetinstone.search import parser_setup, read_input, run_playwright
from tweetinstone.gui.main_window import tis_main_window, stylesheet
from tweetinstone.gui.worker import WorkerSignals

### initialize(): AKA a synonym for main() since I needed to make some nested mains
# Gets args, then based off of that does the real shit
async def initialize(forcegui) -> None:
	# Set up argument parser
	parser = parser_setup()
	
	# Parse the arguments
	args = parser.parse_args()
	
	### Logging setup
	# TODO FUTURE: option to log to a file
	# TODO FUTURE: use 'format=' option to change the output format. The default format set by basicConfig() for messages is: severity:logger name:message
	if args.verbose:
		logging.basicConfig(level=logging.DEBUG)
	else:
		logging.basicConfig(level=logging.INFO)
	
	log = logging.getLogger(__name__)
	
	# TODO FUTURE: optimize?
	# Check if GUI is forced regardless of CLI (this I added when creating `tis-gui` option during package creation)
	if forcegui:
		args.gui = True
	
	# CLI vs GUI Mode
	if args.gui:
		log.debug("Launching GUI")
		
		app = QApplication([])
		
		window = tis_main_window()
		window.show()
		
		### Base styles for future testing
		# Not installed!
		#app.setStyle('Breeze')
		#app.setStyle('Oxygen')
		#app.setStyle('QtCurve')
		
		# Installed:
		#app.setStyle('Fusion')
		#app.setStyle('Windows')
		
		# Custom style to give a twitter-esque look
		app.setStyleSheet(stylesheet)
		
		exit(app.exec())
	else: # This else explicitly defines implicit behavior - CLI execution only happens if the GUI is not selected
		if args.generate: # If generating cookies, only do that and exit
			token = input("Paste your auth_token cookie value: ")
			
			filename = args.generate
			
			gen_cookie(token, filename)
			print("Saved cookie file to '" + str(filename) + "'")
		elif not args.input and len(args.urls[0]) == 0:	# Print help message if no url or list provided
			parser.parse_args(['-h'])
		else: # Run the search on the url(s)
			urls = read_input(args)
			
			# Create signals with class even if we aren't using it
			# TODO FUTURE: use it?
			signals = WorkerSignals()
			
			# Run all the playwright stuff based off of the arguments provided
			await run_playwright(args, urls, signals.progress)