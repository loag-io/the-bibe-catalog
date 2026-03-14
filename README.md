### Biblical GraphRAG: Mapping Multi-Dimensional Scripture Relationships `v 0.1.0`
___

> **Purpose**
>
> A GraphRAG system combining graph databases with AI to automatically discover cross-references across the Bible. Ingests scripture and external resources (sermons, podcasts, articles) using medallion architecture to build a knowledge graph mapping relationships across context, theme, authorship, and literary patterns.

### Contents
- [Overview](#overview)
- [Architecture](#architecture)
  - [Medallion Data Architecture](#medallion-data-architecture)
  - [GraphRAG Pipeline](#graphrag-pipeline)
- [Graph Schema](#graph-schema)
  - [Node Types](#node-types)
  - [Relationship Types](#relationship-types)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Contributing](#contributing)

### Overview

This project leverages **Graph Retrieval-Augmented Generation (GraphRAG)** to create an intelligent knowledge graph of biblical cross-references and relationships. By combining traditional biblical texts with modern AI and graph database technologies, the system can:

*   Automatically discover verse-to-verse cross-references
*   Map multi-dimensional relationships across scripture
*   Integrate insights from sermons, podcasts, articles, and theological books
*   Enable deep exploration of biblical themes, contexts, and patterns

### Architecture

#### Medallion Data Architecture

The system follows a **Bronze → Silver → Gold** medallion architecture:

```
Bronze Layer (Raw Data - DuckDB)
├── Biblical texts (multiple translations)
├── Sermon transcripts
├── Podcast episodes
├── Articles & blog posts
└── Theological books

Silver Layer (Processed Data - DuckDB)
├── Cleaned and normalized texts
├── Embedded vectors for semantic search
├── Initial cross-reference extraction
└── Entity recognition (people, places, events)

Gold Layer (Knowledge Graph - Neo4j)
├── Validated cross-references
├── Multi-dimensional relationships
├── Graph analytics & insights
└── Query-optimized structure
```

#### GraphRAG Pipeline

1. **Ingestion**: Load biblical texts and external resources
2. **Embedding**: Generate vector embeddings for semantic similarity
3. **Entity Extraction**: Identify verses, themes, people, places, events
4. **Relationship Discovery**: Use GenAI to find connections
5. **Graph Construction**: Build nodes and edges in graph database
6. **Validation**: Human-in-the-loop validation of AI-discovered relationships
7. **Enrichment**: Continuously improve with new sources

### Graph Schema

#### Node Types

*   **Verse**: Individual Bible verses
*   **Chapter**: Bible chapters
*   **Book**: Bible books
*   **Theme**: Theological themes (salvation, justice, mercy, etc.)
*   **Person**: Biblical characters
*   **Place**: Geographical locations
*   **Event**: Historical events
*   **Author**: Biblical authors
*   **LiteraryDevice**: Metaphors, parables, prophecies, etc.
*   **ExternalResource**: Sermons, articles, podcasts

#### Relationship Types

*   **CROSS_REFERENCES**: Direct verse-to-verse connections
*   **THEMATIC_LINK**: Shared themes or concepts
*   **CONTEXTUAL_SIMILARITY**: Similar historical/cultural context
*   **LITERARY_PATTERN**: Similar style, genre, or device
*   **AUTHORSHIP**: Written by same author
*   **FULFILLMENT**: Prophecy → fulfillment connections
*   **ALLUSION**: Literary references
*   **PARALLEL_PASSAGE**: Synoptic gospels, parallel accounts
*   **QUOTES**: OT → NT quotations
*   **COMMENTARY**: External resource → verse insights

### Technology Stack

*   **Graph Database (Gold Layer)**: Neo4j
*   **Relational Database (Bronze/Silver Layers)**: DuckDB
*   **Vector Database**: DuckDB
*   **LLM Framework**: LangChain / LlamaIndex / LangGraph
*   **AI Models**: Llama / Qwen
*   **Data Processing**: Python, Pandas
*   **Orchestration**: Jupytere Scheduler
*   **API Layer**: FastAPI / GraphQL

### Project Structure

```
the-bible-catalog/
├── config/             # Configuration files
│   └── .env            # Environment variables (locally stored)
├── database/
│   └── setup/          # Database setup scripts and notebooks
├── docs/               # Documentation
├── notebooks/          # Jupyter notebooks
└── tests/              # Unit tests
```

### Contributing

Contributions are welcome as the project develops. Areas for future contribution:

*   Data source integration
*   Cross-reference validation
*   Graph query optimization
*   Documentation
*   Testing

___

**Note**: This is a research and educational project. Cross-references and relationships are AI-assisted and should be validated by theological experts for scholarly or ministerial use.
