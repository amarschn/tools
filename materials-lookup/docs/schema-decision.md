# Schema decision 001: material granularity

Status: adopted for the prototype

## Decision

Materials form an explicit hierarchy:

```text
family → grade → variant
```

- A **family** is a broad engineering class, such as aluminium alloys.
- A **grade** is a named material independent of processing condition, such as
  aluminium 6061.
- A **variant** is the condition that owns measured observations, such as
  6061-T6.

Search indexes all three levels. Query specificity is a ranking signal: a broad
family term prefers a family, a bare designation prefers a grade, and a
conditioned designation prefers a variant. Prominence remains a small manual
tie-breaker rather than the primary model.

## Aggregate values

Family and grade records do not store point measurements. Their displayed
ranges are generated from descendant variant observations during the build and
are labelled **observed envelopes**.

This avoids two misleading outcomes:

1. treating a class-level range as measurement uncertainty; and
2. creating a second, manually maintained copy of descendant values.

The envelope describes only the prototype corpus. It is not a claim about the
full possible range of a family or grade.

## Consequences

- Variant records must have exactly one grade parent.
- Grade records must have exactly one family parent.
- A variant may carry several observations of the same property when product
  form, thickness, orientation, temperature, test method, or statistical basis
  differs.
- Property pages show conditioned observations, while grade/family record pages
  summarize descendant coverage.
- Manufacturer-specific materials that do not fit cleanly under a standard
  grade remain an open schema case; the prototype does not silently invent a
  parent.
