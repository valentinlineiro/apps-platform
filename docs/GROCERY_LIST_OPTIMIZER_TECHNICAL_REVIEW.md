# Grocery List Optimizer Technical Review

## Scope

This review covers how supermarket data should be normalized for a `grocery-list-optimizer` app built within the current platform architecture: Flask backend, Angular element frontend, tenant-aware portal integration, and platform registry/logging conventions.

The goal is to define a data model and ingestion pipeline that makes optimization reliable. Scrapers and source APIs should not feed optimization logic directly.

## Summary

The correct design is a canonical ingestion pipeline with four layers:

1. Raw source records
2. Canonical product offers
3. Smart catalog mappings
4. Optimizer-ready inputs

This separates source-specific extraction from pricing logic, product equivalence, and route optimization. It also keeps the optimization engine stable even when supermarket connectors change.

## Current Fit With Platform

This workspace already supports a marketplace-style catalog and tenant-aware install model in the portal. A Grocery List Optimizer fits the same plugin model, but its hardest problem is not UI scaffolding. It is data normalization.

Given the current architecture, the backend should own:

- connector execution
- raw snapshot persistence
- normalization
- catalog matching
- cached optimizer inputs

The frontend should consume normalized APIs only.

## Recommended Normalization Model

### 1. Raw Source Records

Each connector should write raw records exactly as received from the supermarket source.

Purpose:

- auditability
- replayability
- parser debugging
- source change detection

Suggested fields:

```ts
type RawSourceRecord = {
  source: 'mercadona' | 'carrefour' | 'dia' | string;
  sourceStoreId: string | null;
  sourceProductId: string;
  sourceUrl: string | null;
  scrapedAt: string;
  payloadJson: unknown;
  titleRaw: string | null;
  brandRaw: string | null;
  priceRaw: string | null;
  promoRaw: string | null;
  packRaw: string | null;
  stockRaw: string | null;
};
```

Do not discard source text after parsing. It is needed when normalization rules fail or source sites change formatting.

### 2. Canonical Product Offers

Every raw record should be transformed into a normalized offer record.

Suggested shape:

```ts
type CanonicalOffer = {
  source: string;
  sourceProductId: string;
  sourceStoreId: string;
  canonicalProductId: string | null;
  title: string;
  brand: string | null;
  category: string | null;
  quantityValue: number | null;
  quantityUnit: 'g' | 'kg' | 'ml' | 'l' | 'unit' | null;
  packCount: number | null;
  totalPrice: number;
  currency: 'EUR';
  unitPrice: number | null;
  unitBasis: 'kg' | 'l' | 'unit' | null;
  inStock: boolean | null;
  isPromo: boolean;
  capturedAt: string;
};
```

This is the minimum level required for meaningful price comparison.

### 3. Smart Catalog

Product identity must be separated from store offers.

Example:

- canonical product: `whole-milk-semi-1l`
- offers: one per supermarket/store combination

Suggested mapping model:

```ts
type ProductMatch = {
  source: string;
  sourceProductId: string;
  canonicalProductId: string;
  confidence: number;
  matchMethod: 'barcode' | 'exact' | 'rules' | 'fuzzy' | 'manual';
};
```

This layer is what allows the optimizer to decide whether two listings are identical, equivalent, or only acceptable substitutes.

### 4. Optimizer Input

The optimization engine should consume only:

- canonical offers
- canonical store metadata
- user constraints

It should not know how any supermarket formats pack sizes, promo labels, or stock text.

## Price Normalization Rules

Unit normalization must be deterministic and centralized.

Recommended rules:

- weight products normalize to `price_per_kg`
- volume products normalize to `price_per_l`
- count-based products normalize to `price_per_unit`
- mixed packs retain both `totalPrice` and derived unit price

Examples:

- `500 g` becomes `0.5 kg`
- `1000 ml` becomes `1 l`
- `6 x 200 ml` becomes `1.2 l`
- `12 uds` becomes `12 unit`

Promotions need special treatment:

- preserve raw promo text
- compute effective price only if the rule is deterministic
- if promo logic is ambiguous, flag `isPromo` but do not optimize based on derived savings

Examples of safe derivations:

- `2nd unit 50% off`
- `3x2`

Examples that should usually remain advisory only:

- loyalty-card discounts
- bundle discounts requiring unrelated products
- app-only or location-specific coupons

## Product Mapping Strategy

The catalog matcher should be staged, not monolithic.

Recommended matching order:

1. barcode or GTIN match
2. exact normalized name plus brand plus size
3. rule-based category match
4. fuzzy token similarity
5. manual review queue

