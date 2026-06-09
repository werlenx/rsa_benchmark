import sys

import pytest

# Entry point

sys.exit(pytest.main([
    ".",
    "--benchmark-only",
    "--benchmark-sort=name",
    "-v",
]))
