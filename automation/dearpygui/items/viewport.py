import dearpygui.dearpygui as dpg

from automation.dearpygui.geometry import Point, Rect


def read_viewport() -> Rect:
    """The viewport's client area, placed where it stands on the screen. Runs on the render thread."""
    corner = dpg.get_viewport_pos()
    return Rect(
        x=corner[0],
        y=corner[1],
        width=dpg.get_viewport_client_width(),
        height=dpg.get_viewport_client_height(),
    )


def read_viewport_decorated() -> bool:
    """Whether the window wears the system's title bar and frame. Runs on the render thread."""
    return bool(dpg.is_viewport_decorated())


def read_viewport_title() -> str:
    """The title the viewport's window carries in its title bar. Runs on the render thread."""
    return str(dpg.get_viewport_title())


def read_pointer() -> Point:
    """Where the pointer stands in the viewport, as the application last saw it. Runs on the render thread."""
    position = dpg.get_mouse_pos(local=False)
    return Point(x=round(position[0]), y=round(position[1]))


def read_client_area() -> Rect:
    """The viewport's client area in the coordinates its items report. Runs on the render thread."""
    return Rect(
        x=0,
        y=0,
        width=dpg.get_viewport_client_width(),
        height=dpg.get_viewport_client_height(),
    )
