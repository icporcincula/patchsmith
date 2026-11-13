"""Command-line entry point for owner-managed project profiles."""

import importlib.util
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "patchsmith_profile_cli", root / "__init__.py", submodule_search_locations=[str(root)],
)
package = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = package
spec.loader.exec_module(package)

from patchsmith_profile_cli.profiles import main  # noqa: E402

if __name__ == "__main__":
    main()
