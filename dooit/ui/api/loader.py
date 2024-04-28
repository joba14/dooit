import importlib.util
from typing import TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from .plug import PluginManager


def register(api: "PluginManager", path: Path) -> None:
    spec = importlib.util.spec_from_file_location("", path)

    if spec and spec.loader:
        foo = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(foo)
            for name, obj in vars(foo).items():
                if hasattr(obj, "__dooit_event"):
                    api.register(name, obj)
        except:
            pass


def load_dir(api: "PluginManager", path: Path) -> bool:
    if not path.exists():
        return False

    for file in path.iterdir():
        if file.is_dir():
            return load_dir(api, file)

        if file.suffix == ".py":
            register(api, file)

    return True