from app.chunking import chunk_text


text = """line one
line two
line three
line four
line five
"""


chunks = chunk_text(
    text,
    chunk_size=25,
    overlap=5
)


for chunk in chunks:

    print("-----")

    print(
        "Lines:",
        chunk["start_line"],
        "-",
        chunk["end_line"]
    )

    print(
        chunk["text"]
    )