### main_window.py ###
# class for main GUI window

## Imports ##
import logging

from PIL import Image
from PySide6.QtWidgets import (QApplication, QDialog, QFileDialog, QLabel, QMainWindow, QMessageBox, QSizePolicy, QGroupBox, QHBoxLayout, QVBoxLayout, QRadioButton, QWidget, QPushButton, QInputDialog, QLineEdit, QProgressBar, QLayout, QSizePolicy, QStyle, QProxyStyle)
from PySide6.QtGui import (QGuiApplication, QKeySequence, QIcon)
from PySide6.QtCore import QDir, QStandardPaths, Qt, Signal, Slot, QThreadPool

# Import TIS-specific functions
from tis.version import __version__
from tis.search import parser_setup
from tis.file_ops import gen_cookie
from tis.text_ops import validURL
from tis.gui.search_window import TweetDialog
from tis.gui.stylesheet import stylesheet

# TODO FUTURE FEATURE: add json viewer like https://doc.qt.io/qtforpython-6/examples/example_widgets_itemviews_jsonmodel.html ?
# TODO FUTURE FEATURE: Checkboxes: STRETCH GOAL. have yes/no if it got correct capture then error message that I can get in issues, then after it's done, it keeps settings and stays open

# Text for 'about' messages in the GUI
ABOUT = """<p><b>TweetInStone</b> is a tool used for capturing images and video representing what tweets were displayed as at a particular date and time. Useful for archivists, data hoarders, and multimedia production use cases where someone wants a screenshot of a tweet and all related data.</p>

<p>TweetInStone was built by Some Guy™ in his spare time and comes at no cost, but also with no obligations of support</p>
"""
ABOUTFOSS = """<p><b>Open-Source Usage & Kudos</b></p>
<p><ul>
<li><b>yt-dlp</b> for downloading twitter videos</li>
<li><b>ffmpeg</b> for performing magic on videos</li>
<li><b>playwright</b> for making it "easy" to automate a browser</li>
<li><b>beautifulsoup</b> for making it "easy" to parse html</li>
</ul></p>
"""

