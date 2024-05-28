## Imports ##
import sys
import asyncio
import traceback
import logging

from PySide6.QtCore import Signal, Slot, QObject, QRunnable

# TODO FUTURE REVIEW
#from asyncio.exceptions import InvalidStateError

# Possible reference to look into re: thread management and being able to kill windows without causing problems with workers: https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html#PySide6.QtCore.PySide6.QtCore.QThread

### GUI Worker class for threading
# Reference: https://www.pythonguis.com/tutorials/multithreading-pyqt-applications-qthreadpool/
# This is used both by the sub-process that archives a tweet and the sub-sub-process that checks the ffmpeg progress file
class Worker(QRunnable):
	'''
	Worker thread

	Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

	:param callback: The function callback to run on this worker thread. Supplied args and
					 kwargs will be passed through to the runner.
	:type callback: function
	:param args: Arguments to pass to the callback function
	:param kwargs: Keywords to pass to the callback function
	'''

	def __init__(self, fn, *args, **kwargs):
		super(Worker, self).__init__()
		
		self.log = logging.getLogger(__name__)
		
		# Store constructor arguments (re-used for processing)
		self.fn = fn
		self.args = args
		self.kwargs = kwargs
		self.signals = WorkerSignals()

		# Add the callback to our kwargs
		self.kwargs['progress_callback'] = self.signals.progress

	@Slot()
	def run(self):
		self.result = asyncio.run(self.run_task())
	
	# I needed to make this a task and thus cancellable. Docs: https://docs.python.org/3/library/asyncio-task.html
	async def run_task(self):
		'''
		Initialise the runner function with passed self.args, self.kwargs.
		'''
		try:
			self.task = asyncio.create_task(self.fn(*self.args, **self.kwargs))
			taskrun = await self.task
		except asyncio.exceptions.CancelledError as cancelled:
			self.log.warning("Running worker process cancelled")
		except:
			traceback.print_exc()
			exctype, value = sys.exc_info()[:2]
			self.signals.error.emit((exctype, value, traceback.format_exc()))
		else:
			self.signals.result.emit(self.task.result())  # Return the result of the processing
		finally:
			self.signals.finished.emit() # Run is done
	
	@Slot()
	def exit(self):
		self.log.debug("Cancelling worker")
		self.task.cancel()

### Class for sending signals to worker process
# Reference: https://www.pythonguis.com/tutorials/multithreading-pyqt-applications-qthreadpool/
class WorkerSignals(QObject):
	'''
	Defines the signals available from a running worker thread.

	Supported signals are:

	finished
		No data

	error
		tuple (exctype, value, traceback.format_exc() )

	result
		object data returned from processing, anything

	progress
		tuple holding lots of data
	'''
	finished = Signal()
	error = Signal(tuple)
	result = Signal(object)
	progress = Signal(tuple) # Tuple structure is defined in update_progress() function in TweetDialog in search_window.py