import datetime
from rich.console import RenderableType
from rich.text import Text
from textual import events
from textual.widgets import TreeNode

from ...ui.widgets import TodoList
from ...ui.events.events import ChangeStatus


class DateTree(TodoList):
    async def validate(self, day, month, year) -> bool:
        try:
            datetime.datetime(int(year), int(month), int(day))
            return True
        except ValueError:
            return False

    async def add_child(self):
        node = self.nodes[self.highlighted]
        if node == self.root or node.parent == self.root:
            await node.add("child", self.get_box())
            await node.expand()
            await self.reach_to_last_child()

    async def add_sibling(self):
        if self.nodes[self.highlighted].parent == self.root:
            await self.root.add("child", self.get_box())
            await self.move_to_bottom()
        else:
            await self.reach_to_parent()
            await self.add_child()

    async def focus_node(self) -> None:
        self.nodes[self.highlighted].data.on_focus()
        self.editing = True
        await self.post_message(ChangeStatus(self, "DATE"))

    async def unfocus_node(self) -> None:
        self.nodes[self.highlighted].data.on_blur()
        self.editing = False
        await self.post_message(ChangeStatus(self, "NORMAL"))

    async def on_key(self, event: events.Key) -> None:
        if self.editing:
            match event.key:
                case "escape":
                    await self.unfocus_node()
                    await self.check_node()
                case _:
                    await self.send_key_to_selected(event)

        else:
            match event.key:
                case "j" | "down":
                    await self.cursor_down()
                case "k" | "up":
                    await self.cursor_up()
                case "g":
                    await self.move_to_top()
                case "G":
                    await self.move_to_bottom()
                case "z":
                    await self.toggle_expand()
                case "Z":
                    await self.toggle_expand_parent()
                case "A":
                    await self.add_child()
                case "a":
                    await self.add_sibling()
                case "d":
                    await self.focus_node()
                case "x":
                    await self.remove_node()

        self.refresh()

    async def check_node(self):
        pass

    def render_custom_node(self, node: TreeNode) -> RenderableType:

        color = "yellow"
        match node.data.todo.status:
            case "PENDING":
                color = "yellow"
            case "COMPLETE":
                color = "green"
            case "OVERDUE":
                color = "red"

        # Setting up text
        label = Text.from_markup(
            str(node.data.render()),
        )

        if not label.plain:
            label = Text("No due date")

        # fix padding
        label = Text(" ") + label
        label.pad_right(self.size.width)

        if node.id == self.highlighted:
            if self.editing:
                label.stylize(self.style_editing)
            else:
                label.stylize(self.style_focus)
        else:
            label.stylize(self.style_unfocus)

        # setup pre-icons
        label = Text.from_markup(f"[{color}]  [/{color}]") + label

        return label