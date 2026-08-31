def build_context(results: list) -> str:

    context_parts = []

    for index, result in enumerate(results, start=1):

        payload = result.payload

        file_path = payload["file_path"]
        start_line = payload.get("start_line")
        end_line = payload.get("end_line")
        symbols = payload.get("symbols", [])
        text = payload["text"]
        symbol_line = f"Symbols: {', '.join(symbols)}\n" if symbols else ""

        context_parts.append(
            f"""
--- Source {index} ---
File: {file_path}
Lines: {start_line} - {end_line}
{symbol_line}

{text}
"""
        )

    return "\n".join(context_parts)
