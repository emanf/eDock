<p align="center">
  <img src="edock_logo.jpg" width="300" alt="eDock Logo">
  <img src="edock.gif" width="250">
</p>

# eDock

eDock is a Python desktop dock that sits on the edge of your screen and gives you quick access to small apps and tools.

Each icon in the dock is a real Python app.

eDock is designed for an open app ecosystem where every app stays accessible, readable, and extensible.

## How eDock apps work

Every app in eDock is an independent Python app with its own folder, files, and configuration.

That means:

- each app is isolated
- apps can be added or removed easily
- apps can be updated independently
- app source code stays open and editable
- the dock acts as a launcher and host for source-based apps

If you want to create automation tools, utilities, bots, experiments, or personal desktop helpers, eDock gives you a simple way to turn them into dock apps.

## Why eDock?

eDock is built around a simple idea:

**Apps should be easy to run, easy to inspect, and easy to modify.**

Instead of hiding app logic behind compiled packages, eDock keeps apps in plain Python source form. This makes it especially useful for developers who want control, transparency, and fast iteration.

## Features

- desktop dock UI for launching apps
- apps run directly from Python source code
- every app is open and editable
- simple app-based structure
- easy to extend with your own apps
- source-available project
- built with Python

---
# Usage

Download Python:
```bash
https://www.python.org/downloads/
```

Clone the repository:
```bash
git clone https://github.com/emanf/edock.git
```
```bash
cd edock
```

Install pip:
```bash
python -m ensurepip --upgrade
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Run eDock:
```bash
python main.py
```

---

- Python
- PySide6 / Qt for Python

---

Contributions are welcome.

You can help by:

- Reporting bugs
- Suggesting ideas
- Improving the code
- Improving the UI
- Creating eDock apps
- Improving documentation

# App Registry

eDock includes a public app registry where developers can publish and distribute their apps.
The registry repository contains the app indexes and packages used by eDock to discover and install apps.
Developers can submit their apps to the registry so they become available for all eDock users.
App submissions are automated and reviewed through the registry workflow.
For details on how the registry works and how to submit an app, see:
```text
https://github.com/emanf/eDock-Apps
```
