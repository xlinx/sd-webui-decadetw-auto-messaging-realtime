import launch

if not launch.is_installed("pyautogui"):
    launch.run_pip(f"install pyautogui", "pyautogui")
