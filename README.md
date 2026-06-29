<p align="center">
  <img src="edock_logo.jpg" width="300" alt="eDock Logo">
  <img src="edock.gif" width="250">
</p>

# eDock


eDock is a simple place for people to build, place, and share small apps.

It started as a long-time idea: a dock where each icon can launch a separate Python app, keeping every app independent and easy to update without changing the others. The project was originally written in AutoIt Script, but it moved to Python because Python fits the idea better and makes the project easier to grow and share.

eDock apps work directly from source, so each app can be shared in its source form and run by eDock without needing to be bundled into a separate build first. This keeps apps simple, flexible, and easy to maintain.

eDock is meant for small tools, simple workflows, and personal apps that stay focused on one job. It is built for people who want a lightweight way to organize apps in a dock-style interface and share them with others.

---
# Usage

## 1. Install Python:
```text
https://www.python.org/downloads/
```

## 2. Install Git:
```text
https://github.com/git-guides/install-git
```

## 3. Clone the repository:
Run the following commands in **Command Prompt (Windows)** or **Terminal (macOS/Linux)**:
```bash
git clone https://github.com/emanf/edock.git
```
```bash
cd edock
```

## 4. Install pip:
```bash
python -m ensurepip --upgrade
```

## 5. Install dependencies:
```bash
pip install -r requirements.txt
```

## 6. Run eDock:
```bash
python main.py
```
or
```bash
pyw main.py
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