The system should keep both the matched product and the confidence score. Low-confidence matches should not silently participate in hard optimization decisions.

For v1, use three practical equivalence levels:

- exact same product
- same brand and same normalized size
- acceptable substitute within category

This is enough to make the optimizer useful without solving the full retail ontology problem.

## Domain Dictionaries

Normalization quality will depend on curated dictionaries and parsers.

Required dictionaries:

- units and size expressions
- brand aliases
- category aliases
- supermarket-specific packaging conventions
- organic/private-label/preferred-brand markers

Examples:

- `1L`, `1000 ml`, `1 litro` => same normalized volume
- `u`, `ud`, `uds`, `unidad` => count-based unit
- `semi`, `semidesnatada` => normalized milk subtype token

This should live in backend normalization modules, not in the optimizer itself.

## Store Normalization

Store metadata also needs a canonical model.

Suggested shape:

```ts
type CanonicalStore = {
  sourceStoreId: string;
  chain: string;
  name: string;
  lat: number;
  lng: number;
  address: string;
  hours: WeeklyHours;
  services: {
    parking: boolean | null;
    pickup: boolean | null;
  };
};
```

This model is required for:

- geo-radius filtering
- one-stop shop selection
- route optimization
- user store exclusions

If busy periods are added later, they should be modeled as advisory metadata, not as a hard dependency of the optimizer.

## Proposed Backend Pipeline

Within this workspace, the backend should be structured conceptually as:

- `connectors/`
  - one adapter per supermarket
- `normalizers/`
  - price parsing
  - unit parsing
  - stock parsing
  - promo parsing
- `catalog/`
  - canonical products
  - matcher
  - review queue
- `cache/`
  - latest offers
  - historical snapshots
- `optimizer/`
  - consumes canonical offers and stores only

Operational flow:

1. connector fetches source data
2. raw source records are stored
3. normalizers derive canonical offers
4. catalog matcher links offers to canonical products
5. latest snapshot is materialized for optimizer queries
6. scheduled synchronization refreshes the cache

## Persistence Recommendations

Do not store only the latest state. Store snapshots.

Minimum persistence layers:

- raw source snapshot table
- normalized offer table
- product match table
- store metadata table
- materialized latest-offer view or cache

Historical snapshots are necessary for:

- debugging
- purchase-frequency suggestions
- price trend analysis
- source quality monitoring

## Multi-Tenant Behavior

The optimizer is naturally tenant-aware because list collaboration and preferences are tenant-specific.

Tenant-scoped data should include:

- shared grocery lists
- item preferences
- excluded stores
- favorite brands
- home location
- historical shopping behavior

Global data should include:

- canonical products
- store metadata
- normalized offers
- source connector state

This split avoids duplicate ingestion while preserving tenant-specific optimization behavior.

## Risks And Constraints

### 1. Data Source Instability

Scrapers will break. The architecture must expect selector drift, anti-bot changes, and missing fields.

Mitigation:

- preserve raw snapshots
- track parse success rates
- isolate supermarket-specific logic in connectors

### 2. False Product Equivalence

Incorrect mappings will produce misleading recommendations.

Mitigation:

- confidence scoring
- manual review path
- conservative v1 equivalence rules

### 3. Promotion Ambiguity

Many promotions are not universally applicable.

Mitigation:

- avoid treating all promo labels as real savings
- separate advisory discounts from deterministic discounts

### 4. Stock Accuracy

Real-time stock is often unreliable or lagging.

Mitigation:

- represent stock as probabilistic or nullable when needed
- re-check before finalizing optimized trips

### 5. Geographic Complexity

Route optimization depends on high-quality store coordinates and user location permissions.

Mitigation:

- keep route calculations modular
- treat logistics as a downstream layer on top of normalized offers

## Recommendation

The correct normalization strategy is:

- ingest raw supermarket data unchanged
- convert it into canonical offers
- map offers into a smart catalog with confidence scores
- expose only normalized models to the optimizer and frontend

Do not couple the optimizer to scraper output. If that boundary is not enforced, every new supermarket integration will destabilize pricing, catalog matching, and route logic.

## Suggested Next Steps

1. Define backend persistence schema for raw records, canonical offers, and product matches.
2. Implement a normalization library for units, price parsing, and promo parsing.
3. Start with one or two supermarket connectors and validate data quality before scaling.
4. Keep v1 catalog matching conservative.
5. Expose normalized APIs to the Angular frontend only after the backend model is stable.
