def chunk_text(text: str, *, max_chars: int = 1000, overlap_chars: int = 100) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []

    text = "\n".join([line.rstrip() for line in text.splitlines()])
    text = text.replace("\t", " ")

    paras = [p.strip() for p in text.split("\n\n") if p.strip()]

    def hard_split(s: str) -> list[str]:
        if len(s) <= max_chars:
            return [s]
        parts = []
        start = 0
        while start < len(s):
            end = min(start + max_chars, len(s))
            parts.append(s[start:end].strip())
            start = end
        return [p for p in parts if p]

    expanded_paras = []
    for p in paras:
        expanded_paras.extend(hard_split(p))

    chunks = []
    buf = ""

    def flush():
        nonlocal buf
        if buf.strip():
            chunks.append(buf.strip())
        buf = ""

    for p in expanded_paras:
        if not buf:
            buf = p
        elif len(buf) + 2 + len(p) <= max_chars:
            buf += "\n\n" + p
        else:
            flush()
            buf = p

    flush()

    if overlap_chars > 0 and len(chunks) > 1:
        overlapped = []
        prev_tail = ""
        for c in chunks:
            if prev_tail:
                overlapped.append((prev_tail + "\n\n" + c).strip())
            else:
                overlapped.append(c)
            prev_tail = c[-overlap_chars:] if len(c) > overlap_chars else c
        return overlapped

    return chunks