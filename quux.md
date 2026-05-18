# Typed graphs as Python base classes

**Created:** 5/18/2026 11:25:49  
**Updated:** 5/18/2026 13:06:30  
**Exported:** 5/18/2026 14:40:56  
**Link:** [https://claude.ai/chat/a4bc8978-a4e3-4d9e-8101-60f085a92497](https://claude.ai/chat/a4bc8978-a4e3-4d9e-8101-60f085a92497)  

## Prompt:
5/18/2026, 11:25:49 AM

This chat builds on https://claude.ai/chat/caa90ff3-8466-4ae1-ad02-4fb7a65b782c but heads in a slightly different direction. I just dealt with a bug at work where the code got WAY simpler when I defined some pretty simple types to define the terms of the problem space. It was a very big win. And it got me thinking about typed graphs.

Let's suppose we think of typed graphs as fundamentally a Python data structure with all the conveniences Python provides (in particular Pydantic, frozen things, ruff and mypy). Then we could define a sort of "typed graph base class" where the things that make it a typed graph are baked in, but a particular schema (medical, Holmes, whatever) could extend those things to support that problem domain. And you still get the predicate validation and a lot of the mechanics as inherited from the "base class". I had started doing that with the kgraph-vs-medlit distinction. I think being more conscious about it might be a win.

Of course I say that while working on the new sherlock ingestion stuff which does not inherit from kgraph and so I guess I've been unnecessarily rebuilding a bunch of that stuff, or just missing it entirely.



## Response:
5/18/2026, 11:26:32 AM



````plaintext
Thought process: Architected generic typed graph base class to eliminate schema duplication.

Will is reflecting on a design insight: defining a typed graph base class in Python/Pydantic that captures the fundamental typed graph mechanics, while allowing domain-specific schemas (Holmes, medical, industrial) to extend it. This connects to his Book 3 formal definition and the kgraph/medlit architecture.

Let me think about what this would actually look like and what the key design points are.

The core insight is:
1. There's a generic typed graph structure (nodes, edges, type vocabularies, predicates/traits)
2. Domain schemas extend this with domain-specific node types, edge types, trait definitions
3. You get predicate validation and traversal mechanics "for free" from the base


4. The 7-tuple formalization maps directly to Pydantic classes: vertex and edge type vocabularies become enums or constrained types, the typing functions become field validators, and the actual vertices and edges become model instances that reference their types.

Now I'm mapping the formal structure onto concrete Python classes—base `TypedNode` and `TypedEdge` models that enforce the typing constraints, with domain-specific subclasses layering on their own vocabularies and validation rules.

The real friction points are reconciling Python's static type system with the graph's runtime type system, keeping nodes and edges immutable as value objects while the graph container itself remains mutable, and recognizing that his existing kgraph code already embodies this pattern but could be more explicit about it. The sherlock ingestion pipeline he's building from scratch is essentially reinventing what kgraph already provides—that's where the refactoring opportunity lies.

Defining the base architecture... I'm defining the validation methods for edges within the schema, then setting up a mutable graph container that holds frozen node and edge objects while enforcing schema constraints. After that, I'm creating a concrete Holmes domain schema with specific node types like characters, locations, objects, and events, along with edge types that define relationships between them like "knows," "located_at," and "possesses."

The real architectural insight here is that all the core traversal logic, validation, and ingestion machinery lives in the base layer—Holmes just needs to provide its schema definition, which mirrors how clear type definitions clarified the problem space in the original work.
````

This is a really clean insight, and it maps directly onto the 7-tuple you formalized for Book 3. The formal definition *is* the base class — you've just been expressing it informally in kgraph rather than as an explicit inheritable structure.

Let me sketch what I think the layering looks like:

---

**The three levels**

```
TypedGraph (base layer)
  — node/edge value objects with typed IDs
  — GraphSchema: frozen declaration of (T_V, T_E, Φ, valid_predicates)
  — validation: does this edge type make sense between these node types?
  — traversal mechanics: BFS, neighbor lookup, reachability
  — ingestion pipeline scaffold: fetch → extract → ingest stages

HolmesSchema(TypedGraph base)           MedlitSchema(TypedGraph base)
  — HolmesNodeType(StrEnum)               — MedlitNodeType(StrEnum)
  — HolmesEdgeType(StrEnum)               — MedlitEdgeType(StrEnum)
  — HOLMES_SCHEMA = GraphSchema(...)      — MEDLIT_SCHEMA = GraphSchema(...)
  — HolmesNode(TypedNode)                 — entity authority routing
  — provisional ID mechanics              — UMLS/HGNC/RxNorm lookup
```

The frozen Pydantic rule fits cleanly here: nodes and edges are frozen value objects; the *graph container* is a mutable dict-of-dicts (or Postgres rows), which is appropriate since it's infrastructure, not domain logic.

---

**What a GraphSchema actually looks like**

```python
from pydantic import BaseModel, model_validator
from typing import FrozenSet, Tuple

Predicate = Tuple[str, str, str]  # (src_node_type, edge_type, tgt_node_type)

class GraphSchema(BaseModel, frozen=True):
    name: str
    node_types: FrozenSet[str]
    edge_types: FrozenSet[str]
    trait_keys: FrozenSet[str]
    valid_predicates: FrozenSet[Predicate]

    @model_validator(mode="after")
    def predicates_reference_declared_types(self) -> "GraphSchema":
        for src, rel, tgt in self.valid_predicates:
            assert src in self.node_types, f"Unknown src type: {src}"
            assert rel in self.edge_types,  f"Unknown edge type: {rel}"
            assert tgt in self.node_types, f"Unknown tgt type: {tgt}"
        return self

    def allows(self, src_type: str, edge_type: str, tgt_type: str) -> bool:
        return (src_type, edge_type, tgt_type) in self.valid_predicates
```

Then a domain file is almost declarative:

```python
class HolmesNodeType(StrEnum):
    CHARACTER = "character"
    LOCATION  = "location"
    OBJECT    = "object"
    CASE      = "case"

class HolmesEdgeType(StrEnum):
    KNOWS        = "knows"
    LOCATED_AT   = "located_at"
    APPEARED_IN  = "appeared_in"
    POSSESSES    = "possesses"

HOLMES_SCHEMA = GraphSchema(
    name="holmes",
    node_types=frozenset(HolmesNodeType),
    edge_types=frozenset(HolmesEdgeType),
    trait_keys=frozenset({"confidence", "story_ref", "provisional"}),
    valid_predicates=frozenset({
        ("character", "knows",       "character"),
        ("character", "located_at",  "location"),
        ("character", "appeared_in", "case"),
        ("character", "possesses",   "object"),
        ("object",    "appeared_in", "case"),
        ("location",  "appeared_in", "case"),
    }),
)
```

mypy sees `HolmesNodeType` as a proper `StrEnum` so you get autocomplete and exhaustiveness checking; the schema instance validates itself at construction time.

---

**What this costs you in the sherlock work**

The sherlock ingestion pipeline you've been building is essentially reimplementing:
- provisional ID generation (already in kgraph's `IdentityServer`)
- deduplication/canonicalization logic
- entity record structures

The cleanest path forward is probably: define `HOLMES_SCHEMA` as above, then write a thin `HolmesIngester` that subclasses or composes kgraph's pipeline scaffold, passing `HOLMES_SCHEMA` where medlit currently hardcodes its type assumptions. The extraction prompts and spaCy segmentation are domain-specific, but the queue/stage/dedup mechanics aren't.

---

**The Book 3 angle**

This is actually a better worked example for the book than the abstract 7-tuple — you can *show* the 7-tuple as a Pydantic class and then demonstrate that `HOLMES_SCHEMA` is a literal instance of it. The formal definition and the running code are the same thing. That's a much stronger pedagogical move than keeping them separate.

Worth being explicit about one thing: `GraphSchema` is the *schema layer*, `TypedNode`/`TypedEdge` instances are the *instance layer* — which directly maps to your earlier decision that traits belong in the schema, not the instance. The `trait_keys` frozenset in `GraphSchema` declares what traits are *legal*; trait *values* live on individual nodes.

Is the immediate practical question "how do I retrofit the Holmes pipeline to use this structure without blowing up what I've already written"?



## Prompt:
5/18/2026, 11:29:01 AM

```
class HolmesNodeType(StrEnum):
    CHARACTER = "character"
    LOCATION  = "location"
    OBJECT    = "object"
    CASE      = "case"
```

Should this inherit from some kind of base Node type which would itself inherit from StrEnum? And likewise the edge type. As far as an immediate practical question, I'll get to rewriting the Holmes pipeline but first I want to clarify this stuff in my head, which seems to be a winning strategy.



## Response:
5/18/2026, 11:29:26 AM



````plaintext
Thought process: Examined inheritance patterns and type safety benefits of base enum approach.

Will is asking about whether `HolmesNodeType` should inherit from a base `NodeType(StrEnum)` rather than directly from `StrEnum`. This is a good design question.

The key considerations:

1. **Does Python's StrEnum support multi-level inheritance well?** Actually, `StrEnum` is tricky with inheritance. You can't add members to an existing enum subclass. So `class HolmesNodeType(NodeType)` would fail if `NodeType` already has members. But if `NodeType` has *no* members (it's just a marker/base), then subclassing works fine.


2. **What a base `NodeType(StrEnum)` with no members gives you:** You get better type annotations—declaring `node_type: NodeType` lets you accept any domain's node type, mypy can verify you're passing actual `NodeType` subclasses rather than arbitrary strings, and you can write functions that accept `type[NodeType]` to work with any node type enum. Without this base class, if `TypedNode` just declares `node_type: str`, you lose all that type safety.

3. **The isinstance angle:** You can check `isinstance(HolmesNodeType.CHARACTER, NodeType)` and it returns True, which is useful for runtime validation.

4. **A stronger alternative:** You could make `TypedNode` generic over the node type itself—something like `TypedNode[NT: NodeType]` with `node_type: NT`—which gives you even tighter typing guarantees.

5. **Why the inheritance works:** Python's enum rules normally prevent subclassing an enum with members, but an empty base enum like `NodeType` can be freely subclassed, so `HolmesNodeType` can inherit from it and add its own members without issues.

The real payoff is using these base enums as type markers. You'd define `NodeType` and `EdgeType` as empty StrEnum bases, then have `TypedNode` and `TypedEdge` accept those base types in their fields. For `GraphSchema`, instead of storing frozensets of strings, you'd store the actual enum class itself—`node_type_enum: type[NodeType]`—which is cleaner and more type-safe.

I could go full generic with TypeVars bound to these bases, but that's probably overcomplicating things. The simpler marker enum pattern gives you isinstance checks, mypy type narrowing, and clear intent without the extra complexity. Plus, `GraphSchema` storing the enum class directly means you get the frozenset of valid values for free by just iterating the enum.
````

Yes, and it buys you more than just organization. The key property of Python enums is that **you can only subclass an enum if the parent has no members** — which means an empty base enum is exactly the right pattern for a marker type:

```python
class NodeType(StrEnum):
    """Abstract base — no members. Domain schemas subclass this."""
    pass

class EdgeType(StrEnum):
    pass

class HolmesNodeType(NodeType):
    CHARACTER = "character"
    LOCATION  = "location"
    OBJECT    = "object"
    CASE      = "case"
```

What this gets you:

**`isinstance` works as you'd expect:**
```python
isinstance(HolmesNodeType.CHARACTER, NodeType)  # True
isinstance(HolmesNodeType.CHARACTER, EdgeType)  # False — caught at runtime
```

**mypy can check the distinction between node and edge types:**
```python
class TypedNode(BaseModel, frozen=True):
    node_type: NodeType   # accepts any NodeType subclass, rejects EdgeType
    
class TypedEdge(BaseModel, frozen=True):
    edge_type: EdgeType   # symmetric
```

Without the base, both fields are typed `StrEnum` and mypy can't distinguish them — you could accidentally pass a `HolmesEdgeType` where a node type is expected.

**`GraphSchema` can store the enum class itself, not a frozenset of strings:**
```python
class GraphSchema(BaseModel, frozen=True):
    node_type_enum: type[NodeType]
    edge_type_enum: type[EdgeType]
    ...
    
    # valid values are just the enum members — no separate frozenset needed
    @property
    def node_types(self) -> frozenset[str]:
        return frozenset(self.node_type_enum)
```

Storing `type[NodeType]` is richer than storing `frozenset[str]` because you can do things like `self.node_type_enum(some_string)` for validation with a proper `ValueError`, and the enum class itself carries documentation, iteration order, and membership testing.

The one thing to be aware of: mypy's handling of `type[SomeEnum]` as a field in a Pydantic model can get fussy — you may need `arbitrary_types_allowed = True` in the model config, since enum metaclasses aren't standard Pydantic types. Worth a quick check before committing to that field signature.



## Prompt:
5/18/2026, 11:40:09 AM

I would expect that we'll want to add fields in some cases. Like medical predicates tend to have a lot of properties involving provenance, evidence, etc. Would that fit into this way of doing things? Maybe show an example of what it looks like?



## Response:
5/18/2026, 11:40:32 AM



````plaintext
Thought process: Architected domain-specific edge subclasses for enriched graph metadata.

Will is asking about enriching edges (predicates) with domain-specific fields — like provenance, evidence strength, citation info for medical graphs. This is a classic challenge in typed graph design: the edge type isn't just a label, it's a typed structure with its own fields.

The approach that fits cleanly with Pydantic + frozen models:

**Option 1: Traits as a frozenset of key-value pairs** (what was sketched before)
- Generic but loses type safety on the values
- `traits: frozenset[tuple[str, Any]]` — mypy can't help you
  
**Option 2: Domain-specific edge subclasses** — I'm defining subclasses like MedlitEdge that inherit from a base TypedEdge and add their own typed fields for provenance, evidence level, and citation info. This gives full mypy and Pydantic validation, plus discriminated unions handle mixed edge types cleanly.

**Option 3: Generic TypedEdge with a typed payload** — I'm using a generic parameter to wrap domain-specific data inside the edge, keeping the base structure flexible while maintaining type safety on the payload.

Option 2 feels like the right call here.

Now I'm thinking through what medical predicates actually need — things like evidence strength, source citations, confidence scores, directionality, contextual details like tissue or cell type, and whether the assertion is direct or inferred. I'm sketching out an EvidenceLevel enum with categories like strong, moderate, weak, and inferred, then building out a MedlitEdge class with fields for PMID, evidence level, confidence score, and assertion type.

Defining edge classes...

The pattern is becoming clearer — the base TypedEdge handles structural concerns like IDs and edge types, while domain-specific edges layer on their semantic metadata. A Holmes story edge would just need a story reference and sentence index, which is much simpler than the medical case. The schema itself could store a reference to the appropriate edge class so the ingestion pipeline knows which class to instantiate. The same approach works for nodes too — a MedlitNode would carry mesh IDs and UMLS identifiers.
````

Yes, cleanly. The base class carries structural fields; domain subclasses add semantic ones. Pydantic inheritance with `frozen=True` works fine here.

```python
# ---- base ----

class TypedEdge(BaseModel, frozen=True):
    id: str
    edge_type: EdgeType
    source_id: str
    target_id: str


# ---- medlit extension ----

class EvidenceLevel(StrEnum):
    STRONG   = "strong"
    MODERATE = "moderate"
    WEAK     = "weak"
    INFERRED = "inferred"

class AssertionType(StrEnum):
    DIRECT   = "direct"
    CURATED  = "curated"
    COMPUTED = "computed"

class MedlitEdge(TypedEdge):
    evidence_level: EvidenceLevel = EvidenceLevel.INFERRED
    assertion_type: AssertionType = AssertionType.DIRECT
    pmid: str | None = None
    confidence: float = 0.0
    # tissue/cell context for pathway edges
    context: str | None = None


# ---- holmes extension (much simpler) ----

class HolmesEdge(TypedEdge):
    story_ref: str | None = None   # e.g. "SCAN", "REDH"
    sentence_idx: int | None = None
    provisional: bool = False
```

Same pattern applies to nodes — `MedlitNode` would carry `umls_cui`, `mesh_id`, `hgnc_id` depending on entity type; `HolmesNode` carries `canonical_name`, `aliases`, `first_appearance`.

The `GraphSchema` then naturally stores the concrete classes, not just the enums:

```python
class GraphSchema(BaseModel, frozen=True):
    name: str
    node_type_enum: type[NodeType]
    edge_type_enum: type[EdgeType]
    node_class: type[TypedNode]
    edge_class: type[TypedEdge]
    valid_predicates: frozenset[tuple[str, str, str]]

    model_config = ConfigDict(arbitrary_types_allowed=True)
```

So the ingestion pipeline can do `schema.edge_class(id=..., edge_type=..., pmid=..., ...)` and get the right concrete type back without any conditionals. The pipeline itself stays generic; domain specificity is fully captured in the schema object.

One thing worth noting: if you ever need to handle *mixed* edge types in a single collection (say, a list that might contain both `MedlitEdge` and `TypedEdge`), Pydantic's discriminated unions on `edge_type` handle that well. But for the common case where a given graph has one edge class throughout, what's above is sufficient and much simpler.



## Prompt:
5/18/2026, 12:59:53 PM

Are you able to read this git repo? This is the new sherlock stuff that doesn't make use of the existing kgraph: https://github.com/wware/sherlock



## Response:
5/18/2026, 1:00:13 PM



````plaintext
Thought process: Thinking about analyzing a GitHub repository's code structure and functionality.

Let me try to fetch the GitHub repo.
````

````plaintext
Web Fetch: Fetched: GitHub - wware/sherlock: Build a "Scandal in Bohemia" typed graph
````

Let me pull the actual scripts:

````plaintext
Web Fetch: Failed to fetch: https://raw.githubusercontent.com/wware/sherlock/main/scripts/04_ner.py
````

````plaintext
Web Fetch: Failed to fetch: https://github.com/wware/sherlock/blob/main/scripts/04_ner.py
````

````plaintext
Thought process: Attempting to fetch individual file URLs from repository.

The fetch tool requires URLs to have been provided by the user or appeared in search/fetch results. The user provided the GitHub repo URL, and I fetched that page. But the individual file URLs (raw.githubusercontent.com) weren't in the results. Let me try fetching the raw content via the API endpoint that would have been referenced.

Actually wait - the user explicitly provided `https://github.com/wware/sherlock` and I fetched it. But the individual file URLs are different domains/paths. Let me try to see if there's another way to access them. Maybe I can use the GitHub API.
 
The raw.githubusercontent.com URLs weren't showing up in the initial fetch results. Let me try the GitHub tree API instead, which should give me access to the file contents directly.
````

````plaintext
Web Fetch: Failed to fetch: https://github.com/wware/sherlock/tree/main/scripts
````

````plaintext
Web Fetch: Failed to fetch: https://api.github.com/repos/wware/sherlock/contents/scripts
````

````plaintext
Thought process: Encountered fetch limitations, pivoted toward alternative retrieval strategies.

The fetch tool has restrictions. The user-provided URL was `https://github.com/wware/sherlock` and I fetched that. But I can't reach the raw file content or the API. Let me try using web_search to find the raw file URLs, which would then allow me to fetch them.

Actually, the smarter thing is to use `web_search` to search for the file content, which might return raw URLs as results that I can then fetch.

Or actually, let me just tell Will what I can see from the repo structure and ask him to share the key files directly, or paste them in.
````

I can see the repo structure and README but can't reach the individual file contents directly — the fetch tool's permissions don't extend to raw file URLs that weren't in the original page. The directory listing got blocked by robots.txt too.

Could you either paste the key scripts here, or do `cat scripts/*.py` and drop the output in? The most relevant ones are probably `05_mention_store.py`, `06_identity.py`, and `08_parse_relationships.py` — those are where the data model decisions will be most visible. The 10-stage structure itself is already clear from the README.



## Prompt:
5/18/2026, 1:01:31 PM

See if this helps: https://github.com/wware/sherlock/archive/refs/tags/preliminary-20260518.zip



## Response:
5/18/2026, 1:01:45 PM



````plaintext
Thought process: Evaluated resource accessibility and proceeded with retrieval.

The user provided a zip file URL. Let me try to fetch it - it was provided by the user so it should be allowed.
````

````plaintext
Bash Tool: Download and extract the sherlock repo zip
````

````plaintext
Bash Tool: See what was actually returned
````

````plaintext
Thought process: Identified network restriction blocking GitHub downloads, contemplated alternative solutions.

The domain `objects.githubusercontent.com` (where GitHub zip downloads come from) isn't in the allowlist. The network configuration only allows certain domains, and GitHub's release/archive CDN isn't in it.

I should tell Will the issue and suggest alternatives - maybe he can paste the files directly, or use a different approach.
````

The zip redirects to `objects.githubusercontent.com` for the actual download, and that domain isn't in my network allowlist. Same wall as before, different door.

The simplest workaround: paste the scripts directly into chat. Given the pipeline, the highest-value files for our conversation are probably:

- `05_mention_store.py` — where entity records get created
- `06_identity.py` — canonicalization/dedup logic
- `08_parse_relationships.py` — where typed triples get constructed

Those three will show what data structures you're actually using and where the gaps are relative to the base class design we've been sketching. The others (sentencize, chunk, NER, validate) are likely thin enough that the patterns will be obvious once we see the core three.



## Prompt:
5/18/2026, 1:02:45 PM

> File: sherlock-preliminary-20260518.zip

Better?



## Response:
5/18/2026, 1:03:25 PM



````plaintext
Thought process: Thinking about clarifying what needs improvement.

The user uploaded the zip file directly. Let me read the file-reading skill first, then extract and examine the contents.
````

````plaintext
Bash Tool: Extract and list all files
````

````plaintext
Bash Tool: Read the core data model scripts
````

````plaintext
Bash Tool: Read remaining scripts
````

````plaintext
Thought process: Analyzed codebase structure and identified typing improvements needed.

Now I have a good picture of the codebase. Let me analyze what's there and what's missing relative to the typed graph base class design.

Key observations:

1. **`RelationshipCandidate` in `08_parse_relationships.py`** - This is actually a pretty well-designed Pydantic model with `frozen=True`. It's essentially a typed edge with extra fields. But it doesn't inherit from anything - it's standalone.

2. **`06_identity.py`** - The identity resolution is all procedural dict-based. `IDENTITY_MAP`, `ENTITY_META`, `TYPE_PREFIX` are all module-level dicts. 

3. **`09_validate.py`** - The `SCHEMA` dict is essentially `valid_predicates` but expressed as domain/range sets per predicate rather than as a frozenset of triples. This is the same information as `GraphSchema.valid_predicates` but in a different structure.

4. **`05_mention_store.py`** - Purely procedural, no types at all. Mentions are dicts throughout.

5. **No shared types module** - Each script is standalone with data flowing as JSONL between them, and there aren't any Pydantic models for entities either—they're just dicts written to JSONL files.

The pipeline is missing the formal type system from the typed graph base: no `TypedNode` or entity models, no enums for node and edge types, and the validation logic in `09_validate.py` is manually reimplementing what `GraphSchema.allows()` would handle. The identity and entity metadata scattered across `06_identity.py` should be consolidated into a shared schema definition. The good news is the pipeline logic itself is solid and well-structured—it just needs the data model formalized into shared Pydantic types.

I'd create a dedicated types module with `HolmesNodeType` and `HolmesEdgeType` enums, proper `Mention` and `Entity` models, and a `HOLMES_SCHEMA` that incorporates the validation rules currently hardcoded in `09_validate.py`. The set-based domain/range pattern in that validation dict is actually more flexible than enumerating all valid (source, edge, target) triples, so it's worth keeping that approach when formalizing the schema.
````

Good picture now. Here's what I see:

**What's already solid**
- `RelationshipCandidate` in `08` is well-designed — frozen Pydantic, field validators, model validators, the works. It's essentially already a `TypedEdge` in all but name and lineage.
- `llm_json.py` is clean and reusable as-is.
- The pipeline stage separation is good.

**What's missing relative to the base class design**

The biggest gap is that there are no shared types — every script operates on raw dicts flowing through JSONL. Specifically:

- **No `Entity` model.** In `06_identity.py`, entities are assembled as dicts from `ENTITY_META` and written to JSONL. A `HolmesNode(TypedNode)` with `canonical_id`, `name`, `node_type`, `wiki` as proper fields would replace all that.

- **The schema is split across two files.** `IDENTITY_MAP`/`TYPE_PREFIX` in `06` and the `SCHEMA` dict in `09` are together expressing what a single `HOLMES_SCHEMA = GraphSchema(...)` would contain. Right now they can drift out of sync — a new predicate added in `08` but not in `09`'s SCHEMA, for instance.

- **`SCHEMA` in `09` uses a domain/range-sets-per-predicate structure** rather than a frozenset of triples. That's actually a fine alternative encoding — more compact when a predicate has many valid src/tgt types. Worth deciding which form goes into `GraphSchema`.

- **`RelationshipCandidate` isn't connected to the schema.** It validates predicate names against `KNOWN_PREDICATES`, but not domain/range — that check lives separately in `09_validate.py`. If both lived in a `HolmesEdge` that knew about `HOLMES_SCHEMA`, you'd get full validation in one place at parse time.

**The concrete fix**

A single `schema.py` in the repo that everything imports:

```python
# schema.py

class HolmesNodeType(NodeType):
    PERSON       = "person"
    LOCATION     = "location"
    OBJECT       = "object"
    DOCUMENT     = "document"
    DISGUISE     = "disguise"
    ORGANISATION = "organisation"
    MOMENT       = "moment"

class HolmesEdgeType(EdgeType):
    LOCATED_AT   = "located_at"
    KNOWS_AT     = "knows_at"
    POSSESSES    = "possesses"
    DISGUISED_AS = "disguised_as"
    AUTHORED     = "authored"
    CONTAINS     = "contains"
    MARRIED_TO   = "married_to"
    EMPLOYED_BY  = "employed_by"

class HolmesNode(TypedNode):
    name: str
    wiki: str | None = None
    provisional: bool = False

HOLMES_SCHEMA = GraphSchema(
    name="holmes",
    node_type_enum=HolmesNodeType,
    edge_type_enum=HolmesEdgeType,
    valid_predicates=frozenset({
        ("person",   "located_at",   "location"),
        ("object",   "located_at",   "location"),
        ("person",   "knows_at",     "person"),
        ("person",   "possesses",    "object"),
        ("person",   "disguised_as", "disguise"),
        ("person",   "authored",     "document"),
        ("location", "contains",     "object"),
        ("person",   "married_to",   "person"),
        ("person",   "employed_by",  "person"),
        ("person",   "employed_by",  "organisation"),
    }),
)
```

Then `RelationshipCandidate` imports `HOLMES_SCHEMA` and its `predicate_must_be_known` validator becomes `HOLMES_SCHEMA.allows(subject_prefix, predicate, object_prefix)`. The `SCHEMA` dict in `09_validate.py` goes away entirely — it's just `HOLMES_SCHEMA.valid_predicates`. And `06_identity.py`'s `TYPE_PREFIX` dict is replaced by `HolmesNodeType`.

The pipeline scripts themselves barely change — they just import from `schema.py` instead of carrying their own type knowledge.



## Prompt:
5/18/2026, 1:05:30 PM

> File: kgraph-20260423_1350.zip

Next I'd like to show you what's in kgraph. I think there's stuff here that could help to form the "typed graph base class" (or maybe "base layer" or "base package") that I talked about above.



## Response:
5/18/2026, 1:06:30 PM



````plaintext
Thought process: Examined kgraph codebase for foundational typed graph architecture.

Let me extract and examine the kgraph codebase.
````

````plaintext
Bash Tool: Extract and list kgraph files
````

````plaintext
Bash Tool: Read the kgschema and medlit schema/model files — the most relevant for the base layer discussion
````

````plaintext
Thought process: Validated kgschema as ideal typed graph base layer foundation.

Now I have a very complete picture. Let me analyze what's in kgschema vs what we need for the "typed graph base layer."

Key findings:

1. **`kgschema` is already very close to what we want as a base layer.** It has:
   - `BaseEntity` (ABC + frozen Pydantic) - nodes
   - `BaseRelationship` (ABC + frozen Pydantic) - edges
   - `DomainSchema` ABC - the schema definition
   - `IdentityServer` ABC - entity resolution
   - `EntityStorageInterface`, `RelationshipStorageInterface`, `DocumentStorageInterface` ABCs
   - Additional models for constraints, evidence, provenance, validation, entity status tracking, and promotion policies

2. **The medlit schema properly extends kgschema** - concrete entity and relationship classes inherit from the base types, and the domain schema is properly implemented.

3. **There's actually a duplicate set of medlit models** - one in `medlit_schema/` with detailed fields like `umls_id` and `rxnorm_id`, and another simpler set in `medlit/entities.py` and `medlit/relationships.py`. 

4. **The sherlock pipeline is essentially reimplementing core kgschema functionality** - its entity resolution, entity records, relationship validation, and schema constraints are all simplified versions of what's already defined in the base classes and domain schema.

5. **Key differences between sherlock's approach and the kgschema design** -  sherlock relies on static identity maps and raw dicts while kgschema uses dynamic DB-backed resolution and typed entity subclasses, and sherlock's schema dict doesn't map to the more structured `PredicateConstraint` model.

6. **The kgschema is missing some foundational pieces for a typed graph base** - there's no `NodeType`/`EdgeType` enum classes, the `DomainSchema` is an abstract base class rather than a frozen Pydantic model, and the `EntitySpec`/`PredicateSpec` definitions in `spec.py` are incomplete.

7. **There are real design tradeoffs here** - `DomainSchema` needs to be an ABC to support async methods and domain logic, `BaseEntity.get_entity_type()` returns strings for flexibility rather than enum types, and the predicate constraints use string sets instead of enum values, which is more permissive but loses static type checking.

8. **The key realization is that kgschema is actually the foundation we've been building toward** - sherlock should define concrete `HolmesEntity` subclasses and a `HolmesDomain` implementation, then map the existing `SCHEMA` dict into this structured model.

9. **Now I'm seeing how the two entity patterns differ** - one approach uses simple subclasses with just the type override and stores metadata in a dict, while the other builds richer type hierarchies with more structure.

For Holmes, the simpler pattern makes sense - it's faster to implement and gets us moving.

The core insight I want to communicate is that kgschema is already solid and well-designed, so rather than building Holmes as a parallel system, it should integrate directly into that foundation. That means mapping Holmes concepts onto the existing abstractions: entities become HolmesEntity, relationships become HolmesRelationship wrapping the candidates, and the domain schema consolidates the SCHEMA dict and identity mapping in one place with a straightforward IdentityServer implementation.

Looking at what kgschema already does well - the PredicateConstraint approach with subject and object type sets is the right pattern, Evidence and Provenance are exactly what we need for provenance tracking, EntityStatus gives us the CANONICAL/PROVISIONAL/MERGED states Holmes will need, and domains can extend the evidence and provenance models. The type system uses string methods rather than enums, which is weaker but functional - worth considering whether to add the enum layer for better type safety.

There's also `ValidationIssue` for structured error handling.
````

Now I have a complete picture of both codebases. This is very informative. The main finding is:

**`kgschema` is already the base layer you've been describing.** It's well-designed and Holmes should plug into it rather than running parallel.

Let me map what exists to what sherlock needs:

---

**The hierarchy is already there**

```
kgschema (base layer — already exists)
  BaseEntity (ABC + frozen Pydantic, get_entity_type() abstract)
  BaseRelationship (ABC + frozen Pydantic, get_edge_type() abstract)
  DomainSchema (ABC: entity_types, relationship_types, predicate_constraints, validate_*)
  IdentityServer (ABC: resolve, promote, find_synonyms, merge)
  EntityStorageInterface / RelationshipStorageInterface (ABCs)
  Evidence, Provenance, EntityStatus, PromotionConfig

medlit_schema (extends kgschema — already exists)
  Disease(BaseEntity), Drug(BaseEntity), Gene(BaseEntity), ...
  Treats(BaseRelationship), Causes(BaseRelationship), ...
  MedlitDomain(DomainSchema)

sherlock (should extend kgschema — currently doesn't)
  06_identity.py ≈ a static IdentityServer
  09_validate.py SCHEMA dict ≈ predicate_constraints
  RelationshipCandidate ≈ BaseRelationship (but orphaned)
  entities.jsonl ≈ BaseEntity instances (but raw dicts)
```

---

**What sherlock's SCHEMA dict maps to**

`09_validate.py` has:
```python
SCHEMA = {
    "located_at": {"dom": {"person", "object"}, "ran": {"location"}},
    ...
}
```

In kgschema terms this is exactly `predicate_constraints` on `DomainSchema`:
```python
class HolmesDomain(DomainSchema):
    @property
    def predicate_constraints(self) -> dict[str, PredicateConstraint]:
        return {
            "located_at": PredicateConstraint(
                subject_types={"person", "object"},
                object_types={"location"},
            ),
            "knows_at":     PredicateConstraint(subject_types={"person"}, object_types={"person"}),
            "possesses":    PredicateConstraint(subject_types={"person"}, object_types={"object"}),
            "disguised_as": PredicateConstraint(subject_types={"person"}, object_types={"disguise"}),
            "authored":     PredicateConstraint(subject_types={"person"}, object_types={"document"}),
            "contains":     PredicateConstraint(subject_types={"location"}, object_types={"object"}),
            "married_to":   PredicateConstraint(subject_types={"person"}, object_types={"person"}),
            "employed_by":  PredicateConstraint(subject_types={"person"}, object_types={"person", "organisation"}),
        }
```

The `09_validate.py` script then becomes nearly trivial — it just calls `domain.validate_relationship(candidate)`.

---

**The entity side**

For Holmes you have two reasonable choices that mirror the existing `medlit/` duality:

**Pattern A** (like `medlit/medlit/entities.py`) — one class per type, all extra fields go in `metadata`:
```python
class HolmesCharacter(BaseEntity):
    def get_entity_type(self) -> str:
        return "person"
```
Simple, fast, metadata in the `dict`.

**Pattern B** (like `medlit/medlit_schema/entity.py`) — typed fields per class:
```python
class HolmesCharacter(BaseEntity):
    wiki: str | None = None
    first_appearance: str | None = None   # e.g. "SCAN"
    
    def get_entity_type(self) -> str:
        return "person"
```
More verbose, but mypy helps and the fields are self-documenting.

For the current Holmes work, Pattern A is probably the right call — you're still figuring out what fields each entity type needs. Pattern B is appropriate once the schema is stable, which medlit is.

---

**The `NodeType`/`EdgeType` StrEnum question**

kgschema doesn't use them — type identity flows through `get_entity_type()` returning a string, and `predicate_constraints` using `set[str]`. That's intentionally loose to keep the base domain-agnostic.

The StrEnum approach I sketched earlier would add a layer of mypy safety at the cost of requiring every domain to define enums. Worth adding to kgschema, but it's an enhancement, not a prerequisite — you could add `node_type_enum: type[NodeType] | None = None` as an optional field on `DomainSchema` and leave existing domains unaffected.

---

**The immediate concrete gap**

The sherlock `06_identity.py` has `IDENTITY_MAP` and `ENTITY_META` but there's no `IdentityServer` implementation. The simplest path is a `StaticHolmesIdentityServer(IdentityServer)` that wraps those two dicts — essentially formalizing what the script already does. No Postgres required for Holmes; a dict-backed implementation is fine for a single-story corpus.

The biggest win from connecting to kgschema is that the pipeline stage outputs — currently raw dicts in JSONL — become proper `BaseEntity` and `BaseRelationship` instances that the kgserver's storage layer already knows how to handle.





---
Powered by [Claude Exporter](https://www.ai-chat-exporter.net)
