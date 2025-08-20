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
import time
import tarfile

from zipfile import BadZipFile, ZipFile, ZipInfo

from rich.progress import Progress, TaskID
from rich.console  import Console
from rich.table    import Table

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

QS = questionary.Style(
	[
		("unsupported", "fg:#ff0000"),
		("non_itch", "fg:#d1c62a"),
		("detached_itch", "fg:#83ff4a"),
		("itch", "fg:#14e329"),
		("system", "fg:#9e35e8"),
		('disabled', 'fg:#858585 italic'),
		('highlighted', 'fg:#ffe600'),
		("current", 'fg:#eba834'),
		("new", 'fg:#eba834'),
		('selected', 'fg:#ff6a00 noreverse'),
		('text', 'fg:#ff0000'),             # plain text
		('highlighted', 'fg:#ffe600'),
	]
)

DEBUG = False

class ZipFileWithPermissions(ZipFile):
	""" Custom ZipFile class handling file permissions. """
	def _extract_member(self, member, targetpath, pwd):
		if not isinstance(member, ZipInfo):
			member = self.getinfo(member)

		targetpath = super()._extract_member(member, targetpath, pwd)

		attr = member.external_attr >> 16
		if attr != 0:
			os.chmod(targetpath, attr)
		return targetpath

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

	if os.path.exists(WORKING_DIR + f"/{game_name}") and not os.path.exists(WORKING_DIR + f"/{game_name}.temp"):
		# Use the cached file
		console.print("[yellow]Using cached update file[/]")
		return WORKING_DIR + f"/{game_name}"

	if os.path.exists(WORKING_DIR + f"/{game_name}.temp"):
		console.print("[bold yellow]Removing partial download[/]")
		os.remove(WORKING_DIR + f"/{game_name}")

	if not os.path.exists(WORKING_DIR + f"/{game_name}.temp"):
		open(WORKING_DIR + f"/{game_name}.temp", "x").close()

	with Progress() as progressIndicator:
		piTask = progressIndicator.add_task(f"[yellow]Downloading [purple]{game_name}[/][/]", total=1)

		try:
			response = urlretrieve(downloadTarget, WORKING_DIR + f"/{game_name}", reporthook)
			os.remove(WORKING_DIR + f"/{game_name}.temp")
			return response[0]

		except Exception as err:
			progressIndicator.stop()

			_debug_log(str(err))
			return ""

def ibl_retach(game_dir:str, prompt):
	return ibl_detach(game_dir, prompt, True)

def ibl_detach(game_dir:str, prompt, reattach:bool=False) -> str:
	""" Detach a game from the Itch app """

	_debug_log(f"Working with game [yellow]{game_dir}[/]")

	try:
		if not reattach:
			shutil.move(f"{game_dir}/.itch", f"{game_dir}/.ibl")
			shutil.move(f"{game_dir}", f"{game_dir}-d")
			console.print("[green]Detached![/]")
			return prompt + "-d"
		else:
			shutil.move(f"{game_dir}/.ibl", f"{game_dir}/.itch")
			shutil.move(f"{game_dir}", game_dir[:-2])
			console.print("[green]Reattached![/]")
			return prompt[:-2]

	except Exception as err:
		console.log("[red]Failed: " + str(err) + "[/]")
		return game_dir

	return game_dir

def scan_all_games_for_updates(itch_games:list, game_path, force_updates:bool=False):
	""" Check all games for updates """
	has_updates = {}

	console.print("[yellow]Checking for updates[/]")
	for itch_game in itch_games:
		console.print(f"[yellow]Checking [/][magenta]{itch_game}[/]")

		if not force_updates:
			cv = update(f"{game_path}/{itch_game}", check_only=True)
		else:
			cv = update(f"{game_path}/{itch_game}", check_only=True, allfUp=True)

		if isinstance(cv, tuple):
			current_version:str = cv[0]
			new_version:str = cv[1]

			if not new_version == "":
				try:
					has_updates[current_version] = [new_version, itch_game]

				except TypeError:
					NotImplemented #type:ignore

	if len(has_updates.keys()) > 0:
		console.clear()
		console.print("[magenta]" + str(len(has_updates.keys())) + "[/][yellow] games can be updated[/]")

		uPvS = []
		prnt = []
		gmns = []

		for cv in has_updates.keys():
			nv = has_updates[cv]
			ngv = nv[0]
			gn = nv[1]

			gmns.append(gn)

			console.print(f"[yellow]{cv}[/] => [magenta]{ngv}[/]")
			uPvS.append([("class:current", f"{cv} ", "class:new", f"{ngv}")])

		for instance in uPvS:
			prnt.append(questionary.Choice(title=instance, checked=True, value=gmns[uPvS.index(instance)]))

		games_to_update = questionary.checkbox("Select updates to install", choices=prnt, style=QS).ask()
		update_status = {}

		for uix in games_to_update:
			us = update(f"{game_path}/{uix}", silent_install=True, allfUp=True)

			match us:
				case 0:
					us = False
				case 1:
					us = True
				case _:
					us = False

			update_status[uix] = us

		# Print update summary
		console.print("Update summary:")

		summary_table = Table(show_header = True, header_style="bold yellow")
		summary_table.add_column("GAME NAME")
		summary_table.add_column("UPDATED")

		for game in update_status.keys():
			summary_table.add_row(game, str(update_status[game]))

		console.print(summary_table)
		time.sleep(5)

	else:
		console.print("[yellow]All games are up-to-date!")

	time.sleep(5)

