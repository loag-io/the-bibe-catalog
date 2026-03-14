### Biblical GraphRAG: Mapping Multi-Dimensional Scripture Relationships `v 0.1.0`
___

> **Purpose**
>
> A GraphRAG system combining graph databases with AI to automatically discover cross-references across the Bible. Ingests scripture and external resources (sermons, podcasts, articles) using medallion architecture to build a knowledge graph mapping relationships across context, theme, authorship, and literary patterns.

### Contents
- [Overview](#overview)
- [Getting Started](#getting-started)
- [Architecture](#architecture)
  - [Medallion Data Architecture](#medallion-data-architecture)
  - [GraphRAG Pipeline](#graphrag-pipeline)
- [Semantic Graph Ontology](#semantic-graph-ontology)
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


### Getting Started

For full setup instructions, see the [Setup Guide](docs/guides/setup.md). It covers:

- Environment configuration and dependencies
- Python 3.12 virtual environment setup
- JupyterLab installation and kernel registration
- Environment variable configuration
- Troubleshooting common issues

### Architecture

#### Medallion Data Architecture

The system follows a **Bronze → Silver → Gold** medallion architecture:

![Screenshot](docs/assets/graphrag-medallion-architecture.svg)

This system organizes data processing into three progressive layers, each building on the last.

*`Bronze`* is the raw ingestion layer. Source documents arrive here unchanged — PDFs, web pages, youtube/podcast/database exports, API responses. It's the immutable source of truth; nothing is transformed or discarded.

*`Silver`* is where structure emerges. Text is chunked, and an extraction pipeline identifies node(s), label(s), relationship(s) and properties. These will then be used in the knowledge graph, turning unstructured content into something traversable and queryable.

*`Gold`* is the query-ready layer. The graph is enriched with vector embeddings on nodes and their surrounding context. Retrieval at this layer combines semantic similarity search with explicit graph traversal — enabling multi-hop reasoning across connected facts that flat vector search alone cannot handle.

The critical distinction from standard RAG happens at the Silver→Gold boundary: instead of indexing isolated text chunks, you're indexing a *graph*. Queries can follow chains of relationships, not just match similar passages.

#### GraphRAG Pipeline

1. **Ingestion**: Load biblical texts and external resources into the Bronze layer
2. **Entity Extraction**: Identify verses, themes, people, places, and events
3. **Relationship Discovery**: Use GenAI to surface connections between entities
4. **Graph Construction**: Promote structured nodes and edges into the Silver layer
5. **Embedding**: Generate vector embeddings and index the graph into Gold
6. **Validation**: Human-in-the-loop review of AI-discovered relationships
7. **Enrichment**: Continuously ingest new sources and re-run the pipeline

### Semantic Graph Ontology

This ontology defines the semantic model for the Gold layer knowledge graph. **Nodes** are the core entities (verses, people, places, etc.). **Labels** are categories applied to nodes to group and classify them by type — a node can carry multiple labels where roles overlap (e.g. a `Person` who is also an `Author`). **Relationships** are the directed edges connecting nodes, each with a required type that describes the nature of the connection. **Properties** are key-value attributes attached to both nodes and relationships to carry additional detail — identifiers, scores, flags, and metadata. They describe entities and connections further but are not structural entry points into the graph.

#### Node Types

| Label | Represents | Key Properties |
|---|---|---|
| `Verse` | Individual Bible verses | `reference`, `text`, `translation`, `book`, `chapter`, `verse_num` |
| `Chapter` | Bible chapters | `number`, `book`, `summary` |
| `Book` | Bible books | `name`, `testament`, `genre`, `canonical_order` |
| `Theme` | Theological themes | `name`, `description`, `category` |
| `Person` | Biblical characters | `name`, `aliases`, `testament`, `role` |
| `Place` | Geographical locations | `name`, `modern_name`, `region`, `coordinates` |
| `Event` | Historical events | `name`, `period`, `description` |
| `Author` | Biblical authors | `name`, `testament`, `tradition` |
| `LiteraryDevice` | Metaphors, parables, prophecies | `type`, `description` |
| `ExternalResource` | Sermons, articles, podcasts | `title`, `url`, `source`, `type`, `date` |

#### Relationship Types

All relationships have a type and a direction — never assumed bi-directional. Properties on relationships capture confidence scores and metadata, which is critical for tracking and validating AI-discovered connections.

| Type | Direction | Key Properties |
|---|---|---|
| `CROSS_REFERENCES` | `Verse` → `Verse` | `confidence`, `source` |
| `THEMATIC_LINK` | `Verse/Book` → `Theme` | `confidence`, `relevance_score` |
| `CONTEXTUAL_SIMILARITY` | `Verse` → `Verse` | `context_type`, `confidence` |
| `LITERARY_PATTERN` | `Verse` → `LiteraryDevice` | `pattern_type`, `confidence` |
| `AUTHORED_BY` | `Book` → `Author` | `tradition`, `disputed` |
| `FULFILLMENT` | `Verse` → `Verse` | `fulfillment_type`, `confidence` |
| `ALLUSION` | `Verse` → `Verse` | `allusion_type`, `confidence` |
| `PARALLEL_PASSAGE` | `Verse` → `Verse` | `gospel`, `deviation_notes` |
| `QUOTES` | `Verse` → `Verse` | `quote_type`, `verbatim` |
| `COMMENTARY` | `ExternalResource` → `Verse` | `insight_type`, `validated` |

> **Validation flag**: AI-discovered relationships carry a `confidence` score and a `validated: boolean` property, supporting the human-in-the-loop review step in the pipeline.

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

> **NOTE**: This is a research and educational project. Cross-references and relationships are AI-assisted and should be validated by theological experts for scholarly or ministerial use.
