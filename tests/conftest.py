import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def plugin_root():
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def invoke(plugin_root, tmp_path):
    def invoke_hook(payload, root=plugin_root, environment=None):
        hook_environment = dict(os.environ, XDG_CONFIG_HOME=str(tmp_path / "config"))
        hook_environment.pop("WELLPUT_CONFIG", None)
        hook_environment.update(environment or {})
        result = subprocess.run(
            [sys.executable, "-S", str(root / "hooks/reply_hook.py")],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=5,
            cwd="/",
            env=hook_environment,
            check=True,
        )
        return json.loads(result.stdout)

    return invoke_hook
