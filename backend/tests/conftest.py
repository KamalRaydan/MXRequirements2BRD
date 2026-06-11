"""Point app data + project folders at temp dirs before any app module loads."""
import os
import tempfile

os.environ.setdefault("APP_DATA_DIR", tempfile.mkdtemp(prefix="maximobrd-test-appdata-"))
os.environ.setdefault("PROJECTS_DEFAULT_DIR", tempfile.mkdtemp(prefix="maximobrd-test-projects-"))
