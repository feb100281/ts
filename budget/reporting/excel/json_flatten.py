def flatten_json(data, prefix=""):
    rows = []

    if isinstance(data, dict):
        for key, value in data.items():
            new_prefix = f"{prefix}.{key}" if prefix else str(key)
            rows.extend(flatten_json(value, new_prefix))

    elif isinstance(data, list):
        for idx, value in enumerate(data):
            new_prefix = f"{prefix}[{idx}]"
            rows.extend(flatten_json(value, new_prefix))

    else:
        rows.append((prefix, data))

    return rows