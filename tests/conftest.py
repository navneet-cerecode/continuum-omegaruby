"""Make the documented project-local test temp path work in a clean checkout."""
from pathlib import Path


def pytest_sessionstart(session):
    (Path(session.config.rootpath) / ".runtime").mkdir(exist_ok=True)
