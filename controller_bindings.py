# This library binds controller input to keyboard input
# Mostly added so I could launch RenPy games straight from my WiiU gaamepad
# It's worth noting that this module will not work on non-x11 systems. So Windows and Wayland are unsupported

import os
import time

import multiprocessing
import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning)

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = 'true'
os.environ['PYGAME_DETECT_AVX2'] = '0'

class ci:
	DPAD_UP    = (0, 1)
	DPAD_DOWN  = (0, -1)
	DPAD_LEFT  = (-1, 0)
	DPAD_RIGHT = (1, 0)

	A = 0
	B = 1
	X = 2
	Y = 3

class co:
	DPAD_UP    = "Up"
	DPAD_DOWN  = "Down"
	DPAD_LEFT  = ""
	DPAD_RIGHT = ""

	A = "Return"
	B = ""
	X = ""
	Y = ""

def start_controller_support() -> multiprocessing.Process:
	instance = multiprocessing.Process(target=_threaded_controller_manager, daemon=True, name="Gamepad bindings")
	instance.start()

	return instance

def send_keystroke(keystroke):
	os.system(f"xdotool key {keystroke}")

def _threaded_greet_controller(controller):
	controller.rumble(100, 1000, 1)
	time.sleep(0.2)
	controller.stop_rumble()

def _threaded_controller_manager():
	try:
		import pygame
	except:
		return
	pygame.init()

	num_detected_joys = pygame.joystick.get_count()

	if num_detected_joys == 0 or os.name != "posix":
		return

	controllers = []

	for event in pygame.event.get():
		if event.type == pygame.JOYDEVICEADDED:
			controllers.append(pygame.joystick.Joystick(event.device_index))

	for controller in controllers:
		_threaded_greet_controller(controller)

	while True:
		try:
			for event in pygame.event.get():
				if event.type == pygame.JOYBUTTONDOWN:
					match event.button:
						case ci.A:
							send_keystroke(co.A)

				if event.type == pygame.JOYHATMOTION:
					match event.value:
						case ci.DPAD_UP:
							send_keystroke(co.DPAD_UP)
						case ci.DPAD_DOWN:
							send_keystroke(co.DPAD_DOWN)

				if event.type == pygame.JOYDEVICEADDED:
					new_controller = pygame.joystick.Joystick(event.device_index)

					_threaded_greet_controller(new_controller)

				if event.type == pygame.QUIT:
					pygame.quit()

			# A, B, X, Y, DPAD
			# controller_input = [gamepad.get_button(ci.A), gamepad.get_button(ci.B), gamepad.get_button(ci.X), gamepad.get_button(ci.Y), gamepad.get_hat(0)]

		except Exception:
			print("\a")

if __name__ == "__main__":
	# Despite the name, this will be  run in the main thread instead of a subprocess
	_threaded_controller_manager()
