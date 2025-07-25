"""
Itchable game launcher

Set game_dir below, after imports
"""

import questionary
import os
import sys
import time
import dotenv
import gzip
import shutil
import json
import requests
import pyimgur

from po2 import nearest_power_of_2

from io import BytesIO
from PIL import Image

from colour import *

from remote_manager import mount_game_folder, unmount_game_folder
from controller_bindings import start_controller_support

BUILD_VERSION = 4
USERNAME = os.getlogin()

# Load environment variables
dotenv.load_dotenv(".env")
game_dir = os.getenv("game_dir")

def _imgur():
	return pyimgur.Imgur(os.getenv("imgur_key"), os.getenv("imgur_secret"), refresh_token=os.getenv("irt"))

try:
	import discordrpc as rpc

	rpc_available = True

except:
	rpc_available = False

if rpc_available:
	rpc_connection = rpc.RPC(1348177137575661588, False, False, exit_on_disconnect=False)

	rpc_connection.set_activity("Browsing for games", large_image="itch_icon")

QUESTIONARY_STYLES = questionary.Style(
	[
		("unsupported", "fg:#ff0000"),
		("non_itch", "fg:#d1c62a"),
		("itch", "fg:#14e329"),
		("system", "fg:#9e35e8")
	]
)

"""
CONSTANTS. DO NOT TOUCH
"""
PATH = sys.path[0]
VALID_EXECUTABLES = ["sh", "x86_64", "exe"] # Executable formats, in order of priority

"""
USER-CONFIGURABLE CONSTANTS
"""

"""
VARIABLES
"""

detected_directories = [] # Contains directories found in %game_dir%
itch_games =  {} # Games installed from itch
cust_games =  [] # Games not installed from itch
unsupported = [] # Games we cannot launch (web games, for example)
cs = None

show_unsupported_only = False

def clear():
	if os.name != "NT": os.system("clear")
	else: os.system("cls")

def search_game_dir(reset_list:bool=False):
	""" Search %game_dir% """

	global detected_directories, itch_games, cust_games, unsupported

	if reset_list:
		detected_directories = []
		itch_games = {}
		cust_games = []
		unsupported = []

	# Build initial list
	for entry in os.listdir(game_dir):
		if os.path.isdir(game_dir + entry): detected_directories.append(entry)

	if len(detected_directories) == 0: print(RED + "No games detected!" + RESET)

	# Parse the directories and determine type

	for game_folder in detected_directories:
		if os.path.exists(game_dir + game_folder + "/.itch"):
			itch_check_versions(game_folder, game_dir + game_folder + "/")
		else:
			valid = False
			for file in os.listdir(game_dir + game_folder):
				try:
					if str(file).split(".")[len(str(file).split("."))-1] in VALID_EXECUTABLES: valid = True
					else: NotImplemented
				except: NotImplemented # No file extension, don't handle it because it's probably Wine being annoying

			if valid:
				cust_games.append(game_folder)
			else:
				unsupported.append(game_folder)

def itch_check_versions(game_name:str, game_path:str):
	""" Check what versions of a game are available """

	global detected_directories, itch_games, cust_games, unsupported

	versions = []

	if "index.html" in os.listdir(game_path):
		unsupported.append(game_name)

	for version in os.listdir(game_path):
		if version != ".itch" and version != "remote_launch.json": versions.append(version)

	itch_games.update({game_name:versions})

def find_executable(launch_path):
	launch_file = None

	for extension in VALID_EXECUTABLES:
		if launch_file != None: continue

		for file in os.listdir(launch_path):
				try:
					if not os.path.isfile(launch_path + file): continue;
					if launch_file != None: continue

					if str(str(file).split(".")[len(str(file).split("."))-1]) == str(extension):
						launch_file = file

				except Exception as err: print(str(err))

	if not launch_file == None:
		return launch_file

	else:
		return -1

def launch_executable(launch_path, game_name:str="", game_cover:str="itch_icon"):
	""" Determine executable type and determine best launch method """
	print(f"{MAGENTA}Launching {game_name}")

	if rpc_available:
		rpc_connection.set_activity(f"Playing {game_name}", large_image=game_cover)

	global cs
	if cs is not None:
		if cs.is_alive:
			cs.kill()
		cs = None


	if ".sh" in launch_path or ".x86_64" in launch_path:
		# Linux native, launch directly

		if not os.access(launch_path, os.X_OK):
			print(RED + "File is not allowed to execute!" + RESET)

			if input(BLUE + "Would you like to make it executable? [Y/N] > ").lower() == "y":
				os.system(f"chmod +x {launch_path}")

				print(YELLOW + "File was made executable. Launching..." + RESET)

			else:
				print(YELLOW + "Attempting to launch anyways..." + RESET)

		print(DRIVES)
		os.system(launch_path)

	elif ".exe" in launch_path:
		# Windows executable, determine if Wine is needed

		if os.name != "NT":
			print(YELLOW + "Warning: launching using Wine's default prefix! Output will be messy" + DRIVES)
			os.system(f"wine {launch_path}")
			print(RESET)

		else:
			print(DRIVES)
			os.system(launch_path)
			print(RESET)

	else:
		print(RED + "Unknown executable type. Attempting direct run..." + DRIVES)
		os.system(launch_path)

	if rpc_available:
		rpc_connection.set_activity(state="Browsing for games", large_image="itch_icon")

	print(YELLOW + "Subprocess exited" + RESET)
	time.sleep(5)

