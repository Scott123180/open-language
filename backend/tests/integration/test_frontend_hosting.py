"""The backend serves the built frontend only in production; in development Vite serves it."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import FrontendBuildMissingError, serve_built_frontend

_BUILT_PAGE = "<html>built frontend</html>"


@pytest.fixture()
def built_frontend(tmp_path) -> Path:
    (tmp_path / "index.html").write_text(_BUILT_PAGE)
    return tmp_path


def _settings(mode: str) -> Settings:
    return Settings(_env_file=None, mode=mode)


def test_development_does_not_serve_a_built_frontend(built_frontend):
    app = FastAPI()

    serve_built_frontend(app, built_frontend, _settings("development"))

    assert TestClient(app).get("/").status_code == 404


def test_production_serves_the_built_frontend_at_the_root(built_frontend):
    app = FastAPI()

    serve_built_frontend(app, built_frontend, _settings("production"))

    assert TestClient(app).get("/").text == _BUILT_PAGE


def test_production_without_a_build_fails_with_the_command_to_run(tmp_path):
    with pytest.raises(FrontendBuildMissingError, match="npm run build"):
        serve_built_frontend(FastAPI(), tmp_path, _settings("production"))
