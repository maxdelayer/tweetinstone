### main.py
# Used to add some hierarchy to avoid some import conflicts

import asyncio
from .initialize import initialize

def main_cli():
	# Cross your fingers and run!
	asyncio.run(initialize(False))

def main_gui():
	# The boolean here is whether or not to force the gui (since I don't want to mess around with the arguments
	asyncio.run(initialize(True))