def chunk_text(
    text: str,
    chunk_size: int = 1200,
    overlap: int = 200
):
    lines = text.splitlines(keepends=True)

    chunks = []

    start_line = 0

    while start_line < len(lines):

        current_length = 0
        end_line = start_line

        # Build the chunk
        while (
            end_line < len(lines)
            and (
                current_length + len(lines[end_line])
                <= chunk_size
                or end_line == start_line
            )
        ):
            current_length += len(lines[end_line])
            end_line += 1

        # Prefer ending at a logical blank-line or closing-brace boundary
        # when doing so does not make the chunk too small.
        if end_line < len(lines):
            minimum_boundary = start_line + max(4, (end_line - start_line) // 2)
            boundary = end_line
            while boundary > minimum_boundary:
                line = lines[boundary - 1].strip()
                if not line or line.endswith(("}", "])")):
                    end_line = boundary
                    break
                boundary -= 1

        chunk = "".join(
            lines[start_line:end_line]
        )

        if chunk.strip():

            chunks.append({
                "text": chunk,
                "start_line": start_line + 1,
                "end_line": end_line
            })

        # Finished the file
        if end_line >= len(lines):
            break

        # Find overlap start
        overlap_length = 0
        new_start = end_line

        while (
            new_start > start_line
            and overlap_length < overlap
        ):
            new_start -= 1
            overlap_length += len(lines[new_start])

        # Make sure the next chunk contains
        # some new content
        if new_start == start_line:
            new_start = start_line + 1

        start_line = new_start

    return chunks
