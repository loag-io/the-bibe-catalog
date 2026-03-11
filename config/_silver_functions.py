# Initialize project environment
import sys; sys.path.insert(0, next((str(p) for p in __import__('pathlib').Path.cwd().parents if (p/'config').exists()), '.'))

# Import common libraries
from config._common_libraries import *
from config._common_functions import *

class ESVBibleEmbedding:
    """
    Verse-anchored embedding generator for ESV Bible bronze table.

    Reads from MotherDuck bible_catalog, builds a context window of
    3 verses before and after each anchor verse (within book boundaries),
    generates embeddings via Ollama, and returns df for upsert.

    Schema additions to bible_catalog:
        context_text  (str)        : 3 prior + anchor + 3 next verses, one per line
        embedding     (list[float]): 768-dim vector from nomic-embed-text:v1.5

    Usage (Jupyter Notebook):
        embedder = ESVBibleEmbedding(
            database_name = f"ext_{p_env}",
            schema        = "bronze",
            table_name    = "bible_catalog",
            embed_model   = "nomic-embed-text:v1.5",
            reset         = False,   # True = reprocess all verses
        )

        df = embedder.run()

        # Upsert to Motherduck
        upsert_to_motherduck(
            df            = df,
            database_name = p_database,
            schema        = 'silver',
            table_name    = p_table,
            key_columns   = ["translation", "book", "chapter", "verse_number"]
        )
    """

    # ── Config ───────────────────────────────────────────────────
    OLLAMA_URL   = "http://localhost:11434/api/embeddings"
    CONTEXT_SIZE = 3          # verses before and after anchor
    LINE_LEN     = 86
    UPSERT_KEYS  = ["translation", "book", "chapter", "verse_number"]

    # ── Canonical column order ───────────────────────────────────
    # _last_modified_timestamp always last — added by upsert_to_motherduck
    COLUMN_ORDER = [
        "translation",
        "testament",
        "book",
        "chapter",
        "verse_number",
        "verse_text",
        "context_text",
        "embedding",
    ]

    # ── Bible Canon — for canonical sort order ───────────────────
    BIBLE_ORDER = [
        "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
        "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings",
        "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah",
        "Esther", "Job", "Psalms", "Proverbs", "Ecclesiastes",
        "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations",
        "Ezekiel", "Daniel", "Hosea", "Joel", "Amos", "Obadiah",
        "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai",
        "Zechariah", "Malachi", "Matthew", "Mark", "Luke", "John",
        "Acts", "Romans", "1 Corinthians", "2 Corinthians", "Galatians",
        "Ephesians", "Philippians", "Colossians", "1 Thessalonians",
        "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon",
        "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John",
        "3 John", "Jude", "Revelation",
    ]

    # ── Init ─────────────────────────────────────────────────────

    def __init__(
        self,
        database_name : str,
        schema        : str  = "bronze",
        table_name    : str  = "bible_catalog",
        embed_model   : str  = "nomic-embed-text:v1.5",
        reset         : bool = False,
    ):
        if not database_name:
            raise ValueError(
                "database_name is required. "
                "Example: ESVBibleEmbedding(database_name=f\"ext_{p_env}\")"
            )

        self.database_name = database_name
        self.schema        = schema
        self.table_name    = table_name
        self.embed_model   = embed_model
        self.reset         = reset
        self.table_path    = f"{database_name}.{schema}.{table_name}"

    # ── Public ───────────────────────────────────────────────────

    def run(self) -> pd.DataFrame:
        """
        Main entry point. Loads bronze table, builds context windows,
        generates embeddings, returns full df for upsert.

        Returns:
            pd.DataFrame: Full bible_catalog with context_text + embedding columns.
                          _last_modified_timestamp always last if present.
                          Returns empty DataFrame if all verses already processed.
        """

        # ── Step 1: Load ─────────────────────────────────────────
        self._print_section_header("STEP 1: LOAD BIBLE CATALOG")
        full_df = self._load_table()
        print(f"  ✓ Loaded {len(full_df):,} verses from {self.table_path}")

        # ── Step 2: Resolve unprocessed verses ───────────────────
        self._print_section_header("STEP 2: RESOLVE UNPROCESSED VERSES")
        unprocessed_df, mode_label = self._resolve_unprocessed(full_df)

        meta = (
            f"Total: {len(full_df):,} verses  |  "
            f"To process: {len(unprocessed_df):,}  |  "
            f"Mode: {mode_label}"
        )
        print(f"  {meta}")

        if unprocessed_df.empty:
            print(f"  ✓ All verses already embedded — nothing to do")
            print(f"  ✓ Use reset=True to reprocess all verses")
            return pd.DataFrame()

        # ── Step 3: Build context windows ────────────────────────
        self._print_section_header("STEP 3: BUILD CONTEXT WINDOWS")
        full_df = self._build_context_windows(full_df)
        print(f"  ✓ Context windows built ({self.CONTEXT_SIZE} verses before + anchor + {self.CONTEXT_SIZE} after)")

        # Re-align unprocessed with updated context_text
        unprocessed_df = full_df[full_df["_needs_embedding"] == True].copy()

        # ── Step 4: Embed ─────────────────────────────────────────
        self._print_section_header("STEP 4: GENERATE EMBEDDINGS")
        unprocessed_df = self._embed_verses(unprocessed_df)

        # ── Step 5: Merge embeddings back into full_df ────────────
        full_df = self._merge_embeddings(full_df, unprocessed_df)

        # Drop internal helper column
        full_df = full_df.drop(columns=["_needs_embedding"], errors="ignore")

        # Enforce column order — _last_modified_timestamp always last
        full_df = self._enforce_column_order(full_df)

        print(f"\n  ✓ Ready to upsert: {len(full_df):,} verses")

        return full_df

    # ── Private: Data ─────────────────────────────────────────────

    def _load_table(self) -> pd.DataFrame:
        """Load full bible_catalog from MotherDuck in canonical order."""
        book_order_sql = "\n".join(
            f"WHEN '{book}' THEN {idx}"
            for idx, book in enumerate(self.BIBLE_ORDER, 1)
        )

        conn = get_motherduck_connection(self.database_name)
        try:
            df = conn.execute(f"""
                SELECT *
                FROM {self.schema}.{self.table_name}
                ORDER BY
                    CASE book {book_order_sql} END,
                    chapter,
                    verse_number
            """).df()
        finally:
            conn.close()

        return df.reset_index(drop=True)

    def _resolve_unprocessed(self, df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
        """
        Determine which verses need embedding.
        Marks df with internal _needs_embedding column.

        A verse is complete if BOTH context_text and embedding are non-null.
        reset=True marks all verses as needing embedding.
        """
        has_context   = "context_text" in df.columns
        has_embedding = "embedding" in df.columns

        if self.reset or not has_context or not has_embedding:
            df["_needs_embedding"] = True
            mode_label = "RESET — reprocessing all verses" if self.reset else "INITIAL RUN — no embeddings found"
        else:
            is_complete            = df["context_text"].notna() & df["embedding"].notna()
            df["_needs_embedding"] = ~is_complete
            complete_count         = is_complete.sum()
            pending_count          = (~is_complete).sum()

            if pending_count == 0:
                mode_label = f"ALL COMPLETE — {complete_count:,} verses already embedded"
            else:
                mode_label = f"RESUME — {complete_count:,} complete, {pending_count:,} remaining"

        unprocessed_df = df[df["_needs_embedding"] == True].copy()
        return unprocessed_df, mode_label

    def _build_context_windows(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Build context_text for each verse — CONTEXT_SIZE verses before
        and after the anchor, one verse per line. Never crosses book boundaries.
        """
        df      = df.reset_index(drop=True)
        context = []
        n       = len(df)

        for i in range(n):
            anchor_book = df.at[i, "book"]

            # Gather prior verses within same book
            prior = []
            for j in range(i - self.CONTEXT_SIZE, i):
                if j >= 0 and df.at[j, "book"] == anchor_book:
                    prior.append(df.at[j, "verse_text"])

            # Anchor verse
            anchor = df.at[i, "verse_text"]

            # Gather next verses within same book
            nxt = []
            for j in range(i + 1, i + self.CONTEXT_SIZE + 1):
                if j < n and df.at[j, "book"] == anchor_book:
                    nxt.append(df.at[j, "verse_text"])

            context.append("\n".join(prior + [anchor] + nxt))

        df["context_text"] = context
        return df

    def _embed_verses(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate embeddings for all unprocessed verses via Ollama.
        Prints progress every 10%.
        """
        total          = len(df)
        embeddings     = []
        start_time     = time.time()
        next_milestone = 10

        print(f"  Model: {self.embed_model}  |  Verses to embed: {total:,}")
        print(f"{'─' * self.LINE_LEN}")

        for i, row in enumerate(df.itertuples(), 1):
            embedding = self._get_embedding(row.context_text)
            embeddings.append(embedding)

            pct = (i / total) * 100
            if pct >= next_milestone:
                elapsed = time.time() - start_time
                eta     = (elapsed / i) * (total - i)
                print(
                    f"  [{next_milestone:>3}%]  {i:>6,} / {total:,} verses  |  "
                    f"Elapsed: {format_duration(elapsed)}  |  "
                    f"ETA: {format_duration(eta)}"
                )
                next_milestone += 10

        duration        = time.time() - start_time
        df["embedding"] = embeddings

        print(f"{'─' * self.LINE_LEN}")
        print(f"  ✓ Complete: {total:,} verses embedded  |  Duration: {format_duration(duration)}")
        print(f"{'─' * self.LINE_LEN}")

        return df

    def _merge_embeddings(self, full_df: pd.DataFrame, embedded_df: pd.DataFrame) -> pd.DataFrame:
        """
        Merge context_text and embedding from embedded_df back into full_df.
        Preserves existing embeddings for verses that were skipped.
        """
        merge_cols = ["translation", "book", "chapter", "verse_number", "context_text", "embedding"]
        update_df  = embedded_df[merge_cols].copy()

        # Drop old context_text and embedding from full_df if they exist
        full_df = full_df.drop(columns=["context_text", "embedding"], errors="ignore")

        # Merge updated values back in
        full_df = full_df.merge(
            update_df,
            on  = ["translation", "book", "chapter", "verse_number"],
            how = "left"
        )

        return full_df

    def _enforce_column_order(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Reorder columns so that:
        1. Known schema columns come first in COLUMN_ORDER
        2. Any extra columns come next
        3. _last_modified_timestamp is always last if present
        """
        ts_col      = "_last_modified_timestamp"
        known       = [c for c in self.COLUMN_ORDER if c in df.columns]
        extra       = [c for c in df.columns if c not in self.COLUMN_ORDER and c != ts_col]
        trailing    = [ts_col] if ts_col in df.columns else []

        return df[known + extra + trailing]

    # ── Private: Embedding ───────────────────────────────────────

    def _get_embedding(self, text: str) -> list[float]:
        """Call Ollama embeddings endpoint and return vector."""
        resp = requests.post(
            self.OLLAMA_URL,
            json    = {"model": self.embed_model, "prompt": text},
            timeout = 60
        )
        resp.raise_for_status()
        return resp.json()["embedding"]

    # ── Private: Print Helpers ───────────────────────────────────

    def _print_section_header(self, title: str) -> None:
        """Print a lightweight ── section header."""
        section = f"── {title} "
        print(f"\n{section}{'─' * (self.LINE_LEN - len(section))}")