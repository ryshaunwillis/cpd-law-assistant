import json
import os
import time
from pathlib import Path
from typing import Any

import tiktoken
from openai import OpenAI


BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_JSONL = BASE_DIR / "data" / "processed" / "ilcs" / "ilcs_720_5_chunks.jsonl"
OUT_DIR = BASE_DIR / "data" / "processed" / "ilcs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_JSONL = OUT_DIR / "ilcs_720_5_chunks_embedded.jsonl"
STATE_PATH = OUT_DIR / "ilcs_720_5_embedding_state.json"

# Good default for cost/performance. You can switch to text-embedding-3-large later.
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# For v3 embedding models, OpenAI recommends cl100k_base for token counting.
ENCODING_NAME = "cl100k_base"

# Stay conservative so we never get near model limits.
MAX_TOKENS_PER_INPUT = 7500

# Batch a few chunks at a time for efficiency.
BATCH_SIZE = 32

# Optional shortening parameter supported by v3 embeddings models.
# Leave unset to use full size. Example env value: 1024
EMBEDDING_DIMENSIONS = os.getenv("OPENAI_EMBEDDING_DIMENSIONS")

# Simple retry settings
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 2.0


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"last_completed_index": -1}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def count_tokens(text: str, encoding: tiktoken.Encoding) -> int:
    return len(encoding.encode(text))


def trim_text_to_token_limit(text: str, encoding: tiktoken.Encoding, max_tokens: int) -> str:
    tokens = encoding.encode(text)
    if len(tokens) <= max_tokens:
        return text
    trimmed = encoding.decode(tokens[:max_tokens])
    return trimmed


def prepare_input_text(chunk: dict[str, Any], encoding: tiktoken.Encoding) -> tuple[str, int]:
    content = (chunk.get("content") or "").strip()
    token_count = count_tokens(content, encoding)

    if token_count > MAX_TOKENS_PER_INPUT:
        content = trim_text_to_token_limit(content, encoding, MAX_TOKENS_PER_INPUT)
        token_count = count_tokens(content, encoding)

    return content, token_count


def build_embedding_request_kwargs(texts: list[str]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": EMBEDDING_MODEL,
        "input": texts,
    }

    if EMBEDDING_DIMENSIONS:
        kwargs["dimensions"] = int(EMBEDDING_DIMENSIONS)

    return kwargs


def request_embeddings_with_retry(client: OpenAI, texts: list[str]) -> list[list[float]]:
    delay = INITIAL_RETRY_DELAY

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.embeddings.create(**build_embedding_request_kwargs(texts))
            return [item.embedding for item in response.data]
        except Exception as exc:
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"Embedding request failed after {MAX_RETRIES} attempts: {exc}") from exc

            print(f"Embedding request failed (attempt {attempt}/{MAX_RETRIES}): {exc}")
            print(f"Retrying in {delay:.1f}s...")
            time.sleep(delay)
            delay *= 2

    raise RuntimeError("Unexpected retry flow failure.")


def main() -> None:
    if not INPUT_JSONL.exists():
        raise FileNotFoundError(f"Chunk file not found: {INPUT_JSONL}")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY is not set.")

    client = OpenAI(api_key=api_key)
    encoding = tiktoken.get_encoding(ENCODING_NAME)

    chunks = load_jsonl(INPUT_JSONL)
    if not chunks:
        raise RuntimeError("No chunks found in input JSONL.")

    state = load_state()
    start_index = state.get("last_completed_index", -1) + 1

    if start_index >= len(chunks):
        print("All chunks are already embedded.")
        print(f"Output file: {OUT_JSONL}")
        return

    print(f"Loaded chunks: {len(chunks)}")
    print(f"Starting at:   {start_index}")
    print(f"Model:         {EMBEDDING_MODEL}")

    # If starting from scratch, clear old output file.
    if start_index == 0 and OUT_JSONL.exists():
        OUT_JSONL.unlink()

    for batch_start in range(start_index, len(chunks), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(chunks))
        batch = chunks[batch_start:batch_end]

        prepared_texts: list[str] = []
        prepared_meta: list[tuple[dict[str, Any], int]] = []

        for chunk in batch:
            text, token_count = prepare_input_text(chunk, encoding)
            prepared_texts.append(text)
            prepared_meta.append((chunk, token_count))

        embeddings = request_embeddings_with_retry(client, prepared_texts)

        output_rows: list[dict[str, Any]] = []
        for (chunk, token_count), embedding in zip(prepared_meta, embeddings):
            row = {
                **chunk,
                "embedding_model": EMBEDDING_MODEL,
                "embedding_dimensions": len(embedding),
                "content_token_count": token_count,
                "embedded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "embedding": embedding,
            }
            output_rows.append(row)

        append_jsonl(OUT_JSONL, output_rows)

        save_state({"last_completed_index": batch_end - 1})

        print(
            f"Embedded batch {batch_start}-{batch_end - 1} "
            f"({batch_end}/{len(chunks)})"
        )

    print("Done embedding all chunks.")
    print(f"Saved JSONL: {OUT_JSONL}")
    print(f"Saved state: {STATE_PATH}")


if __name__ == "__main__":
    main()