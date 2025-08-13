import os
import questionary
import json
import sys
import time


from modules.colour import RED, YELLOW, BLUE, RESET

PATH = sys.path[0]

def unmount_game_folder(GAME_DIR:str):
	print(YELLOW + f"Unmounting {GAME_DIR}" + RESET)
	os.system(f"umount {GAME_DIR}")
	time.sleep(2)

def mount_game_folder(GAME_DIR:str, install_location:str) -> tuple[bool, str]:
	""" Mounts a remote game folder. Returns `true` on success """
	try:
		with open(f"{GAME_DIR}/remote_launch.json", "r") as remote_config_file:
			rcf = json.loads(remote_config_file.read())
			remote_address = rcf["remote_address"]
			remote_login   = rcf["remote_username"]

			game_name = GAME_DIR.split("/")[len(GAME_DIR.split("/")) - 1].upper()

			print(YELLOW + "Querying remote device..."  + RESET)

			os.system(f"sshfs {remote_address}:{GAME_DIR.replace(os.getlogin(), remote_login)}/global {GAME_DIR}/remote")

			if os.path.ismount(f"{GAME_DIR}/remote"):
				print(YELLOW + f"{game_name} mounted at {GAME_DIR}/remote" + RESET)

				return True, game_name

			else:
				print(RED + "Failed to mount remote game directory!" + RESET)
				return False, ""

	except FileNotFoundError:
		print(RED + "Missing configuration file" + RESET)

		return False, ""

	except Exception as err:
		print(RED + f"Remote launch failed: {str(err)}")

		return False, ""