# Build iniital list of games
search_game_dir()

if __name__ == "__main__":
	while True:
		cs = start_controller_support()
		clear()

		if os.name != "posix":
			print(YELLOW + "Controllers are NOT supported on this platform!)" + RESET)

		if os.path.exists("/tmp/_itchable_game_image"):
			os.remove("/tmp/_itchable_game_image")

		# Main loop #
		# Build the main menu #

		# The main menu is rebuilt each loop, because it doesn't cost that much to iterate a list in memory
		# Note: this menu should remain static unless search_game_dir() is explicitly called
		# Scanning the disk for files is more expensive, so we avoid it unless requested (on launch or by user)
		menu_choices = []


		if not show_unsupported_only:
			for game in sorted(itch_games.keys()):
				menu_choices.append(questionary.Choice(title=[("class:itch", game)]))

			for game in sorted(cust_games):
				menu_choices.append(questionary.Choice(title=[("class:non_itch", game)]))

		# Unsupported games aren't shown by default, but give a menu option if unsupported games are detected

		if len(unsupported) != 0:
			if not show_unsupported_only: menu_choices.append(questionary.Choice(title=[("class:unsupported", "(System) Unsupported Games")]))

		if show_unsupported_only:
			if len(unsupported) != 0:
				print(YELLOW + "The following games were detected, but cannot be launched by Itchable:" + RESET)
				for game in sorted(unsupported):
					print(RED + game + RESET)
			else: print(YELLOW + "No unsupported games detected" + RESET)

			show_unsupported_only = False
			input(RED + "Press enter to continue" + RESET)
			clear()

		else:
			if rpc_available: menu_choices.append(questionary.Choice(title=[("class:system", "(Itchable) Disable RPC for session")]))
			menu_choices.append(questionary.Choice(title=[("class:system", "(Itchable) Override game directory")]))
			if os.path.exists("/bin/ajax12"): menu_choices.append(questionary.Choice(title=[("class:system", "(System) Mod Injector")]))
			menu_choices.append(questionary.Choice(title=[("class:system", "(System) Scan for changes")]))
			menu_choices.append(questionary.Choice(title=[("class:system", "(System) Exit")]))

			if not rpc_available: print(YELLOW + "Discord RPC is unavailable or disabled" + RESET)

			prompt = questionary.select("Select a game", menu_choices, style=QUESTIONARY_STYLES).ask()

			match prompt:
				case "(System) Unsupported Games":
					show_unsupported_only = True
					clear()

				case "(Itchable) Disable RPC for session":
					rpc_connection.disconnect()
					rpc_available = False

				case "(Itchable) Override game directory":
					new_path = questionary.path("New game path").ask()

					game_dir = new_path

					print(YELLOW + f"Scanning {new_path} for games..." + RESET)

					search_game_dir(True)

				case "(System) Scan for changes":
					clear()
					print(YELLOW + "Scanning for new or changed files..." + RESET)

					search_game_dir(True) # Re-scan the disk

				case "(System) Mod Injector":
					print("\n" + RESET)
					os.system("ajax12")

				case "(System) Exit":
					if cs is not None:
						if cs.is_alive:
							cs.kill()

					sys.exit(0)

				case _:
					clear()

					# Determine launch type
					if prompt in itch_games:
						print(f"{YELLOW}Launching {MAGENTA}{prompt}{YELLOW}...{RESET}" )

						launch_path = game_dir + prompt
						game_title = None

						if os.path.exists(launch_path):
							# Decompress the itch game info, it will be used to get the game's display name
							try:
								with gzip.open(f"{launch_path}/.itch/receipt.json.gz", "rb") as gz_in:
									with open(f"{launch_path}/.itch/receipt.json", "wb") as gz_out:
										shutil.copyfileobj(gz_in, gz_out)

								with open(f"{launch_path}/.itch/receipt.json", "r") as receipt_raw:
									receipt = json.loads(receipt_raw.read())

								game_title = receipt["game"]["title"]
								game_cover = receipt["game"]["coverUrl"]

								# Check if the game has a cached imgur URL
								if os.path.exists(f"{launch_path}/.itch/icon_url"):
									UPLOADED = True

									with open(f"{launch_path}/.itch/icon_url", "r") as cached_image:
										game_image = cached_image.read()

									print(YELLOW + "Using already uploaded image" + RESET)

								else:
									UPLOADED = False

							except Exception:
								UPLOADED = True

								game_cover = "itch_icon"
								game_image = "itch_icon"

							# Crop the fuckin image
							try:
								if not UPLOADED:
									print(YELLOW + "Configuring game image..." + RESET)

									response = requests.get(game_cover)
									img = Image.open(BytesIO(response.content))
									width, height = img.size

									new_width = 512 if width >= 512 else (nearest_power_of_2(height) if height <= width else nearest_power_of_2(width))
									new_height = new_width

									left = (width - new_width)/2
									top = (height - new_height)/2
									right = (width + new_width)/2
									bottom = (height + new_height)/2

									img = img.crop((left, top, right, bottom))

									img.save("/tmp/_itchable_game_image", format="PNG")

									imgur = _imgur()

									imgur_url = imgur.upload_image("/tmp/_itchable_game_image")
									game_image = imgur_url.link_big_square

									print(YELLOW + "Image uploaded to " + game_image)

									with open(f"{launch_path}/.itch/icon_url", "x") as icon_url:
										icon_url.write(imgur_url.link_big_square)


							except Exception as err:
								print(RED + "Failed to upload to Imgur! " + str(err) + RESET)
								game_image = "itch_icon"

							if len(os.listdir(launch_path)) > 2:
								# Show a prompt screen
								clear()

								detected_versions:list = os.listdir(launch_path)
								try:
									detected_versions.remove(".itch")
									detected_versions.remove("remote_launch.json")
								except Exception:
									NotImplemented # pyright:ignore

								try:
									detected_versions.remove("global")
								except Exception:
									NotImplemented # pyright:ignore

								version = questionary.select("Select version", detected_versions).ask()

								is_remote = False
								game_mounted = [False, ""]

								if version == "remote":
									game_mounted = mount_game_folder(game_dir + prompt, game_dir)
									is_remote = True

								if game_mounted[0]: #pyright:ignore
									print(RED + "Streaming game files from another device!\n" + RESET)

								launch_path = f"{launch_path}/{version}/"
								launch_file = find_executable(launch_path)

								preservedlp = f"{launch_path}"

								if not launch_file == -1:
									launch_path = launch_path + launch_file

									print(f"{YELLOW}Found executable! Launching using {MAGENTA}{launch_path}{RESET}")

									# game_name = game_mounted[1] if is_remote else version
									if game_title is None:
										game_title = version
									game_name = game_title

									launch_executable(launch_path, game_name, game_image)

								else:
									print(RED + "Failed to find valid executable! Aborting..." + RESET)
									time.sleep(5)

								# Unmount if remote
								if game_mounted[0]:
									unmount_game_folder(preservedlp)



							else:
								# Launch the available version
								found_launchable = False

								for dir in os.listdir(launch_path):
									if dir != ".itch":
										found_launchable = True

										launch_path = launch_path + f"/{dir}/"
										version = dir

										print(f"{YELLOW}Found game version: {MAGENTA}{dir}{YELLOW}, attempting launch...")
										print(f"{YELLOW}Current path is {MAGENTA}{launch_path}{RESET}")

								if not found_launchable:
									print(f"{RED}Couldn't find a version of {MAGENTA}{prompt}{RED} to launch!")
									time.sleep(5)

								else:
									# Find the executable #

									launch_file = find_executable(launch_path)

									if not launch_file == -1:
										launch_path = launch_path + launch_file

										print(f"{YELLOW}Found executable! Launching using {MAGENTA}{launch_path}{RESET}")

										launch_executable(launch_path, game_title, game_image)

									else:
										print(RED + "Failed to find valid executable! Aborting..." + RESET)
										time.sleep(5)

						else:
							print(RED + "WARNING: Directory has moved or been deleted!" + RESET)
							time.sleep(5)
							search_game_dir(True) # Force a rescan, since and invalid entry has been generated

					elif prompt in cust_games:
						print(f"{YELLOW}Launching {MAGENTA}{prompt}{YELLOW}...{RESET}")

						launch_path = game_dir + prompt + "/"
						launch_file = find_executable(launch_path)

						if not launch_file == -1:
							launch_path = launch_path + launch_file

							print(f"{YELLOW}Found executable! Launching using {MAGENTA}{launch_path}{RESET}")

							launch_executable(launch_path, launch_file)

						else:
							print(RED + "Failed to find valid executable! Aborting..." + RESET)
							time.sleep(5)
