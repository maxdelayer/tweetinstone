## Imports ##
import logging

# TODO FUTURE: review this for ones not used
from PySide6.QtWidgets import (QApplication, QDialog, QLabel, QMessageBox, QSizePolicy, QGroupBox, QHBoxLayout, QVBoxLayout, QPushButton, QProgressBar, QLayout, QErrorMessage)
from PySide6.QtGui import (QPixmap, QImage, QIcon, QDrag)
from PySide6.QtCore import Qt, Signal, Slot, QThreadPool, QMimeData
from PIL import Image

## Import TIS-specific functions
from tweetinstone.search import read_input, run_playwright
from tweetinstone.file_ops import check_progress_file
from tweetinstone.gui.worker import Worker, WorkerSignals

### Custom dialog for the search
# This runs the worker that does the same async function the CLI version uses
# TODO FUTURE: add a different progress bar that shows busy and is red whenever it's recovering from an error like page load
# TODO FEATURE: add a part that shows the full log when verbose is enabled
class TweetDialog(QDialog):
	def __init__(self, args, parent=None):
		super().__init__(parent)
		
		self.log = logging.getLogger(__name__)
		
		# TODO FUTURE TEST: This doesn't change stuff on win11 WSL, but maybe on linux?
		self.setWindowFlags(Qt.WindowCloseButtonHint | Qt.WindowTitleHint)
		self.setWindowTitle("Search")
		
		# Create the boxes and buttons for the window
		self.create_layout()
	
		# Set up threadpool for the workers that run searches
		self.threadpool = QThreadPool()

		### Run the job
		# Get urls from file or single url, and get number of them
		urls = read_input(args)
		self.search_bar.setMaximum(len(urls))
		
		self.show()
		
		self.worker = Worker(run_playwright, args, urls)
		
		# Connect worker signals to functions to manage the GUI
		# When the worker thread emits signals, these functions update the gui!
		self.worker.signals.progress.connect(self.update_progress)
		self.worker.signals.result.connect(self.search_finished)
		#self.worker.signals.finished.connect(self.search_finished)
		
		# Start the worker thread
		self.threadpool.start(self.worker)

	# Function to initialize the various layout elements
	def create_layout(self):
		# Each piece of data looks nicer grouped into boxes
		self.search_box = QGroupBox("Current Search", alignment=Qt.AlignCenter)
		search_layout = QHBoxLayout()
		self.search_bar = QProgressBar()
		self.search_bar.setMinimum(1)
		self.search_bar.setValue(1)
		self.search_bar.setFormat("#1 of ?")
		search_layout.addWidget(self.search_bar)
		
		search_layout.setSizeConstraint(QLayout.SetMinimumSize)
		self.search_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
		self.search_box.setLayout(search_layout)
		
		self.tweet_box = QGroupBox("Current Tweet", alignment=Qt.AlignCenter)
		tweet_layout = QVBoxLayout()
		self.tweet_label     = QLabel("", alignment=Qt.AlignCenter)
		self.tweet_url_label = QLabel("", alignment=Qt.AlignCenter)
		tweet_layout.addWidget(self.tweet_label)
		tweet_layout.addWidget(self.tweet_url_label)
		self.tweet_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
		self.tweet_box.setLayout(tweet_layout)
		
		# The 'Capture Stage' box has a progress 
		self.stage_box = QGroupBox("Tweet Capture Stage", alignment=Qt.AlignCenter)
		stage_layout = QHBoxLayout()
		
		self.stage_bar = QProgressBar(alignment=Qt.AlignCenter)
		self.stage_bar.setMinimum(1)
		self.stage_bar.setMaximum(5)
		self.stage_bar.setValue(1)
		
		stage_layout.addWidget(self.stage_bar)
		self.stage_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
		self.stage_box.setLayout(stage_layout)
		
		# The button lives outside of the preview box
		self.preview_button = QPushButton("Hide Preview")
		self.preview_button.clicked.connect(self.toggle_preview)
		
		# Preview box is useful for copying to clipboard
		self.preview_box = QGroupBox("Preview", alignment=Qt.AlignCenter)
		preview_layout = QVBoxLayout()
		self.preview_info = QLabel("Preview image is of search #1", alignment=Qt.AlignCenter)
		self.preview_info.hide() # Hide this until we have an image
		self.preview_copy_button = QPushButton("Copy to clipboard")
		self.preview_copy_button.clicked.connect(self.copy_preview)
		self.preview_copy_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
		self.preview_image = QLabel("", alignment=Qt.AlignCenter)
		preview_layout.addWidget(self.preview_info)
		preview_layout.addWidget(self.preview_copy_button, alignment=Qt.AlignCenter)
		preview_layout.addWidget(self.preview_image, alignment=Qt.AlignCenter)
		self.preview_box.setLayout(preview_layout)
		
		self.button_box = QGroupBox("Options", alignment=Qt.AlignCenter)
		self.button_layout = QHBoxLayout()
		self.cancel_button = QPushButton("Cancel")
		self.cancel_button.clicked.connect(self.cancel)
		self.finish_button = QPushButton("Finish")
		self.finish_button.clicked.connect(self.accept)
		self.finish_button.hide()
		self.button_layout.addWidget(self.cancel_button, alignment=Qt.AlignCenter)
		self.button_layout.addWidget(self.finish_button, alignment=Qt.AlignCenter)
		self.button_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
		self.button_box.setLayout(self.button_layout)

		layout = QVBoxLayout()
		layout.addWidget(self.search_box)
		layout.addWidget(self.tweet_box)
		layout.addWidget(self.stage_box)
		layout.addWidget(self.preview_button, alignment=Qt.AlignCenter)
		layout.addWidget(self.preview_box)
		layout.addWidget(self.button_box)
		
		self.setLayout(layout)
		self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
		self.setMinimumWidth(450)

	@Slot()
	# Cancel the worker process and then return rejection to signify to main window that it was cancelled
	def cancel(self):
		self.worker.exit() # Tell the worker to kill itself
		self.reject() # Send negative signal back to main window

	@Slot()
	def copy_preview(self):	
		# TODO RELEASE: test this on a thing where no progress was ever made
		if hasattr(self, 'clipboard_copy'):
			bytes = self.clipboard_copy.tobytes("raw","RGBA")
			
			# I never expected this to work in a million fucking years. holy shit.
			clipboard = QApplication.clipboard()
			clipboard.setImage(QImage(bytes, self.clipboard_copy.size[0], self.clipboard_copy.size[1], QImage.Format_RGBA8888))

	# Show/hide the image preview box
	def toggle_preview(self):
		if self.preview_box.isHidden():
			self.preview_box.show()
			self.preview_button.setText("Hide Preview")
		else:
			self.preview_box.hide()
			self.preview_button.setText("Show Preview")
		
		# Let the window adjust it's size based on the box being hidden
		self.adjustSize()
	
	def disable_buttons(self):
		self.preview_button.setEnabled(False)
		self.preview_copy_button.setEnabled(False)
		self.finish_button.setEnabled(False)
	def enable_buttons(self):
		self.preview_button.setEnabled(True)
		self.preview_copy_button.setEnabled(True)
		self.finish_button.setEnabled(True)
	
	# TODO FUTURE FEATURE: have search bar show which searches have failed!
	# TODO FUTURE: add this type of functionality to the CLI version's output for videos
	# Update the UI as the worker process sends back progress
	def update_progress(self, progress_data):
		# Assign data from the tuple into named variables for readability
		search = progress_data[0]
		tweet  = progress_data[1]
		url    = progress_data[2] # URL string also stores the progressfile name for ffmpeg progress output
		stage  = progress_data[3]
		image  = progress_data[4]
		
		#msg    = progress_data[5] # For errors?
		# TODO FUTURE: if statement if there is error. if error, don't do the following since the data is info about the error
		
		# Only update each field if there is new, non-default data
		if search != 0:
			self.search_bar.setValue(search)
			self.search_bar.setFormat("#" + str(search) + " of " + str(self.search_bar.maximum()))
			self.last_search = search
		if tweet != 0:
			self.tweet_label.setText("#" + str(tweet) + " in Search")
		if url != "" and stage != 5:
			self.tweet_url_label.setText("URL: 'https://twitter.com/" + url + "'")
		if stage != 0: # TODO Future: for python >= 3.10 change this to a case statement
			# Change text of progress bar based on what stage it's at
			# Stages 2 and 4 are doubled up because they can go back and forth
			# Wouldn't want to have my fake progress bar go backwards
			if stage == 1:
				stage_text = "Initialization"
			elif stage == 2:
				stage_text = "Loading Page"
			elif stage == 3:
				stage_text = "Detecting Tweet"
				stage = 2
			elif stage == 4:
				stage_text = "Screenshotting Tweet"
			elif stage == 5:
				stage = 4 # We're still technically in phase 4
				
				# Check if progressfile name was passed in the URL field
				if url == "": # No filename on this stage means it's downloading
					stage_text = "Downloading Video"
				else: # If there is a filename passed on this stage, we activate a worker process to keep checking it
					stage_text = ""
					progressfile = url
					
					# Activate another worker to query the progressfile
					self.vidworker = Worker(check_progress_file, progressfile)
					
					# Connect worker signals to functions to manage the GUI
					# TODO FUTURE REVIEW/CHANGE THESE???
					#self.vidworker.signals.finished.connect(self.vid_finished)
					self.vidworker.signals.progress.connect(self.vid_progress)
					self.threadpool.start(self.vidworker)
			elif stage == 6:
				stage_text = ""
			else:
				stage_text = "UNKNOWN"
						
			# Set text to stage string
			if stage_text != "":
				self.stage_bar.setFormat(stage_text)
			
			# Set progress bar value
			self.stage_bar.setValue(stage)
		
		# Update the image with the latest version
		if image is not None:
			# Only update the image if it's large enough
			if image.width > 0:
				# Keep this copy not as thumbnail for copy to clipboard
				self.clipboard_copy = image.copy()
				
				# Create new Image to copy this into
				thumbnail = Image.new("RGBA", (self.clipboard_copy.size[0],self.clipboard_copy.size[1]))
				thumbnail.paste(self.clipboard_copy, (0, 0))
				thumbnail.thumbnail((400,600))
				# https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.thumbnail

				imagedata = thumbnail.tobytes("raw","RGBA")
				qt_image = QImage(imagedata, thumbnail.size[0], thumbnail.size[1], QImage.Format_RGBA8888)
				
				pixmap = QPixmap.fromImage(qt_image)
				self.preview_image.setPixmap(pixmap)
				
				# TODO FUTURE REVIEW: way to associate thread image with update? 
				# TODO FUTURE REVIEW: Send the image back each time and don't use globals!!!
				self.preview_info.setText("Preview image of search #" + str(self.last_search))
				
				# Make preview_info viewable
				self.preview_info.show()
		# Adjust size based on what's changed
		self.adjustSize()
	
	### video_progress()
	# Run another worker asyncio job to track the ffmpeg progress file
	# Random props to this guy (https://superuser.com/a/1460400) for recommending a look at this thing (https://github.com/slhck/ffmpeg-normalize/blob/master/ffmpeg_normalize/_cmd_utils.py)
	# Not my biggest problem (dealing with threads in my wack gui) but I appreciate its elegance and that someone else had to deal with a similar type of bullshit (morale-boosting when dealing with esoteric bullshit)
	def vid_progress(self, progress_data):
		progress = progress_data[2] # string is the 'progress' key
		
		# TODO FUTURE: stick everything in 'progress' and then parse it in here instead
		#keys = progress.splitlines()
		
		if progress == "end":
			# TODO FUTURE: perhaps I can skip this step, or do some other stuff here
			self.stage_bar.setFormat("Compositing Finished")
			self.adjustSize()
		else:
			# Update the progress bar text
			self.stage_bar.setFormat("Compositing Video (" + progress + ")")
			self.adjustSize()
	
	# Set the UI to the state when the search is done
	def search_finished(self, result):
		# Set the UI to the state when the search is done
		self.search_bar.setRange(0,1)
	
		if len(result) > 0:
			self.search_bar.setFormat("All searches complete! (With Errors)")
			self.search_bar.setValue(0)
			# TODO FUTURE: change colors
		else:
			self.search_bar.setFormat("All searches complete!")
			self.search_bar.setValue(1)
		
		self.tweet_box.hide()
		self.stage_box.hide()
		
		self.cancel_button.hide()
		self.finish_button.show()
		
		# Update the GUI
		self.adjustSize()
		
		# Print any failed output
		if len(result) > 0:
			failed = result[0]
			failedfile = result[1]
			
			self.disable_buttons()
			error_message = QMessageBox(QMessageBox.Critical, "[" + str(len(failed)) + "] Searches Failed!", "[" + str(len(failed)) + "] searches failed to complete.\n\nA list of failures has been saved to '" + failedfile + "'", buttons=QMessageBox.StandardButton.Ok, parent=self)
			error_message.exec()
			self.enable_buttons()

	# TODO FUTURE FEATURE?: DRAG AND DROP IMAGE PREVIEW
	# https://doc.qt.io/qtforpython-6.4/overviews/dnd.html#drag-and-drop
	### Functions for drag and drop
	#def mousePressEvent(self, event):
	#	if (event.button() == Qt.LeftButton and self.preview_image.geometry().contains(event.pos())):
	#		drag = QDrag(self)
	#		
	#		imagedata = self.clipboard_copy.tobytes("raw","RGBA")
	#		fullimage = QImage(imagedata, self.clipboard_copy.size[0], self.clipboard_copy.size[1], QImage.Format_RGBA8888)	
	#		drag.setPixmap(QPixmap.fromImage(fullimage))
	#		
	#		mimeData = QMimeData()
	#		#mimeData.setText(commentEdit.toPlainText())
	#		mimeData.setImageData(fullimage)
	#		drag.setMimeData(mimeData)
			
			#Qt.DropAction dropAction = drag.exec()
	#		dropAction = drag.exec()