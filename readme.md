A simple text-based launcher for Itch games. Open your visual novels without the damned Itch app eating resources!

Requires the following Python modules:
- questionary
- dotenv
- pyimgur
- Pillow
- requests

Primarily developed for Linux, but Windows should technically be supported

## Environment Variables

`game_dir = "/path/to/games"` - The path Itchable will scan for games\
`itch_auth = "auth_key"`      - Itch auth key, for updating games. See the section below\
`autocheck_updates = True`    - Whether to automatically check for game updates
`raw_cake = False`            - Whether to enable unfinished / half-baked features
`use_discord_rpc = False`     - Whether to enable Discord RPC

## Updating Games

This project supports using Itch to check for and install game updates, with a few caveats:

1. The game must have originally been insstalled using the Itch app
2. You must have an Itch account
3. The Itch app will no longer know what version is installed

### Getting your API key

1. Open the [Itch API keys page](https://itch.io/user/settings/api-keys)
2. Click `Generate new API key`
3. On the new API key, click `View`
4. Copy the API key
5. Create the .env file in the same folder as `launcher.py`
6. Set the `itch_auth` env var by typing `itch_auth = "paste_your_api_key_here"` and saving the file
