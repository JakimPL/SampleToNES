from sampletones_shared.types.data import SerializedData


def renamed(data: SerializedData, old_key: str, new_key: str) -> SerializedData:
    entries = dict(data)
    if old_key in entries:
        entries[new_key] = entries.pop(old_key)

    return entries
