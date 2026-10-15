from typing import List, Dict, Any, Optional, Tuple

class Chunk:
    def __init__(self, text: str, chunk_index: int, page_number: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None):
        self.text = text
        self.chunk_index = chunk_index
        self.page_number = page_number
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "chunk_index": self.chunk_index,
            "page_number": self.page_number,
            "metadata": self.metadata,
        }

class RecursiveTextChunker:
    """Configurable recursive character/sentence chunker."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50, separators: Optional[List[str]] = None):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be non-negative and less than chunk_size")
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""]

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        """Recursively split text using hierarchy of separators."""
        final_chunks: List[str] = []
        separator = separators[-1]
        new_separators = []

        for i, _s in enumerate(separators):
            if _s == "":
                separator = _s
                break
            if _s in text:
                separator = _s
                new_separators = separators[i + 1:]
                break

        splits = text.split(separator) if separator else list(text)

        good_splits: List[str] = []
        for s in splits:
            if not s:
                continue
            if len(s) < self.chunk_size:
                good_splits.append(s)
            else:
                if new_separators:
                    other_chunks = self._split_text(s, new_separators)
                    good_splits.extend(other_chunks)
                else:
                    # Character slice fallback
                    for idx in range(0, len(s), self.chunk_size - self.chunk_overlap):
                        good_splits.append(s[idx:idx + self.chunk_size])

        # Merge small splits up to chunk_size with chunk_overlap
        current_chunk: List[str] = []
        current_len = 0

        for piece in good_splits:
            piece_len = len(piece) + (len(separator) if current_chunk else 0)
            if current_len + piece_len <= self.chunk_size:
                current_chunk.append(piece)
                current_len += piece_len
            else:
                if current_chunk:
                    merged = separator.join(current_chunk).strip()
                    if merged:
                        final_chunks.append(merged)
                    
                    # Compute overlap from end of current_chunk
                    overlap_chunk: List[str] = []
                    overlap_len = 0
                    for prev_piece in reversed(current_chunk):
                        if overlap_len + len(prev_piece) <= self.chunk_overlap:
                            overlap_chunk.insert(0, prev_piece)
                            overlap_len += len(prev_piece)
                        else:
                            break
                    current_chunk = overlap_chunk
                    current_len = overlap_len
                
                current_chunk.append(piece)
                current_len += len(piece)

        if current_chunk:
            merged = separator.join(current_chunk).strip()
            if merged:
                final_chunks.append(merged)

        return final_chunks

    def chunk_extracted_pages(self, pages: List[Tuple[str, Optional[int]]]) -> List[Chunk]:
        """Chunk a sequence of extracted (page_text, page_num) sections into indexed Chunks."""
        all_chunks: List[Chunk] = []
        global_index = 0

        for page_text, page_num in pages:
            if not page_text.strip():
                continue
            split_texts = self._split_text(page_text, self.separators)
            for split_text in split_texts:
                if not split_text.strip():
                    continue
                metadata = {
                    "char_count": len(split_text),
                    "word_count": len(split_text.split()),
                    "chunk_size": self.chunk_size,
                    "chunk_overlap": self.chunk_overlap,
                }
                all_chunks.append(
                    Chunk(
                        text=split_text,
                        chunk_index=global_index,
                        page_number=page_num,
                        metadata=metadata,
                    )
                )
                global_index += 1

        return all_chunks
