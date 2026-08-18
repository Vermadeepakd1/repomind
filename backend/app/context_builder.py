def build_context(results: list) -> str:

    context_parts = []

    for index, result in enumerate(results, start=1):

        payload = result.payload

        file_path = payload["file_path"]
        start_line = payload.get("start_line")
        end_line = payload.get("end_line")
        text = payload["text"]

        context_parts.append(
            f"""
--- Source {index} ---
File: {file_path}
Lines: {start_line} - {end_line}

{text}
"""
        )

    return "\n".join(context_parts)