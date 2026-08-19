from sampletones_shared.types.data import SerializedData


def renamed(data: SerializedData, old_key: str, new_key: str) -> SerializedData:
    renamed = dict(data)
    if old_key in renamed:
        renamed[new_key] = renamed.pop(old_key)

    return renamed
