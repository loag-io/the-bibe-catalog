# Initialize project environment
import sys; sys.path.insert(0, next((str(p) for p in __import__('pathlib').Path.cwd().parents if (p/'config').exists()), '.'))

# Import common libraries
from config._common_libraries import *
from config._common_functions import *

class ESVBibleIngestion:
    """
    ESV Bible ingestion client for TrioTheo Bronze layer.

    Schema:
        translation  (str)  : "ESV"
        testament    (str)  : "Old Testament" | "New Testament"
        book         (str)  : Full book name
        chapter      (int)  : Chapter number
        verse_number (int)  : Verse number
        verse_text   (str)  : Clean verse text
        
    Usage (Jupyter Notebook):    
        ingestor = ESVBibleIngestion(api_key="your-token")
    
        # Single passage → df
        df = ingestor.get_passage_df("Genesis 1-3")
    
        # Single book → df
        df = ingestor.get_book_df("Romans")
    
        # Full Bible → df (~7 min, 1,189 API calls)
        df = ingestor.get_full_bible_df()
    """

    # ── API Config ───────────────────────────────────────────────
    BASE_URL      = "https://api.esv.org/v3/passage/text/"
    RATE_LIMIT    = 0.25
    MAX_RETRIES   = 3
    RETRY_BACKOFF = 2.0
    LINE_LEN      = 86  # total width including corner/edge chars

    # ── ESV API Parameters ───────────────────────────────────────
    # Tuned for clean AI/NLP processing
    DEFAULT_PARAMS = {
        "include-passage-references":  False,  # Tracked in schema
        "include-verse-numbers":       True,   # Required for verse parsing
        "include-first-verse-numbers": True,
        "include-footnotes":           False,  # Clean text for AI
        "include-footnote-body":       False,
        "include-headings":            False,  # Clean text for AI
        "include-short-copyright":     False,  # Added at display layer
        "include-selahs":              True,   # Preserve Psalm poetic markers
        "indent-using":                "space",
        "line-length":                 0,      # No artificial line wrapping
    }

    # ── Bible Canon — 66 Books ───────────────────────────────────
    # Format: (book_name, testament, chapter_count)
    BIBLE_CANON = [
        # ── Old Testament (39) ──────────────────
        ("Genesis",         "Old Testament", 50),
        ("Exodus",          "Old Testament", 40),
        ("Leviticus",       "Old Testament", 27),
        ("Numbers",         "Old Testament", 36),
        ("Deuteronomy",     "Old Testament", 34),
        ("Joshua",          "Old Testament", 24),
        ("Judges",          "Old Testament", 21),
        ("Ruth",            "Old Testament",  4),
        ("1 Samuel",        "Old Testament", 31),
        ("2 Samuel",        "Old Testament", 24),
        ("1 Kings",         "Old Testament", 22),
        ("2 Kings",         "Old Testament", 25),
        ("1 Chronicles",    "Old Testament", 29),
        ("2 Chronicles",    "Old Testament", 36),
        ("Ezra",            "Old Testament", 10),
        ("Nehemiah",        "Old Testament", 13),
        ("Esther",          "Old Testament", 10),
        ("Job",             "Old Testament", 42),
        ("Psalms",          "Old Testament",150),
        ("Proverbs",        "Old Testament", 31),
        ("Ecclesiastes",    "Old Testament", 12),
        ("Song of Solomon", "Old Testament",  8),
        ("Isaiah",          "Old Testament", 66),
        ("Jeremiah",        "Old Testament", 52),
        ("Lamentations",    "Old Testament",  5),
        ("Ezekiel",         "Old Testament", 48),
        ("Daniel",          "Old Testament", 12),
        ("Hosea",           "Old Testament", 14),
        ("Joel",            "Old Testament",  3),
        ("Amos",            "Old Testament",  9),
        ("Obadiah",         "Old Testament",  1),
        ("Jonah",           "Old Testament",  4),
        ("Micah",           "Old Testament",  7),
        ("Nahum",           "Old Testament",  3),
        ("Habakkuk",        "Old Testament",  3),
        ("Zephaniah",       "Old Testament",  3),
        ("Haggai",          "Old Testament",  2),
        ("Zechariah",       "Old Testament", 14),
        ("Malachi",         "Old Testament",  4),
        # ── New Testament (27) ──────────────────
        ("Matthew",         "New Testament", 28),
        ("Mark",            "New Testament", 16),
        ("Luke",            "New Testament", 24),
        ("John",            "New Testament", 21),
        ("Acts",            "New Testament", 28),
        ("Romans",          "New Testament", 16),
        ("1 Corinthians",   "New Testament", 16),
        ("2 Corinthians",   "New Testament", 13),
        ("Galatians",       "New Testament",  6),
        ("Ephesians",       "New Testament",  6),
        ("Philippians",     "New Testament",  4),
        ("Colossians",      "New Testament",  4),
        ("1 Thessalonians", "New Testament",  5),
        ("2 Thessalonians", "New Testament",  3),
        ("1 Timothy",       "New Testament",  6),
        ("2 Timothy",       "New Testament",  4),
        ("Titus",           "New Testament",  3),
        ("Philemon",        "New Testament",  1),
        ("Hebrews",         "New Testament", 13),
        ("James",           "New Testament",  5),
        ("1 Peter",         "New Testament",  5),
        ("2 Peter",         "New Testament",  3),
        ("1 John",          "New Testament",  5),
        ("2 John",          "New Testament",  1),
        ("3 John",          "New Testament",  1),
        ("Jude",            "New Testament",  1),
        ("Revelation",      "New Testament", 22),
    ]

    # Lookup: book_name → (testament, chapter_count)
    BOOK_LOOKUP = {book: (testament, chapters) for book, testament, chapters in BIBLE_CANON}

    # ── Init ─────────────────────────────────────────────────────

    def __init__(self, api_key: str = None, rate_limit: float = None):
        self.api_key    = api_key or os.environ.get("ESV_API_KEY", "")
        if not self.api_key:
            raise EnvironmentError(
                "ESV API key required. Pass api_key= or set ESV_API_KEY env var."
            )
        self.rate_limit = rate_limit or self.RATE_LIMIT
        self._headers   = {"Authorization": f"Token {self.api_key}"}

    # ── Public ───────────────────────────────────────────────────

    def get_passage_df(self, passage: str) -> pd.DataFrame:
        """
        Fetch any passage reference and return a verse-per-row DataFrame.
        e.g. "Genesis 1-3", "John 3:16", "Romans 8:1-4"
        """
        start_time = time.time()
        self._print_section_header("ESV PASSAGE FETCH")
        print(f"  Reference: {passage}")

        raw      = self._fetch_raw(passage)
        passages = raw.get("passages", [])

        if not passages:
            print(f"  ⚠️  No passage data returned for: {passage!r}")
            print(f"{'─' * self.LINE_LEN}")
            return self._empty_df()

        canonical       = raw.get("canonical", passage)
        book, testament = self._resolve_book_testament(canonical, passage)
        start_chapter   = self._parse_chapter_from_ref(canonical, passage)

        print(f"  Book: {book}  |  Testament: {testament}  |  Chapter: {start_chapter}")

        rows = self._parse_passage_text(passages[0], book, testament, start_chapter=start_chapter)
        df   = self._to_df(rows)

        duration = time.time() - start_time
        print(f"  ✓ Complete: {len(df)} verses  |  Duration: {format_duration(duration)}")
        print(f"{'─' * self.LINE_LEN}")

        return df

    def get_book_df(self, book_name: str) -> pd.DataFrame:
        """
        Fetch all chapters of a single book.
        e.g. "Romans", "1 Corinthians", "Philemon"
        """
        if book_name not in self.BOOK_LOOKUP:
            raise ValueError(f"Unknown book: {book_name!r}. Check BIBLE_CANON for valid names.")

        testament, chapter_count = self.BOOK_LOOKUP[book_name]
        start_time = time.time()

        self._print_section_header("ESV BOOK FETCH")
        print(f"  Book: {book_name}  |  Testament: {testament}  |  Chapters: {chapter_count}")
        print(f"{'─' * self.LINE_LEN}")

        all_rows = []
        for chapter_num in range(1, chapter_count + 1):
            ref      = f"{book_name} {chapter_num}:1-200"
            raw      = self._fetch_raw(ref)
            passages = raw.get("passages", [])

            if passages:
                chapter_rows = self._parse_passage_text(passages[0], book_name, testament, start_chapter=chapter_num)
                all_rows.extend(chapter_rows)
                print(f"  [{chapter_num:02d}/{chapter_count:02d}] Chapter {chapter_num:<4}  →  {len(chapter_rows):>4} verses  ✓")
            else:
                print(f"  [{chapter_num:02d}/{chapter_count:02d}] Chapter {chapter_num:<4}  →  ⚠️  No data for {ref}")

            time.sleep(self.rate_limit)

        df       = self._to_df(all_rows)
        duration = time.time() - start_time

        print(f"{'─' * self.LINE_LEN}")
        print(f"  ✓ Complete: {len(df)} verses across {chapter_count} chapters  |  Duration: {format_duration(duration)}")
        print(f"{'─' * self.LINE_LEN}")

        return df

    def get_full_bible_df(self) -> pd.DataFrame:
        """
        Ingest all 66 books of the ESV Bible.
        ~1,189 API calls, ~7 min at default rate limit.
        """
        start_time  = time.time()
        inner_width = self.LINE_LEN - 2  # width between ┌ and ┐

        # ── Start banner ─────────────────────────────────────────
        title    = "ESV FULL BIBLE INGESTION"
        sep_len  = inner_width - 2 - len(title) - 1  # ─ + space + title + space + ─...
        meta     = "Books: 66 (39 OT + 27 NT)  |  Est. calls: ~1,189  |  Est. time: ~7 min"
        print(f"\n┌─ {title} {'─' * sep_len}┐")
        print(f"│ {meta:<{inner_width - 2}} │")
        print(f"└{'─' * inner_width}┘")

        all_rows = []

        for testament_label, testament_filter, testament_total in [
            ("OLD TESTAMENT", "Old Testament", 39),
            ("NEW TESTAMENT", "New Testament", 27),
        ]:
            # ── Testament section header ──────────────────────────
            section_title = f"── {testament_label} ({testament_total} books) "
            print(f"\n{section_title}{'─' * (self.LINE_LEN - len(section_title))}")

            book_idx = 0
            for book_name, testament, chapter_count in self.BIBLE_CANON:
                if testament != testament_filter:
                    continue

                book_idx += 1
                book_rows = []

                for chapter_num in range(1, chapter_count + 1):
                    ref      = f"{book_name} {chapter_num}:1-200"
                    raw      = self._fetch_raw(ref)
                    passages = raw.get("passages", [])

                    if passages:
                        book_rows.extend(self._parse_passage_text(passages[0], book_name, testament, start_chapter=chapter_num))
                    else:
                        print(f"  ⚠️  Empty response: {ref}")

                    time.sleep(self.rate_limit)

                all_rows.extend(book_rows)
                print(f"  [{book_idx:02d}/{testament_total:02d}] {book_name:<20} {chapter_count:>3} ch  →  {len(book_rows):>5} verses  ✓")

        # ── Complete banner ───────────────────────────────────────
        df       = self._to_df(all_rows)
        duration = time.time() - start_time

        title    = "ESV FULL BIBLE COMPLETE"
        sep_len  = inner_width - 2 - len(title) - 1
        summary  = f"Total verses: {len(df):,}  |  Books: 66  |  Duration: {format_duration(duration)}"
        print(f"\n┌─ {title} {'─' * sep_len}┐")
        print(f"│ {summary:<{inner_width - 2}} │")
        print(f"└{'─' * inner_width}┘\n")

        return df

    # ── Private: Print Helpers ───────────────────────────────────

    def _print_section_header(self, title: str) -> None:
        """Print a lightweight ── section header (no box)."""
        section = f"── {title} "
        print(f"\n{section}{'─' * (self.LINE_LEN - len(section))}")

    # ── Private: API ─────────────────────────────────────────────

    def _fetch_raw(self, passage: str) -> dict:
        params = {"q": passage, **self.DEFAULT_PARAMS}

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                resp = requests.get(
                    self.BASE_URL, headers=self._headers,
                    params=params, timeout=15
                )
                resp.raise_for_status()
                return resp.json()

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 400:
                    print(f"  ⚠️  Bad request — skipping: {passage!r}")
                    return {}

            except requests.exceptions.RequestException as e:
                print(f"  ⚠️  Request error on {passage!r}, attempt {attempt}: {e}")

            if attempt < self.MAX_RETRIES:
                time.sleep(self.rate_limit * (self.RETRY_BACKOFF ** attempt))

        print(f"  ✗ All {self.MAX_RETRIES} attempts failed for {passage!r}")
        return {}

    # ── Private: Parsing ─────────────────────────────────────────

    def _parse_passage_text(self, passage_text: str, book: str, testament: str, start_chapter: int = 1) -> list[dict]:
        """
        Split ESV API passage text into one dict per verse.
        Handles prose, poetry (Psalms/Proverbs), Selah markers, and multi-chapter passages.
        """
        if not passage_text:
            return []

        parts = re.split(r'\[(\d+)\]', passage_text)
        rows  = []
        i     = 1

        while i < len(parts) - 1:
            verse_num_str = parts[i].strip()
            raw_text      = parts[i + 1]

            verse_text = re.sub(r'[ \t]+', ' ', raw_text)
            verse_text = re.sub(r'\n+', ' ', verse_text)
            verse_text = re.sub(r'\s{2,}[A-Z][A-Z\s,]+$', '', verse_text).strip()

            if verse_num_str.isdigit() and verse_text:
                rows.append({
                    "translation":  "ESV",
                    "testament":    testament,
                    "book":         book,
                    "chapter":      None,
                    "verse_number": int(verse_num_str),
                    "verse_text":   verse_text,
                })
            i += 2

        # Resolve chapter numbers — start from known chapter, increment on verse resets
        if rows:
            chapter = start_chapter
            for idx, row in enumerate(rows):
                if idx > 0 and row["verse_number"] == 1:
                    chapter += 1
                row["chapter"] = chapter

        return rows

    def _parse_chapter_from_ref(self, canonical: str, fallback: str) -> int:
        """Extract starting chapter number from a reference string like 'Exodus 11:1-20'."""
        for ref in (canonical, fallback):
            match = re.search(r'\b(\d+)(?::|$|\s)', ref.split()[-1] if ref.split() else "")
            if not match:
                match = re.search(r'(\d+)(?::\d+)?(?:\s*[-–]\s*\d+(?::\d+)?)?$', ref)
            if match:
                return int(match.group(1))
        return 1

    def _resolve_book_testament(self, canonical: str, fallback: str) -> tuple[str, str]:
        for book_name in self.BOOK_LOOKUP:
            if canonical.startswith(book_name):
                testament, _ = self.BOOK_LOOKUP[book_name]
                return book_name, testament
        for book_name in self.BOOK_LOOKUP:
            if fallback.startswith(book_name):
                testament, _ = self.BOOK_LOOKUP[book_name]
                return book_name, testament
        return "Unknown", "Unknown"

    # ── Private: DataFrame ───────────────────────────────────────

    def _to_df(self, rows: list[dict]) -> pd.DataFrame:
        if not rows:
            return self._empty_df()

        df = pd.DataFrame(rows, columns=[
            "translation", "testament", "book",
            "chapter", "verse_number", "verse_text",
        ])
        df["chapter"]      = df["chapter"].astype("Int16")
        df["verse_number"] = df["verse_number"].astype("Int16")
        df["translation"]  = df["translation"].astype("string")
        df["testament"]    = df["testament"].astype("string")
        df["book"]         = df["book"].astype("string")
        df["verse_text"]   = df["verse_text"].astype("string")

        return df.reset_index(drop=True)

    def _empty_df(self) -> pd.DataFrame:
        return pd.DataFrame(columns=[
            "translation", "testament", "book",
            "chapter", "verse_number", "verse_text"
        ])