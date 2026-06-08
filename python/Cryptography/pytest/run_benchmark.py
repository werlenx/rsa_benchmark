import pytest
import sys

# Entry point

sys.exit(pytest.main([
    ".",
    "--benchmark-only",
    "--benchmark-sort=name",
    "-v"
]))
