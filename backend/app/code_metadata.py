import re


SYMBOL_PATTERNS = (
    r"\b(?:def|class|function)\s+([A-Za-z_$][\w$]*)",
    r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?",
    r"\b([A-Za-z_$][\w$]*)\s*\([^\n{}]*\)\s*\{",
)


def extract_symbols(text: str) -> list[str]:
    symbols = []
    for pattern in SYMBOL_PATTERNS:
        symbols.extend(re.findall(pattern, text))

    unique_symbols = []
    for symbol in symbols:
        if symbol not in unique_symbols:
            unique_symbols.append(symbol)

    return unique_symbols[:12]