### Main GUI class
# Heavily based off of: https://doc.qt.io/qtforpython-6/examples/example_widgets_imageviewer.html
# as well as https://doc.qt.io/qtforpython-6/examples/example_widgets_tutorials_addressbook.html
class tis_main_window(QMainWindow):
	# For what I'm doing with modes, see https://doc.qt.io/qtforpython-6/examples/example_widgets_tutorials_addressbook.html
	StandbyMode, FileMode, URLMode, SearchMode, DisableMode = range(5)
	# StandbyMode = waiting around
	# File mode   = search ready using file
	# URL mode    = search ready using url mode
	# SearchMode  = processing a search
	# DisableMode = Standby Mode but with buttons greyed out. Used when errors pop up
	
	# Initialize - set up the GUI's initial state
	def __init__(self, parent=None):
		super().__init__(parent)
		
		self.log = logging.getLogger(__name__)
		
		# TODO FUTURE TEST:
		# test this under this https://doc.qt.io/qtforpython-6/PySide6/QtCore/Qt.html#PySide6.QtCore.Qt.WindowType
		#self.setWindowFlags(Qt.CustomizeWindowHint)
		
		# Set default vars
		self.current_mode = self.StandbyMode
		self.search_url  = ""
		self.search_file = ""
		
		# Set up variables for command line argument settings
		self.create_settings()
		
		# TODO FUTURE CRIT: Use QMainWindow for managing it. learn more!
		self.setWindowTitle('TweetInStone')
		
		# Create the main layout
		# Kudos to https://stackoverflow.com/questions/32714656/pyqt-add-a-scrollbar-to-mainwindow for centralWidget idea
		centralWidget = QWidget()
		self.setCentralWidget(centralWidget)
		self.main_layout = QVBoxLayout(centralWidget)
		
		self.title = QLabel("TweetInStone", alignment=Qt.AlignCenter)
		
		# Create input/options boxes
		self.create_input_box()
		self.create_mode_box()
		
		# Add boxes to the main layout
		#self.main_layout.addWidget(self.title)
		# TODO FUTURE: fix this box?
		self.main_layout.addWidget(self._input_box)
		self.main_layout.addWidget(self.mode_box)
		
		# Run button
		self._submit_button = QPushButton("Begin Capture")
		self._submit_button.setEnabled(False)
		self._submit_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
		
		self._submit_button.clicked.connect(self.begin_detect)
		
		# TODO FUTURE: refine this maybe put button here?
		self.search_box = QGroupBox("Search Target", alignment=Qt.AlignBottom |Qt.AlignCenter)
		search_layout = QVBoxLayout()
		self._current_search_label = QLabel("No search target loaded", alignment=Qt.AlignBottom |Qt.AlignCenter)
		search_layout.addWidget(self._current_search_label)
		self.search_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
		self.search_box.setLayout(search_layout)
		
		self.main_layout.addWidget(self.search_box)
		
		self.main_layout.addWidget(self._submit_button, alignment=Qt.AlignCenter)
		
		### Finalize UI Loading
		# Set main layout
		self.setLayout(self.main_layout)
		# TODO FUTURE: FIX
		#self._input_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
		
		# Add all buttons to the menu bar
		self.create_actions()
		
		# TODO FUTURE: figure out sizing
		#self.resize(QGuiApplication.primaryScreen().availableSize() * 3 / 5)
		self.setMinimumWidth(550)
		
		# Update UI
		self.update_maingui(self.StandbyMode)
		
		# TODO FUTURE; figure out how to use openUrl()
		# https://doc.qt.io/qtforpython-6/overviews/desktop-integration.html
	
	### Function for actual tweet search:
	@Slot()
	def begin_detect(self):
		# Set up argument parser and get with values from GUI options
		parser = parser_setup()
		
		guiargs = [
			'--scale', 
			str(self._settings_scale_value),
			'--color',
			str(self._settings_color_value),
			'--locale',
			self._settings_locale_value,
			'--timezone',
			self._settings_timezone_value
		]
		
		if self._settings_cookie:
			guiargs.append('--cookies')
			guiargs.append(self._settings_cookie_filename)
		
		# Copy mode arguments
		if self.singlemode.isChecked():
			self.log.debug("Single search mode loaded via GUI")
			guiargs.append('--only')
		elif self.threadmode.isChecked():
			self.log.debug("Thread search mode loaded via GUI")
			guiargs.append('--thread')
		elif self.replymode.isChecked():
			self.log.debug("Default search mode (replies) loaded via GUI")
		
		# Copy input arguments
		if self.search_file != "":
			guiargs.append('--input')
			guiargs.append(self.search_file)
		else:
			# TODO FUTURE: danger?
			guiargs.append(self.search_url)
		
		# Reset the args global with newly-parsed settings from the GUI
		args = parser.parse_args(guiargs)
		
		# Update UI so the button search can't be run twice
		self.unload_search()
		self.update_maingui(self.DisableMode)
		self.progress = TweetDialog(args) # does copy() help here?
		result = self.progress.exec() # Running with exec() lets us wait for signal/progress that tweets are grabbed
		self.update_maingui(self.StandbyMode)
		
		if result == 0: # Cancel
			self.log.warning("Search cancelled from GUI")
			self.update_maingui(self.DisableMode)
			error_message = QMessageBox(QMessageBox.Critical, "Search Cancelled!", "The search was cancelled before completion and thus not all tweets were saved.\n\nAny saved output may be erroneous or incomplete!", buttons=QMessageBox.StandardButton.Ok, parent=self)
			error_message.exec()
			self.update_maingui(self.StandbyMode)
		elif result == 1: # Finish
			self.log.debug("Search finished and closed")
			# TODO FUTURE: any other additions here?
		
		#self.progress.setWindowModality(Qt.WindowModal)	
		# TODO FUTURE FEATURE: have messagebox pop up asking if output is expected
	
	# TODO FUTURE: review this
	@Slot()
	def end_search(self): # Cancel an active search. unload and reset and clean up
		self.unload_search()

	### UI Creation functions: ###
	# These are each run once in init
	def create_input_box(self):
		self._input_box = QGroupBox("Tweet URL Input", alignment=Qt.AlignBottom |Qt.AlignCenter)
		self.inputlayout = QHBoxLayout()
		
		self.clipboard_button = QPushButton("Clipboard")
		self.clipboard_button.clicked.connect(self.set_url_clipboard)
		
		self.orlabel = QLabel("OR", alignment=Qt.AlignCenter)
		
		self.urlbutton = QPushButton("Type")
		self.urlbutton.clicked.connect(self.set_url)
	
		self.orlabel2 = QLabel("OR", alignment=Qt.AlignCenter)
		
		self.filebutton = QPushButton("File")
		self.filebutton.clicked.connect(self.set_url_file)
		
		# Hidden button to unload search info
		self.resetbutton = QPushButton("Reset search")
		self.resetbutton.clicked.connect(self.unload_search)
		
		# Add all buttons to the box
		self.inputlayout.addWidget(self.clipboard_button)
		self.inputlayout.addWidget(self.orlabel)
		self.inputlayout.addWidget(self.urlbutton)
		self.inputlayout.addWidget(self.orlabel2)
		self.inputlayout.addWidget(self.filebutton)
		self.inputlayout.addWidget(self.resetbutton)
		
		self._input_box.setLayout(self.inputlayout)
		self._input_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
		
		self.update_input_box() # Update which buttons are shown/hidden
	def create_mode_box(self):
		self.mode_box = QGroupBox("Capture Mode", alignment=Qt.AlignBottom |Qt.AlignCenter)
		layout = QVBoxLayout()

		# Scope option buttons (exclusive radio)
		self.singlemode = QRadioButton("Single tweet")
		self.threadmode = QRadioButton("Entire Thread")
		self.replymode = QRadioButton("Tweet + previous tweets")
		
		## TODO RELEASE: remove this
		#self.threadmode.setIcon(QIcon("verified.png"))
		
		layout.addWidget(self.singlemode)
		layout.addWidget(self.threadmode)
		layout.addWidget(self.replymode)

		self.mode_box.setLayout(layout)
		self.mode_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
		
		# Update the GUI with default selection
		self.update_mode_box()
	def create_actions(self): # Created actions for the QMenuBar
		# TODO RELEASE: make view menu with settings to add debug information
		# TODO RELEASE: FOR ALL QKeySequence change to reasonable: https://doc.qt.io/qtforpython-5/PySide2/QtGui/QKeySequence.html
	
		### FILE MENU
		# TODO FUTURE: change file menu to tweetinstone or application menu
		# The file menu is used for importing files and exiting the app
		file_menu = self.menuBar().addMenu("&File")
		file_menu.addSeparator()
		# Close the app
		self._exit_act = file_menu.addAction("E&xit")
		self._exit_act.triggered.connect(self.close)
		self._exit_act.setShortcut("Ctrl+Q")
		
		### COOKIE MENU
		# Import, generate, unload cookies
		cookie_menu = self.menuBar().addMenu("&Cookies")
		# Import cookies from file
		self._import_act = cookie_menu.addAction("&Import Cookies...")
		self._import_act.triggered.connect(self.set_cookie_file)
		# TODO FUTURE:
		#self._import_act.setShortcut(QKeySequence.Open)
		cookie_menu.addSeparator()
		self.unload_cookie_act = cookie_menu.addAction("&Unload Cookies...")
		self.unload_cookie_act.triggered.connect(self.unload_cookie_file)
		self.unload_cookie_act.setEnabled(False) #Disable unloading cookies by default
		# TODO FUTURE
		#self.unload_cookie_act.setShortcut(QKeySequence.Open)
		# Create cookie file from authorization
		self._generate_act = cookie_menu.addAction("&Generate Cookies...")
		self._generate_act.triggered.connect(self.generate_cookie)
		cookie_menu.addSeparator()

		### EDIT MENU
		# This menu is all about changing settings of the final output
		edit_menu = self.menuBar().addMenu("&Edit")
		self._edit_color_act = edit_menu.addAction("Browser &Color")
		self._edit_color_act.triggered.connect(self.set_color)
		edit_menu.addSeparator()
		self._edit_scale_act = edit_menu.addAction("Browser DPI &Scale")
		self._edit_scale_act.triggered.connect(self.set_scale)
		edit_menu.addSeparator()
		self._edit_localization_act = edit_menu.addAction("Browser &Localization")
		self._edit_localization_act.triggered.connect(self.set_locale) 
		edit_menu.addSeparator()
		self._edit_time_act = edit_menu.addAction("Browser &Time Zone")
		self._edit_time_act.triggered.connect(self.set_timezone)

		### HELP MENU
		# Print out help info
		help_menu = self.menuBar().addMenu("&Help")
		about_act = help_menu.addAction("&About TweetInStone")
		about_act.triggered.connect(self._about)
		help_menu.addSeparator()
		about_foss_act = help_menu.addAction("About &Open-Source Software Used")
		about_foss_act.triggered.connect(self._about_foss)
		help_menu.addSeparator()
		# TODO FUTURE: move this to the above section?
		about_qt_act = help_menu.addAction("About &Qt")
		about_qt_act.triggered.connect(QApplication.aboutQt)
	def create_settings(self): # Sets default settings
		self._settings_scale = False
		self._settings_scale_value = 4
		
		self._settings_color = False
		self._settings_color_value = "dark"
		
		self._settings_locale = True
		self._settings_locale_value = "en-US"
		
		self._settings_timezone = True
		self._settings_timezone_value = "America/New_York"
		
		self._settings_cookie = False
		self._settings_cookie_filename = ""
		
		# TODO FUTURE: verbose setting as a gui option?
		#self._settings_verbosity = False
		#self._settings_verbosity_value = 
	
	### UI Update functions: ###
	# These are run occasionally based on user input to reflect what options are available or enabled
	def update_maingui(self, mode): # Update the UI, particularly button availability
		self.current_mode = mode
		
		# Don't let the submit button be pressable if there isn't a file or url specified
		if self.current_mode in (self.FileMode, self.URLMode):
			self._submit_button.setEnabled(True)
		else:
			self._submit_button.setEnabled(False)
		
		# Update the menu bar
		if self._settings_cookie == True:
			self.unload_cookie_act.setEnabled(True)
		else:
			self.unload_cookie_act.setEnabled(False)
		
		# Update the other option boxes in the main gui
		self.update_input_box()
		self.update_mode_box()
		self.update_search_box()
		#self.adjustSize()
	def update_input_box(self):
		# TODO FUTURE: change to case:?
		if self.current_mode == self.SearchMode:
			# if we're searching, don't let the reset button be pressable
			self.resetbutton.show()
			self.resetbutton.setEnabled(False)
			
			# TODO: make the other buttons done
		elif self.current_mode in (self.URLMode, self.FileMode):
			# If search data is loaded, add a button to unload the data
			self.clipboard_button.hide()
			self.orlabel2.hide()
			self.urlbutton.hide()
			self.orlabel.hide()
			self.filebutton.hide()
			
			self.resetbutton.show()
			self.resetbutton.setEnabled(True)
		elif self.current_mode == self.StandbyMode:
			self.clipboard_button.show()
			self.orlabel2.show()
			self.urlbutton.show()
			self.orlabel.show()
			self.filebutton.show()
			
			self.resetbutton.hide()
			
			self.clipboard_button.setEnabled(True)
			self.urlbutton.setEnabled(True)
			self.filebutton.setEnabled(True)
		else:
			# DisableMode
			self.clipboard_button.show()
			self.orlabel2.show()
			self.urlbutton.show()
			self.orlabel.show()
			self.filebutton.show()
			
			self.resetbutton.hide()
			
			self.clipboard_button.setEnabled(False)
			self.urlbutton.setEnabled(False)
			self.filebutton.setEnabled(False)
	def update_mode_box(self): # Updates the mode availability based on if cookies are loaded or not
		if self.current_mode == self.SearchMode:
			# If w're in the middle of a search, disable all the buttons
			self.singlemode.setEnabled(False)
			self.threadmode.setEnabled(False)
			self.replymode.setEnabled(False)
		else:
			if self._settings_cookie == True:
				# Enable all search modes
				self.singlemode.setEnabled(True)
				self.threadmode.setEnabled(True)
				self.replymode.setEnabled(True)
				
				# Default to capture replies
				self.replymode.toggle()
			else:
				self.singlemode.setEnabled(True)
				# Disable other capture modes because they won't work without cookies
				self.threadmode.setEnabled(False)
				self.replymode.setEnabled(False)
				
				# Default to capture only one tweet
				self.singlemode.toggle()
	def update_search_box(self):
		if self.current_mode == self.SearchMode:
			# TODO RELEASE: make this update the label?
			self.search_box.show()
		elif self.current_mode in (self.URLMode, self.FileMode):
			self.search_box.show()
		else:
			self.search_box.hide()
	
	### 'About' menus:
	def _about(self):
		QMessageBox.about(self, "About TweetInStone", ABOUT)
	def _about_foss(self):
		QMessageBox.about(self, "FOSS Software Used In TweetInStone", ABOUTFOSS)
	
	### View customization option functions:
	# Reference: https://doc.qt.io/qtforpython-6.4/PySide6/QtWidgets/QInputDialog.html
	def set_color(self):
		items = ("dark", "light")
	
		item, ok = QInputDialog.getItem(self,"Browser Dark Mode", "Why would you change it?", items, 0, False)
		if ok and item:
			self._settings_color = True
			self._settings_color_value = item
	def set_scale(self):
		i, ok = QInputDialog.getInt(self, "Browser DPI Scale", "Browser DPI Scale", 4, 1, 4, 1)
		if ok:
			self._settings_scale = True
			self._settings_scale_value = i		
	def set_locale(self):
		text, ok = QInputDialog.getText(self, "Browser Locale", "Browser Locale", QLineEdit.Normal, "en-US")
		if ok:
			self._settings_locale = True
			self._settings_locale_value = text
	def set_timezone(self):
		text, ok = QInputDialog.getText(self, "Browser Time Zone", "Browser Time Zone", QLineEdit.Normal, "America/New_York")
		if ok:
			self._settings_timezone = True
			self._settings_timezone_value = text
	
	### Search target functions:
	def set_url(self):
		text, ok = QInputDialog.getText(self, "Tweet URL", "Tweet URL", QLineEdit.Normal, "")
		if ok and text != '':
		
			if validURL(text):
				self.search_url = text
				self._current_search_label.setText("URL: '" + text + "'")
				
				self.update_maingui(self.URLMode)
			else:
				self.update_maingui(self.DisableMode)
				error_message = QMessageBox(QMessageBox.Critical, "Invalid URL", "The entered URL ['" + text + "'] isn't valid", buttons=QMessageBox.StandardButton.Ok)
				error_message.exec()
				self.update_maingui(self.StandbyMode)
	def set_url_clipboard(self): # Why have the user paste when we can do it for them?
		clipboard = QGuiApplication.clipboard()
		text = clipboard.text()
		
		if validURL(text):
			self.search_url = text
			self._current_search_label.setText("URL: '" + text + "'")
			
			self.update_maingui(self.URLMode)
		else:
			# TODO FUTURE: change to something that replaces the input box instead of an unreliable modal (??? what did i mean by this?)
			self.update_maingui(self.DisableMode)
			error_message = QMessageBox(QMessageBox.Critical, "Invalid URL", "The URL ['" + text + "'] from clipboard isn't valid", buttons=QMessageBox.StandardButton.Ok)
			error_message.exec()
			self.update_maingui(self.StandbyMode)
	def set_url_file(self): # Dialog to select file to load urls from
		filename = QFileDialog.getOpenFileName(self, "Select file of tweet links", "", "All Files (*);;Text Files (*.txt)", "Text Files (*.txt)")
		
		if filename[0] != '':
			self._current_search_label.setText("File: '" + filename[0] + "'")
			self.search_file = filename[0]
			self.update_maingui(self.FileMode)
	def unload_search(self): # Returns state to when a search wasn't loaded
		self.search_url = ""
		self.search_file = ""
		
		self._current_search_label.setText("No search target loaded")
		
		self.update_maingui(self.StandbyMode)

	### Cookie-related functions:
	def set_cookie_file(self): # Dialog to select cookie file
		file = QFileDialog.getOpenFileName(self, "Select cookie file", "", "All Files (*);;Text Files (*.txt)", "Text Files (*.txt)")
		if file[0] != '':
			self._settings_cookie = True
			self._settings_cookie_filename = file[0]
			
			# TODO FUTURE FEATURE: detect if the cookie file is correctly formatted
			
			self.update_maingui(self.current_mode)
	def unload_cookie_file(self): # Unloads the cookie file
		self._settings_cookie = False
		self._settings_cookie_filename = ""
		self.update_maingui(self.current_mode)
	def generate_cookie(self): # Saves cookie to file after prompting user
		# TODO FUTURE OPTIMIZATION: QLineEdit.Normal - are there other modes here that give more space?
		cookie_gen_tkn, ok = QInputDialog.getText(self, "Save Cookie", "Paste your auth_token cookie value:", QLineEdit.Normal, "")
		if ok and cookie_gen_tkn != '':
			file, ok = QInputDialog.getText(self, "Name Cookie File", "Enter file name to save to:", QLineEdit.Normal, "")
			if ok and file != '':
				gen_cookie(cookie_gen_tkn, file)
	
	### DOCUMENTATION/EXAMPLES:
	# Reference on how to learn what I did here came from a lot of these examples
	# https://doc.qt.io/qtforpython-5/overviews/application-windows.html
	# https://doc.qt.io/qtforpython-6/overviews/examples-dialogs.html
	# https://doc.qt.io/qtforpython-6/examples/example_widgets_dialogs_standarddialogs.html
	# https://doc.qt.io/qtforpython-6/examples/example_widgets_layouts_basiclayouts.html
	# https://doc.qt.io/qtforpython-6/examples/example_widgets_itemviews_jsonmodel.html
	# https://doc.qt.io/qtforpython-5/overviews/dialogs.html#dialog-windows
	# https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QInputDialog.html#qinputdialog
	# https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QMessageBox.html#PySide6.QtWidgets.PySide6.QtWidgets.QMessageBox
	# https://doc.qt.io/qtforpython-6/examples/example_widgets_tutorials_addressbook.html
	# https://doc.qt.io/qtforpython-6/tutorials/qmlsqlintegration/qmlsqlintegration.html # Check this example?
	# https://doc.qt.io/qtforpython-6/examples/example_widgets_imageviewer.html # really useful
	# https://doc.qt.io/qtforpython-6/examples/example_widgets_desktop_screenshot.html
	# https://doc.qt.io/qtforpython-6/overviews/qtwidgets-widgets-groupbox-example.html#group-box-example # Nice button type reference
	# tweetdialog used a lot from https://doc.qt.io/qtforpython-6/examples/example_widgets_tutorials_addressbook.html part7