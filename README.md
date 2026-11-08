# Among Us Deduction Panel — Android project

A Kivy-based Android rewrite of the desktop CustomTkinter tracker.

## Build an APK

Buildozer is best run on Linux or WSL2 (Ubuntu), not directly inside Android Termux.

1. Install Ubuntu / WSL2 or use a Linux computer.
2. Install build dependencies:

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git zip unzip \
  openjdk-17-jdk autoconf libtool pkg-config zlib1g-dev \
  libncurses5-dev libncursesw5-dev libtinfo6 cmake libffi-dev libssl-dev
```

3. Create a virtual environment and install Buildozer:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install buildozer cython
```

4. Put `main.py` and `buildozer.spec` in the same directory, then run:

```bash
buildozer android debug
```

5. The APK will be created under `bin/`. Copy it to your Android phone and install it.
   Android may ask you to allow installation from that file manager/browser.

## App use

- Players tab: review all ten slots, change Alive/Dead/Ejected/Cleared, and toggle a quick manual suspicion flag.
- Locations tab: log rooms and round timestamps.
- Alibis tab: enter claims, partner names, times, and verified/unverified status.
- Events tab: record body reports, meetings, kill windows, manual flags, and notes.
- Save/Load: stores a JSON match file in the app's private storage.

## Notes

- This is a manual companion app. It does not read game memory, connect to Among Us, or modify game files.
- Suspicion scores are heuristic review signals, not probabilities or proof.
- Room travel times are approximate. Vents, doors, sabotage, map differences, and game settings can invalidate warnings.
- Buildozer Android builds are most reliable on Linux. Building directly inside Termux on the phone is not the supported workflow.