def _cGi(game_dir, ich, check_only:bool=False) -> tuple:
	if os.path.exists(f"{game_dir}/.{ich}/receipt.json.gz"):
		if not os.path.exists(f"{game_dir}/receipt.json"):
			# Extract the JSON first
			with gzip.open(f"{game_dir}/.{ich}/receipt.json.gz", "rb") as gz_in:
				with open(f"{game_dir}/.{ich}/receipt.json", "wb") as gz_out:
					shutil.copyfileobj(gz_in, gz_out)

		if not os.path.exists(f"{game_dir}/.{ich}/_ibgv"):
			with open(f"{game_dir}/.{ich}/receipt.json", "r") as rjR:
				receipt = json.loads(rjR.read())

				game_version = receipt["upload"]["filename"]
				game_id      = receipt["game"]["id"]

				with open(f"{game_dir}/.{ich}/_ibgv", "x") as rjW:
					rjW.write(game_version)
					rjW.flush()

				with open(f"{game_dir}/.{ich}/_ibgid", "x") as ibgidW:
					ibgidW.write(str(game_id))
					ibgidW.flush()

		else:
			with open(f"{game_dir}/.{ich}/_ibgv", "r") as ibgvR:
				game_version = ibgvR.read()

			with open(f"{game_dir}/.{ich}/_ibgid", "r") as ibgidR:
				game_id = ibgidR.read()

		return game_version, game_id

	else:
		if not check_only:
			console.print("[bold red]Itch receipt is missing. Cannot continue![/]")
			time.sleep(5)
		return (None, None)

def update(game_dir:str, silent_install:bool=False, check_only:bool=False, force_reinstall:bool=False, allfUp:bool=False):
	""" Check if the game has any updates """

	# Note to self:
	# gameInfo["upload"]["filename"]

	_debug_log(f"Working with game [yellow]{game_dir}[/]")

	if not os.path.exists(WORKING_DIR):
		os.mkdir(WORKING_DIR)

	if os.path.exists(f"{game_dir}/.ibl"):
		ich = "ibl"
	else:
		ich = "itch"

	if True:

		# Get the game info
		_cGiE = _cGi(game_dir, ich, check_only)
		game_version, game_id = _cGiE[0], _cGiE[1]

		if game_version is None:
			return 0

		# Check the latest available version
		with console.status("[yellow]Checking for updates[/]"):
			itch_game_info = requests.get(UPLOAD_ENDPOINT.format(gameID=game_id, ak=API_KEY))
			itch_game_info = json.loads(itch_game_info.text)

			selected_package = ""
			file_name = ""

		_debug_log(itch_game_info)

		if "authentication required" in str(itch_game_info) or "invalid key" in str(itch_game_info):
			console.log("[red]You need to provide a valid API key. See the readme.[/]")
			return 0

		for package in itch_game_info["uploads"]:
			try:
				if PLATFORM in package["traits"]:
					selected_package = package["id"]
					file_name = package["filename"]

			except:
				NotImplemented

		if not os.path.exists(f"{game_dir}/.{ich}/blacklist"):
			os.mkdir(f"{game_dir}/.{ich}/blacklist")

		blacklisted_updates = os.listdir(f"{game_dir}/.{ich}/blacklist")

		if selected_package != "" and not check_only:
			if file_name in blacklisted_updates:
				console.print(f"[yellow]Blacklisted update ([magenta]{file_name}[/]) will not be installed[/]")
				return 0

			if (file_name != game_version) or force_reinstall or allfUp:
				console.print(f"[yellow]Update available:[/] [bold magenta]{game_version}[/] -> [bold green]{file_name}[/]")

				if not silent_install:
					do_update = questionary.select("Install?", ["Yes", "No", "Blacklist update"]).ask()

				else:
					do_update = "Yes"

				if do_update == "Yes":
					dlfile = download(selected_package, file_name)

					if dlfile != "":
						with console.status("[yellow]Installing update[/]"):
							for file in os.listdir(game_dir):
								if file != ".itch" and file != ".ibl":
									try:
										shutil.rmtree(f"{game_dir}/{file}")

									except NotADirectoryError:
										os.remove(f"{game_dir}/{file}")

							shutil.move(dlfile, f"{game_dir}/{file_name}")

							try:
								with ZipFileWithPermissions(f"{game_dir}/{file_name}", "r") as game_archive:
									game_archive.extractall(game_dir)

							except BadZipFile:
								if file_name.endswith(".bz2"):
									shutil.unpack_archive(f"{game_dir}/{file_name}", game_dir, "bztar")
								else:
									shutil.unpack_archive(f"{game_dir}/{file_name}", game_dir)

							with open(f"{game_dir}/.{ich}/_ibgv", "w") as ibgvW:
								ibgvW.truncate(0)
								ibgvW.seek(0)

								ibgvW.write(file_name)
								ibgvW.flush()

						if not silent_install:
							console.print("[yellow]Update complete![/]")
						return 1

					else:
						if not silent_install:
							console.print("[red]Failed to download update[/]")
						return 0

				elif do_update == "Blacklist update":
					with open(f"{game_dir}/.{ich}/blacklist/{file_name}", "x") as blkfile:
						blkfile.write("1")
						blkfile.flush()

					console.print("[yellow]Update blacklisted[/]")

				else:
					return 0

			else:
				console.print("[yellow]Game is already up to date[/]")

		elif check_only:
			if file_name in blacklisted_updates:
				return "None"

			else:
				if (file_name != game_version) or allfUp:
					return (game_version, file_name)

				else:
					return 0

		else:
			console.print("[bold red]Failed to get update info from Itch[/]")

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
