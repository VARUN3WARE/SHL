# 05 - Catalog Data Strategy

## Scope

Only use SHL `Individual Test Solutions`. Exclude `Pre-packaged Job Solutions`.

The product catalog page lists both categories, so the scraper must preserve category boundaries. Do not rely only on product URL patterns.

Main catalog:

- https://www.shl.com/solutions/products/product-catalog/

Example item pages:

- https://www.shl.com/solutions/products/product-catalog/view/java-8-new/
- https://www.shl.com/solutions/products/product-catalog/view/occupational-personality-questionnaire-opq32r/
- https://www.shl.com/solutions/products/product-catalog/view/shl-verify-interactive-g/
- https://www.shl.com/products/product-catalog/view/global-skills-assessment/

## Fields to collect

Minimum required for evaluator:

- exact `name`;
- exact catalog `url`;
- exact `test_type`.

Strongly recommended:

- description;
- job levels;
- languages;
- assessment length text;
- parsed duration minutes;
- remote testing flag;
- adaptive/IRT flag;
- source section;
- downloads/fact-sheet labels if available.

## Test type legend

The catalog defines:

- `A` - Ability & Aptitude
- `B` - Biodata & Situational Judgement
- `C` - Competencies
- `D` - Development & 360
- `E` - Assessment Exercises
- `K` - Knowledge & Skills
- `P` - Personality & Behavior
- `S` - Simulations

Store this legend in code and docs. It helps generate readable replies without inventing anything.

## Scraping approach

### Page traversal

The catalog supports pagination using query params like:

```text
?start=0&type=1
?start=12&type=1
```

`type=1` appears to correspond to Individual Test Solutions in search results. Verify this during scraping.

### Suggested scraper algorithm

1. Request catalog listing pages for Individual Test Solutions.
2. Parse the table rows under the `Individual Test Solutions` heading.
3. Extract product name, product URL, remote testing, adaptive/IRT, and test type.
4. Follow each product URL.
5. Parse product page fields:
   - heading;
   - description;
   - job levels;
   - languages;
   - assessment length;
   - test type;
   - remote testing;
   - downloads.
6. Normalize fields but keep raw source text.
7. Write `data/catalog_raw.json`.
8. Write `data/catalog_clean.json`.
9. Validate all records.

## Validation checks

Required:

- no empty `name`;
- no empty `url`;
- URL starts with `https://www.shl.com/`;
- source section is `Individual Test Solutions`;
- `test_type` contains only known letters;
- no duplicate URLs;
- exact returned recommendation rows must exist in catalog.

Recommended:

- count products by test type;
- count missing descriptions;
- count missing durations;
- spot-check known products:
  - `Java 8 (New)`;
  - `Occupational Personality Questionnaire OPQ32r`;
  - `SHL Verify Interactive G+`;
  - `Global Skills Assessment`.

## Normalization

### Names

Keep exact names for output. Add normalized aliases for lookup:

- lowercase;
- remove punctuation;
- remove `(New)`;
- convert `&` to `and`;
- collapse whitespace;
- add acronyms from known products, for example `OPQ`, `GSA`, `SVIG+`.

### Durations

Examples:

- `Approximate Completion Time in minutes = 18` -> `18`.
- `Untimed, approx. 25` -> `25` with raw text preserved.
- missing duration -> `null`.

### Test type

Catalog may show multi-letter strings like `A E B C D P`. Preserve as a string and also store as a list:

```json
{"test_type": "A E B C D P", "test_type_codes": ["A", "E", "B", "C", "D", "P"]}
```

For the API response, return the string form from catalog.

## Retrieval text

Build `search_text` using:

```text
{name}
{description}
Job levels: ...
Test type: ...
Languages: ...
Assessment length: ...
```

Add controlled synonyms in a separate field, not into the raw description:

- developer -> software engineer, programmer
- stakeholder -> communication, collaboration, relationship management
- manager -> leadership, people management
- personality -> OPQ, behavior, workplace style
- cognitive -> ability, reasoning, G+
- coding -> programming, software development

## Runtime rule

Never scrape SHL at request time. Scrape before deployment and ship the cleaned catalog with the app.

Reasons:

- evaluator timeout is 30 seconds;
- SHL may block requests;
- free hosting cold starts are slow;
- deterministic data improves debugging.

