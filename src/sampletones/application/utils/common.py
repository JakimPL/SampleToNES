import dearpygui.dearpygui as dpg


def dpg_delete_item(tag: str) -> None:
    if dpg.does_item_exist(tag):
        dpg.delete_item(tag)


def dpg_delete_children(tag: str) -> None:
    if dpg.does_item_exist(tag):
        dpg.delete_item(tag, children_only=True)


def dpg_configure_item(tag: str, **kwargs) -> None:
    if dpg.does_item_exist(tag):
        dpg.configure_item(tag, **kwargs)
