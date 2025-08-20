""" Handles uploading the game cover to itch """

import requests

from io import BytesIO

from PIL import Image

from modules.colour import YELLOW, RESET
from modules.po2    import nearest_power_of_2

def upload_cover_to_itch(game_cover, launch_path, ich, _imgur):
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

	print(YELLOW + "Image uploaded to " + game_image + RESET)
	with open(f"{launch_path}/.{ich}/icon_url", "x") as icon_url:
		icon_url.write(imgur_url.link_big_square)

	return game_image
