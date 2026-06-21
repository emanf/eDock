<p align="center">
  <img src="edock_logo.jpg" width="300" alt="eDock Logo">
</p>

<h1 align="center">eDock</h1>

<p align="center">
  A desktop dock for running open-source Python apps directly from source code.
</p>

<p align="center">
  Build apps. Drop them into the dock. Launch, inspect, and improve them.
</p>

---

## What is eDock?

eDock is a Python desktop dock that sits on the edge of your screen and gives you quick access to small apps and tools.

Each icon in the dock is a real Python app.

These apps are not packaged into closed binaries. They run directly from their source code, which means users and developers can:

- launch apps instantly from the dock
- inspect how each app works
- edit the source code
- improve or customize apps
- build and share their own apps

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
- built with Python and PySide6

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

Fork the repository, make your changes, and open a pull request.
