# Until I can figure out how to show NSFW games using this,
# the project is dead smfh
# i hate itch

import requests
import questionary
import rich
import sys
import os
import dotenv
import time
import gzip
import zipfile
import shutil
import json

from rich.progress import Progress, TaskID
from rich.console  import Console

from urllib.request import urlretrieve

if __name__ == "__main__":
	dotenv.load_dotenv("../.env")
else:
	dotenv.load_dotenv(".env")

GAME_DIR = os.getenv("game_dir", "")
API_KEY  = os.getenv("itch_auth", "")

detectedPlatform = os.name
console = Console(log_time=False)

piTask:TaskID
progressIndicator:Progress

match detectedPlatform:
	case "nt":
		PLATFORM = "p_windows"
		WORKING_DIR = "%LOCALAPPDATA/itchable"

	case "posix":
		PLATFORM = "p_linux"
		WORKING_DIR = "/tmp/itchable"

	case _:
		PLATFORM = "?"
		WORKING_DIR = "None"

# General configuration
SEARCH_ENDPOINT = "https://itch.io/autocomplete?query={query}" # Must be URL encoded
UPLOAD_ENDPOINT = "https://api.itch.io/games/{gameID}/uploads?api_key={ak}"
DWNLOD_ENDPOINT = "https://api.itch.io/uploads/{fileID}/download?api_key={ak}" # YOU DON'T NEED AN API KEY, HALLELUJAH
# edit four hours later: FUCK, YOU NEED AUTHENTICATION TWT
# edit 7 minutes later: lowkey not my problem LMFAO

DEBUG = False

def _debug_log(text:str):
	if DEBUG:
		console.log(f"[bold orange]DEBUG[/]: [magenta]{text}[/]")

def reporthook(count, block_size, total_size):
    global progressIndicator
    global piTask

    progress_size = int(count * block_size)

    progressIndicator.update(piTask, completed=progress_size, total=total_size)
    # sys.stdout.write("\r...%d%%, %d MB, %d KB/s, %d seconds passed" %
    #                 (percent, progress_size / (1024 * 1024), speed, duration))
    # sys.stdout.flush()

def download(file_id:str, game_name:str):
	global progressIndicator, piTask
	downloadTarget = DWNLOD_ENDPOINT.format(fileID=file_id, ak=API_KEY)

	if os.path.exists(WORKING_DIR + f"/{game_name}"):
		# Use the cached file
		console.print("[yellow]Using cached update file[/]")
		return WORKING_DIR + f"/{game_name}"

	with Progress() as progressIndicator:
		piTask = progressIndicator.add_task(f"[yellow]Downloading [purple]{game_name}[/][/]", total=1)

		try:
			response = urlretrieve(downloadTarget, WORKING_DIR + f"/{game_name}", reporthook)
			return response[0]

		except Exception as err:
			progressIndicator.stop()

			_debug_log(str(err))
			return ""

def update(game_dir:str):
	""" Check if the game has any updates """

	# Note to self:
	# gameInfo["upload"]["filename"]

	_debug_log(f"Working with game [yellow]{game_dir}[/]")

	if os.path.exists(f"{game_dir}/.itch/receipt.json.gz"):
		if not os.path.exists(f"{game_dir}/receipt.json"):
			# Extract the JSON first
			with gzip.open(f"{game_dir}/.itch/receipt.json.gz", "rb") as gz_in:
				with open(f"{game_dir}/.itch/receipt.json", "wb") as gz_out:
					shutil.copyfileobj(gz_in, gz_out)

		if not os.path.exists(f"{game_dir}/.itch/_ibgv"):
			with open(f"{game_dir}/.itch/receipt.json", "r") as rjR:
				receipt = json.loads(rjR.read())

				game_version = receipt["upload"]["filename"]
				game_id      = receipt["game"]["id"]

				with open(f"{game_dir}/.itch/_ibgv", "x") as rjW:
					rjW.write(game_version)
					rjW.flush()

				with open(f"{game_dir}/.itch/_ibgid", "x") as ibgidW:
					ibgidW.write(str(game_id))
					ibgidW.flush()

		else:
			with open(f"{game_dir}/.itch/_ibgv", "r") as ibgvR:
				game_version = ibgvR.read()

			with open(f"{game_dir}/.itch/_ibgid", "r") as ibgidR:
				game_id = ibgidR.read()

		# Check the latest available version
		with console.status("[yellow]Checking for updates[/]"):
			itch_game_info = requests.get(UPLOAD_ENDPOINT.format(gameID=game_id, ak=API_KEY))
			itch_game_info = json.loads(itch_game_info.text)

			selected_package = ""
			file_name = ""

		_debug_log(itch_game_info)

		if "authentication required" in str(itch_game_info) or "invalid key" in str(itch_game_info):
			console.log("[red]You need to provide a valid API key. See the readme.[/]")
			return

		for package in itch_game_info["uploads"]:
			try:
				if PLATFORM in package["traits"]:
					selected_package = package["id"]
					file_name = package["filename"]

			except:
				NotImplemented

		if selected_package != "":
			if file_name != game_version:
				do_update = questionary.select("Update found! Install?", ["Yes", "No"]).ask()

				if do_update == "Yes":
					dlfile = download(selected_package, file_name)

					if dlfile != "":
						with console.status("[yellow]Installing update[/]"):
							for file in os.listdir(game_dir):
								if file != ".itch":
									try:
										shutil.rmtree(f"{game_dir}/{file}")

									except NotADirectoryError:
										os.remove(f"{game_dir}/{file}")

							shutil.move(dlfile, f"{game_dir}/{file_name}")

							with zipfile.ZipFile(f"{game_dir}/{file_name}", "r") as game_archive:
								game_archive.extractall(game_dir)

							with open(f"{game_dir}/.itch/_ibgv", "w") as ibgvW:
								ibgvW.truncate(0)
								ibgvW.seek(0)

								ibgvW.write(file_name)
								ibgvW.flush()

						console.print("[yellow]Update complete![/]")

					else:
						console.print("[red]Failed to download update[/]")

				else:
					console.print("[yellow]Returning[/]")
					return

			else:
				console.print("[yellow]Game is already up to date[/]")

		else:
			console.print("[bold red]Failed to get update info from Itch[/]")

	else:
		console.print("[bold red]Itch receipt is missing. Cannot continue![/]")
		time.sleep(5)
		return

def _interface():
	# Setup

	if PLATFORM != "?":
		if not os.path.exists(WORKING_DIR):
			os.mkdir(WORKING_DIR)

	else:
		console.print(f"[red]Platform type [purple]{detectedPlatform}[/] is not supported[/]")
		return

if __name__ == "__main__":
	if PLATFORM != "?":
		if not os.path.exists(WORKING_DIR):
			os.mkdir(WORKING_DIR)

	else:
		console.print(f"[red]Platform type [purple]{detectedPlatform}[/] is not supported[/]")

	gp = input("> ")

	update(gp)
