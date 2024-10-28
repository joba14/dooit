from uuid import uuid4
from dataclasses import dataclass
from typing import Any, ClassVar, Dict, List, Literal, Optional, TYPE_CHECKING
from typing_extensions import Self
from rich.text import Text

if TYPE_CHECKING:
    from dooit.api.workspace import Workspace
    from dooit.api.todo import Todo


SortMethodType = Literal["description", "status", "due", "urgency", "effort"]


@dataclass
class Result:
    """
    Response class to return result of an operation
    """

    ok: bool
    cancel_op: bool
    message: Optional[str] = None
    color: str = "white"

    @classmethod
    def result_ok(cls, message: Optional[str] = None):
        return cls(True, False, message, "green")

    @classmethod
    def result_warn(cls, message: Optional[str] = None):
        return cls(False, False, message, "yellow")

    @classmethod
    def result_err(cls, message: str):
        return cls(False, True, message, "red")

    def is_ok(self) -> bool:
        return self.ok

    def is_err(self) -> bool:
        return not self.ok

    def text(self):
        def colored(a, b):
            return f"[{b}]{a}[/{b}]"

        if self.message:
            return colored(self.message, self.color)

        return Text()


Ok = Result.result_ok
Err = Result.result_err
Warn = Result.result_warn


class ChildManager:
    """
    Manages children operations for Model class
    """

    def __init__(self, parent: "Model"):
        self.parent = parent

    def get_children(self, kind: str) -> List:
        if kind not in ["workspace", "todo"]:
            raise TypeError(f"Cannot perform this operation for type {kind}")
        return self.parent.workspaces if kind.lower() == "workspace" else self.parent.todos

    def get_child_index(self, kind: str, **kwargs) -> int:
        key, value = list(kwargs.items())[0]
        for i, child in enumerate(self.get_children(kind)):
            if getattr(child, key) == value:
                return i
        return -1

    def add_child(self, kind: str, index: int = 0, inherit: bool = False) -> Any:
        # We cannot place those imports at the file scope because
        # that would cause relatve import error
        # pylint: disable=relative-beyond-top-level,import-outside-toplevel
        from ..api.workspace import Workspace
        from ..api.todo import Todo

        child = Workspace(parent=self.parent) if kind == "workspace" else Todo(parent=self.parent)
        if inherit and isinstance(self.parent, Todo):
            child.fill_from_data(self.parent.to_data(), overwrite_uuid=False)
            child.description, child.effort = "", 0
            child.edit("status", "PENDING")

        children = self.get_children(kind)
        children.insert(index, child)
        return child

    def remove_child(self, kind: str, uuid: str) -> Optional[Any]:
        idx = self.get_child_index(kind, uuid=uuid)
        return self.get_children(kind).pop(idx) if idx != -1 else None


class Model:
    """
    Model class to for the base tree structure
    """

    class_kind: ClassVar[str]
    fields: List
    sortable_fields: List[SortMethodType]

    def __init__(
        self,
        parent: Optional["Model"] = None,
    ) -> None:
        self._uuid = f"{self.kind}_{uuid4()}"
        self.parent = parent

        self.child_manager = ChildManager(self)
        self.workspaces: List[Workspace] = []
        self.todos: List[Todo] = []

    @property
    def uuid(self) -> str:
        return self._uuid

    @property
    def kind(self):
        return self.class_kind

    @property
    def nest_level(self):
        level = 0
        kind = self.kind
        parent = self.parent

        while parent and parent.kind == kind:
            level += 1
            parent = parent.parent

        return level

    @property
    def is_last_sibling(self) -> bool:
        if parent := self.parent:
            return parent.child_manager.get_children(self.kind)[-1] == self

        return False

    @property
    def is_first_sibling(self) -> bool:
        if parent := self.parent:
            return parent.child_manager.get_children(self.kind)[0] == self

        return False

    @property
    def has_same_parent_kind(self) -> bool:
        if parent := self.parent:
            return parent.kind == self.kind

        return False

    def _get_index(self) -> int:
        """
        Get items's index among it's siblings
        """

        if not self.parent:
            return -1

        return self.parent.child_manager.get_child_index(self.kind, uuid=self._uuid)

    def edit(self, key: str, value: str) -> Result:
        """
        Edit item's attrs
        """

        var = f"_{key}"
        if hasattr(self, var):
            return getattr(self, var).set(value)

        return Err("Invalid Request!")

    def shift_up(self) -> None:
        """
        Shift the item one place up among its siblings
        """

        idx = self._get_index()

        if idx in [0, -1]:
            return

        if not self.parent:
            return
        arr = self.parent.child_manager.get_children(self.kind)
        arr[idx], arr[idx - 1] = arr[idx - 1], arr[idx]

    def shift_down(self) -> bool:
        """
        Shift the item one place down among its siblings
        """

        idx = self._get_index()

        if idx == -1 or not self.parent:
            return False

        arr = self.parent.child_manager.get_children(self.kind)
        if idx == len(arr) - 1:
            return False

        arr[idx], arr[idx + 1] = arr[idx + 1], arr[idx]
        return True

    def prev_sibling(self) -> Optional[Self]:
        """
        Returns previous sibling item, if any, else None
        """

        if not self.parent:
            return None

        idx = self.parent.child_manager.get_child_index(self.kind, uuid=self._uuid)

        if idx:
            return self.parent.child_manager.get_children(self.kind)[idx - 1]
        return None

    def next_sibling(self) -> Optional[Self]:
        """
        Returns next sibling item, if any, else None
        """

        if not self.parent:
            return None

        idx = self.parent.child_manager.get_child_index(self.kind, uuid=self._uuid)
        arr = self.parent.child_manager.get_children(self.kind)

        if idx < len(arr) - 1:
            return arr[idx + 1]
        return None

    def add_sibling(self, inherit: bool = False) -> Self:
        """
        Add item sibling
        """

        if self.parent:
            return self.parent.child_manager.add_child(self.kind, self._get_index() + 1, inherit)

        raise TypeError("Cannot add sibling")

    def drop(self) -> None:
        """
        Delete the item
        """

        if self.parent:
            self.parent.child_manager.remove_child(self.kind, self._uuid)

    def sort(self, attr: str) -> None:
        """
        Sort the children based on specific attr
        """

        if self.parent:
            children = self.parent.child_manager.get_children(self.kind)
            children.sort(key=lambda x: getattr(x, f"_{attr}").get_sortable())

    def commit(self) -> Dict[str, Any]:
        """
        Get a object summary that can be stored
        """

        return {
            getattr(
                child,
                "description",
            ): child.commit()
            for child in self.workspaces
        }

    def from_data(self, data: Dict[str, Any]) -> None:
        raise NotImplementedError

    def get_all_workspaces(self) -> List:
        # We cannot place those imports at the file scope because
        # that would cause relatve import error
        # pylint: disable=import-outside-toplevel,relative-beyond-top-level
        from ..api.workspace import Workspace

        arr = [self] if isinstance(self, Workspace) else []
        for i in self.workspaces:
            arr.extend(i.get_all_workspaces())

        return arr

    def get_all_todos(self) -> List:
        # We cannot place those imports at the file scope because
        # that would cause relatve import error
        # pylint: disable=import-outside-toplevel,relative-beyond-top-level
        from ..api.todo import Todo

        arr = [self] if isinstance(self, Todo) else []
        for i in self.todos:
            arr.extend(i.get_all_todos())

        return arr

    def __init_subclass__(cls) -> None:
        cls.class_kind = cls.__name__.lower()


Model.__init_subclass__()
