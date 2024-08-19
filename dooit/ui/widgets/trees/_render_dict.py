from typing import Dict, Generic, TypeVar
from dooit.api import Workspace, Todo
from dooit.ui.widgets.renderers import (
    BaseRenderer,
    TodoRender,
    WorkspaceRender,
)

T = TypeVar("T", bound=BaseRenderer)


class RenderDict(Dict, Generic[T]):
    """
    Default Dict implementation for Todo/Workspace Renderers
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def from_id(self, _id: str) -> T:
        raise NotImplementedError

    def __getitem__(self, __key: str) -> T:
        return super().__getitem__(__key)

    def __missing__(self, key: str) -> T:
        self[key] = self.from_id(key)
        return self[key]


class WorkspaceRenderDict(RenderDict[WorkspaceRender]):
    """
    Default Dict implementation for Workspace Renderers
    """

    def from_id(self, _id: str) -> WorkspaceRender:
        w = Workspace.from_id(_id)
        return WorkspaceRender(w)


class TodoRenderDict(RenderDict[TodoRender]):
    """
    Default Dict implementation for Todo Renderers
    """

    def from_id(self, _id: str) -> TodoRender:
        t = Todo.from_id(_id)
        return TodoRender(t)