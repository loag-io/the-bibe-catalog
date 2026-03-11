# Initialize project environment
import sys; sys.path.insert(0, next((str(p) for p in __import__('pathlib').Path.cwd().parents if (p/'config').exists()), '.'))

# Import common libraries
from config._common_libraries import *
from config._common_functions import *

class ESVBibleEmbedding:
    """
    Verse-anchored embedding generator for ESV Bible bronze → silver pipeline.

    Reads from MotherDuck bronze.bible_catalog, builds a context window of
    3 verses before and after each anchor verse (within book boundaries),
    generates embeddings via Ollama, and upserts to silver every 10% of progress.

    Resume logic: skips verses whose guid already exists in silver.bible_catalog.

    Schema additions to silver.bible_catalog:
        context_text  (str)        : 3 prior + anchor + 3 next verses, one per line
        embedding     (list[float]): 768-dim vector from nomic-embed-text:v1.5

    Usage (Jupyter Notebook):
        embedder = ESVBibleEmbedding(database_name=f"ext_{p_env}")
        embedder.run(key_columns=["translation", "book", "chapter", "verse_number"])
    """

    # ── Config ───────────────────────────────────────────────────
    OLLAMA_URL   = "http://localhost:11434/api/embeddings"
    CONTEXT_SIZE = 3
    LINE_LEN     = 86
    UPSERT_KEYS  = ["translation", "book", "chapter", "verse_number"]

    # ── Canonical column order ───────────────────────────────────
    COLUMN_ORDER = [
        "guid",
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
        source_schema : str  = "bronze",
        target_schema : str  = "silver",
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
        self.source_schema = source_schema
        self.target_schema = target_schema
        self.table_name    = table_name
        self.embed_model   = embed_model
        self.reset         = reset
        self.source_path   = f"{database_name}.{source_schema}.{table_name}"
        self.target_path   = f"{database_name}.{target_schema}.{table_name}"

    # ── Public ───────────────────────────────────────────────────

    def run(self, key_columns: list = None) -> pd.DataFrame:
        """
        Main entry point. Loads bronze, skips guids already in silver,
        builds context windows, generates embeddings, and upserts to silver
        every 10% of progress.

        Args:
            key_columns (list): Upsert key columns for MotherDuck.
                                Defaults to UPSERT_KEYS if not provided.

        Returns:
            pd.DataFrame: All newly embedded verses. Empty if nothing to process.
        """
        key_columns = key_columns or self.UPSERT_KEYS
        inner_width = self.LINE_LEN - 2

        # ── Start banner ──────────────────────────────────────────
        title   = "ESV BIBLE EMBEDDING"
        sep_len = inner_width - 2 - len(title) - 1
        print(f"\n┌─ {title} {'─' * sep_len}┐")
        print(f"│ {'Source: ' + self.source_path:<{inner_width - 2}} │")
        print(f"│ {'Target: ' + self.target_path:<{inner_width - 2}} │")
        print(f"│ {'Model:  ' + self.embed_model:<{inner_width - 2}} │")
        print(f"└{'─' * inner_width}┘")

        # ── Step 1: Load bronze ───────────────────────────────────
        self._print_section_header("STEP 1: LOAD BRONZE BIBLE CATALOG")
        full_df = self._load_source()
        print(f"  ✓ Loaded {len(full_df):,} verses from {self.source_path}")

        # ── Step 2: Resolve unprocessed verses ───────────────────
        self._print_section_header("STEP 2: RESOLVE UNPROCESSED VERSES")
        full_df, mode_label = self._resolve_unprocessed(full_df)
        unprocessed_df      = full_df[full_df["_needs_embedding"]].copy()

        meta = (
            f"Total: {len(full_df):,} verses  |  "
            f"To process: {len(unprocessed_df):,}  |  "
            f"Mode: {mode_label}"
        )
        print(f"  {meta}")

        if unprocessed_df.empty:
            print(f"  ✓ All verses already in {self.target_path} — nothing to do")
            print(f"  ✓ Use reset=True to reprocess all verses")
            return pd.DataFrame()

        # ── Step 3: Build context windows ────────────────────────
        self._print_section_header("STEP 3: BUILD CONTEXT WINDOWS")
        full_df = self._build_context_windows(full_df)
        print(f"  ✓ Context windows built ({self.CONTEXT_SIZE} verses before + anchor + {self.CONTEXT_SIZE} after)")

        # Re-align unprocessed with updated context_text
        unprocessed_df = full_df[full_df["_needs_embedding"]].copy()

        # ── Step 4: Embed + upsert every 10% ─────────────────────
        self._print_section_header("STEP 4: GENERATE EMBEDDINGS")
        result_df = self._embed_and_upsert(unprocessed_df, key_columns)

        # ── Complete banner ───────────────────────────────────────
        title   = "ESV BIBLE EMBEDDING COMPLETE"
        sep_len = inner_width - 2 - len(title) - 1
        print(f"\n┌─ {title} {'─' * sep_len}┐")
        print(f"│ {'Embedded & upserted: ' + f'{len(result_df):,} verses':<{inner_width - 2}} │")
        print(f"│ {'Target: ' + self.target_path:<{inner_width - 2}} │")
        print(f"└{'─' * inner_width}┘\n")

        return result_df

    # ── Private: Data ─────────────────────────────────────────────

    def _load_source(self) -> pd.DataFrame:
        """Load full bible_catalog from bronze in canonical order."""
        book_order_sql = "\n".join(
            f"WHEN '{book}' THEN {idx}"
            for idx, book in enumerate(self.BIBLE_ORDER, 1)
        )

        conn = get_motherduck_connection(self.database_name)
        try:
            df = conn.execute(f"""
                SELECT *
                FROM {self.source_schema}.{self.table_name}
                ORDER BY
                    CASE book {book_order_sql} END,
                    chapter,
                    verse_number
            """).df()
        finally:
            conn.close()

        return df.reset_index(drop=True)

    def _load_target_guids(self) -> set:
        """Load existing guids from silver — used for resume logic."""
        try:
            conn = get_motherduck_connection(self.database_name)
            try:
                result = conn.execute(f"""
                    SELECT guid
                    FROM {self.target_schema}.{self.table_name}
                """).df()
                return set(result["guid"].tolist())
            finally:
                conn.close()
        except Exception:
            return set()

    def _resolve_unprocessed(self, df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
        """
        Determine which verses need embedding by comparing bronze guids
        against guids already present in silver.
        """
        if self.reset:
            df["_needs_embedding"] = True
            mode_label = "RESET — reprocessing all verses"
        else:
            existing_guids = self._load_target_guids()

            if not existing_guids:
                df["_needs_embedding"] = True
                mode_label = "INITIAL RUN — no existing records in silver"
            else:
                df["_needs_embedding"] = ~df["guid"].isin(existing_guids)
                complete_count = df["guid"].isin(existing_guids).sum()
                pending_count  = df["_needs_embedding"].sum()

                if pending_count == 0:
                    mode_label = f"ALL COMPLETE — {complete_count:,} verses already in silver"
                else:
                    mode_label = f"RESUME — {complete_count:,} complete, {pending_count:,} remaining"

        return df, mode_label

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

            prior = []
            for j in range(i - self.CONTEXT_SIZE, i):
                if j >= 0 and df.at[j, "book"] == anchor_book:
                    prior.append(df.at[j, "verse_text"])

            anchor = df.at[i, "verse_text"]

            nxt = []
            for j in range(i + 1, i + self.CONTEXT_SIZE + 1):
                if j < n and df.at[j, "book"] == anchor_book:
                    nxt.append(df.at[j, "verse_text"])

            context.append("\n".join(prior + [anchor] + nxt))

        df["context_text"] = context
        return df

    def _embed_and_upsert(self, df: pd.DataFrame, key_columns: list) -> pd.DataFrame:
        """
        Generate embeddings for all unprocessed verses via Ollama.
        Upserts to silver every 10% of progress.
        Prints progress in bronze-style format.
        """
        total          = len(df)
        embeddings     = []
        start_time     = time.time()
        next_pct       = 10
        batch_start    = 0   # index of first verse not yet upserted
        total_upserted = 0

        print(f"  Model: {self.embed_model}  |  Verses to embed: {total:,}")
        print(f"{'─' * self.LINE_LEN}")

        for i, row in enumerate(df.itertuples(), 1):
            embedding = self._get_embedding(row.context_text)
            embeddings.append(embedding)

            pct = (i / total) * 100

            if pct >= next_pct or i == total:
                elapsed  = time.time() - start_time
                eta      = (elapsed / i) * (total - i)

                # Upsert the batch accumulated since last milestone
                batch_df             = df.iloc[batch_start:i].copy()
                batch_df["embedding"] = embeddings[batch_start:i]
                batch_df             = self._enforce_column_order(batch_df)
                upsert_to_motherduck(batch_df, self.database_name, self.target_schema, self.table_name, key_columns)
                total_upserted += len(batch_df)
                batch_start     = i

                milestone = int(pct // 10) * 10 if i < total else 100
                print(
                    f"  [{milestone:>3}%]  {i:>6,} / {total:,} verses  |  "
                    f"upserted {len(batch_df):,}  |  "
                    f"Elapsed: {format_duration(elapsed)}  |  "
                    f"ETA: {format_duration(eta)}"
                )
                next_pct = milestone + 10

        duration = time.time() - start_time
        df["embedding"] = embeddings

        print(f"{'─' * self.LINE_LEN}")
        print(
            f"  ✓ Complete: {total:,} verses embedded  |  "
            f"Total upserted: {total_upserted:,}  |  "
            f"Duration: {format_duration(duration)}"
        )
        print(f"{'─' * self.LINE_LEN}")

        return self._enforce_column_order(df)

    def _enforce_column_order(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Reorder columns so that:
        1. Known schema columns come first in COLUMN_ORDER
        2. Any extra columns come next
        3. _last_modified_timestamp is always last if present
        """
        ts_col   = "_last_modified_timestamp"
        known    = [c for c in self.COLUMN_ORDER if c in df.columns]
        extra    = [c for c in df.columns if c not in self.COLUMN_ORDER and c != ts_col and c != "_needs_embedding"]
        trailing = [ts_col] if ts_col in df.columns else []

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