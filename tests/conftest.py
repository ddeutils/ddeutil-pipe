import shutil
from collections.abc import Generator
from pathlib import Path

import pytest
from ddeutil.io.param import Params

from .utils import dotenv_setting, initial_sqlite

collect_ignore: list[str] = [
    "vendors",
    "test_loader_simple.py",
]

dotenv_setting()
initial_sqlite()


@pytest.fixture(scope="session")
def root_path() -> Path:
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def test_path(root_path) -> Path:
    return root_path / "tests"


@pytest.fixture(scope="session")
def data_path(test_path: Path) -> Path:
    return test_path / "data"


@pytest.fixture(scope="session")
def conf_path(data_path: Path) -> Path:
    return data_path / "conf"


@pytest.fixture(scope="session")
def params_session(
    conf_path: Path,
    test_path: Path,
    root_path: Path,
) -> Generator[Params, None, None]:
    yield Params.model_validate(
        {
            "engine": {
                "paths": {
                    "conf": conf_path,
                    "data": test_path / ".cache",
                    "root": root_path,
                },
            },
            "stages": {
                "raw": {"format": "{naming:%s}.{timestamp:%Y%m%d_%H%M%S}"},
                "staging": {"format": "{naming:%s}.{version:v%m.%n.%c}"},
                "persisted": {
                    "format": "{domain:%s}_{naming:%s}.{compress:%-g}",
                    "rules": {
                        "compress": "gzip",
                    },
                },
            },
        }
    )
    if (test_path / ".cache").exists():
        shutil.rmtree(test_path / ".cache")


@pytest.fixture(scope="session")
def params_simple(
    conf_path: Path,
    root_path: Path,
) -> Generator[Params, None, None]:
    yield Params.model_validate(
        {
            "engine": {
                "paths": {
                    "conf": conf_path,
                    "root": root_path,
                },
            },
        }
    )
