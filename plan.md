# Computational Gastronomy — Delhi Food Intelligence

## 0. Agent Operating Mode

You are building a university mini-project collaboratively.

**Do NOT attempt to build the entire project in one go.**

Work strictly in small, verifiable phases.

After completing each phase:

1. Implement only the required functionality for that phase.
2. Run the relevant tests/checks.
3. Inspect the generated outputs/data.
4. Report what was built.
5. Report what was tested.
6. Report any problems, assumptions, or data-quality issues.
7. Show me representative outputs where appropriate.
8. **STOP and ask for my explicit approval before proceeding to the next phase.**

Do not proceed to the next phase without approval.

If a decision materially affects the architecture, dataset schema, data source, methodology, or scientific validity, stop and ask me before implementing it.

Do not silently make major assumptions.

---

# 1. Project Goal

Build an interactive web application called:

## "Delhi Gastronomic Intelligence"

The application studies the food landscape of Delhi using a custom, integrated gastronomic dataset.

The project has exactly four primary deliverables:

### Deliverable 1
**Large, structured Delhi menu dataset with proper metadata**

### Deliverable 2
**Interactive Food Map of Delhi**

### Deliverable 3
**Cuisine-adjusted Gastronomic Price Index**

### Deliverable 4
**What Drives Dish Prices?**

The final application should have four clearly visible buttons/pages:

```text
┌──────────────────────────────────────────────┐
│       DELHI GASTRONOMIC INTELLIGENCE         │
│                                              │
│  [ Dataset ] [ Food Map ] [ Price Index ]    │
│                                              │
│             [ What Drives Price? ]           │
└──────────────────────────────────────────────┘
```

Do not add unrelated features unless explicitly approved.

---

# 2. Geographic Scope

Initial scope:

## Delhi

Do not expand to all of India or even all of North India unless explicitly approved later.

The project should cover a sufficiently large number of Delhi localities to make spatial analysis meaningful.

Target:

- approximately 30–60 localities
- approximately 5,000–15,000 restaurants if realistically obtainable
- approximately 75,000–250,000 menu items as a target range

These are targets, not requirements.

**Data quality is more important than hitting an arbitrary number.**

The agent must report actual achievable coverage before committing to a final target.

---

# 3. Core Principle: Build a Custom Integrated Dataset

The project must NOT simply download one existing "Zomato dataset" or similar dataset and call it our own.

We will construct a custom dataset by integrating multiple legitimate data sources.

Potential categories of sources:

1. Restaurant/menu source
2. Geographic source
3. Ingredient/dish information source
4. Raw-material/ingredient price source

The exact sources must be investigated and proposed before large-scale data collection.

Respect the terms, robots policies, rate limits, licensing, and access restrictions of every source.

Do not attempt to bypass CAPTCHAs, authentication, anti-bot systems, paywalls, or technical restrictions.

If a source cannot legally/practically be collected at the required scale, propose an alternative and STOP for approval.

---

# 4. Data Architecture

Do NOT create one giant CSV.

Use normalized tables.

Initial proposed schema:

## restaurants

```text
restaurant_id
name
normalized_name
address
locality_id
latitude
longitude
rating
rating_count
price_range
restaurant_type
veg_nonveg
source
source_id
```

## menu_items

```text
dish_id
restaurant_id
dish_name
normalized_dish_name
category
cuisine
price
description
is_veg
is_bestseller
image_url
source
source_id
```

## localities

```text
locality_id
locality_name
normalized_name
district
latitude
longitude
geometry
```

## ingredients

```text
ingredient_id
canonical_name
category
aliases
```

## dish_ingredients

```text
dish_id
ingredient_id
quantity
unit
confidence
source
```

## ingredient_prices

```text
ingredient_id
date
market
price
unit
source
```

The agent may propose schema modifications if justified.

Do not change the schema silently.

---

# 5. Data Integration Requirements

The custom dataset must demonstrate actual data integration.

We need to solve:

## Entity resolution

Different sources may refer to the same restaurant differently.

Example:

```text
"Punjabi By Nature"
"Punjabi By Nature - CP"
"Punjabi By Nature, Connaught Place"
```

These should resolve to a canonical restaurant entity where appropriate.

Possible matching signals:

- normalized name
- address
- locality
- latitude/longitude
- phone number where legitimately available
- source identifiers

Do not merge records merely because names look similar.

Use confidence scores where useful.

---

# 6. Canonicalization

Create canonical vocabularies.

### Cuisine

For example:

```text
North Indian
North-Indian
Indian North
North Indian Cuisine
```

may map to:

```text
NORTH_INDIAN
```

### Ingredients

```text
Tomato
Tomatoes
Fresh Tomato
```

→

```text
TOMATO
```

### Dish names

Normalize obvious variations while preserving the original name.

Always retain:

```text
original_name
normalized_name
```

Never destroy source data during cleaning.

---

# 7. Data Provenance

Every important record should retain provenance.

We should be able to answer:

> Where did this restaurant/dish/price come from?

Therefore include:

```text
source
source_id
collection_date
```

where appropriate.

Maintain a `DATA_SOURCES.md` document containing:

- source name
- URL/API
- data obtained
- access method
- collection date
- license/usage notes
- limitations

---

# 8. Technology Stack

Preferred stack unless there is a strong reason to change:

### Data

- Python
- Pandas or Polars
- DuckDB
- Parquet

### Geographic analysis

- GeoPandas
- Shapely
- OpenStreetMap-derived geographic data
- Folium or Plotly

### ML

- scikit-learn
- XGBoost/LightGBM if required

### Explainability

- SHAP

### NLP

Start simple.

Possible tools:

- regex/rule-based extraction
- spaCy
- Sentence Transformers

Do not introduce an LLM merely because it is available.

### Web application

Prefer:

**Streamlit**

unless a technical requirement makes another framework substantially better.

---

# 9. Development Rules

Use Git.

Maintain:

```text
README.md
DATA_SOURCES.md
DATA_DICTIONARY.md
METHODOLOGY.md
```

Suggested structure:

```text
project/
│
├── app/
│   ├── main.py
│   ├── pages/
│   │   ├── dataset.py
│   │   ├── food_map.py
│   │   ├── price_index.py
│   │   └── price_drivers.py
│
├── data/
│   ├── raw/
│   ├── interim/
│   └── processed/
│
├── src/
│   ├── ingestion/
│   ├── cleaning/
│   ├── integration/
│   ├── geography/
│   ├── pricing/
│   ├── nlp/
│   └── modeling/
│
├── tests/
│
├── notebooks/
│
├── scripts/
│
├── README.md
├── DATA_SOURCES.md
├── DATA_DICTIONARY.md
├── METHODOLOGY.md
└── requirements.txt
```

Do not build everything immediately.

---

# PHASE 0 — Project Discovery

Before writing substantial code:

### Tasks

1. Inspect the development environment.
2. Identify Python version.
3. Identify available compute.
4. Check whether GPU is available.
5. Inspect existing project directory.
6. Check available packages.
7. Propose the final architecture.
8. Propose candidate data sources.
9. Explain the expected data available from each source.
10. Identify licensing/access concerns.
11. Estimate expected dataset size.
12. Identify the highest-risk part of the project.

### Output

Provide a short technical proposal:

```text
Architecture
Data sources
Schema
Expected scale
Risks
Compute requirements
Proposed next step
```

### STOP

Ask:

> "Phase 0 is complete. Do you approve this architecture and data acquisition plan?"

Do not proceed until approved.

---

# PHASE 1 — Data Source Feasibility Test

Do NOT collect thousands of records.

Choose a very small pilot:

### Target

Approximately:

- 2–3 localities
- 50–200 restaurants
- a manageable number of menu items

The objective is to determine whether the required fields can actually be obtained.

Test:

- restaurant name
- location
- locality
- cuisine
- rating
- price
- dish name
- dish description
- menu category
- image
- source metadata

### Output

Create:

```text
data/raw/pilot/
```

and produce:

```text
pilot_restaurants.parquet
pilot_menu_items.parquet
```

Create a data-quality report containing:

- row count
- missing values
- duplicate rate
- unique restaurants
- unique dishes
- cuisine count
- price coverage
- locality coverage

### STOP

Show me:

- sample records
- schema
- data-quality report
- source coverage
- problems encountered

Ask for approval before scaling.

---

# PHASE 2 — Finalize Dataset Schema

Using the pilot data:

1. Review the schema.
2. Identify fields that are unavailable or unreliable.
3. Modify schema if necessary.
4. Create `DATA_DICTIONARY.md`.
5. Define canonical formats.
6. Define IDs.
7. Define normalization rules.
8. Define entity-resolution rules.
9. Define missing-value handling.

Do not discard useful raw fields.

### STOP

Ask me to approve:

- schema
- canonicalization rules
- entity-resolution methodology

---

# PHASE 3 — Build Data Integration Pipeline

Implement reusable pipelines rather than one-off notebooks.

Example:

```text
source extraction
      ↓
raw storage
      ↓
cleaning
      ↓
normalization
      ↓
entity resolution
      ↓
geographic mapping
      ↓
validation
      ↓
Parquet/DuckDB
```

Requirements:

- reproducible
- rerunnable
- logged
- deterministic where possible
- no silent data loss

Produce a data integration report.

### STOP

Show:

- final row counts
- duplicate counts
- unmatched entities
- missing values
- locality coverage
- cuisine coverage
- representative records

Ask before moving forward.

---

# PHASE 4 — Scale Data Collection

Only after the pilot pipeline is approved.

Scale collection to the agreed Delhi scope.

Do not blindly maximize data.

Monitor:

- source failures
- duplicate rates
- malformed records
- missing prices
- missing locations
- API/request limits
- rate limits
- changes in source structure

Periodically checkpoint the data.

### STOP

After the first meaningful batch, report:

```text
Restaurants:
Menu items:
Localities:
Cuisines:
Data completeness:
Duplicate rate:
```

Ask whether to continue scaling.

---

# PHASE 5 — Geographic Dataset

Build the locality/geographic layer.

Tasks:

1. Obtain Delhi locality boundaries.
2. Normalize locality names.
3. Map restaurant coordinates to localities.
4. Validate coordinate assignments.
5. Identify restaurants outside expected Delhi boundaries.
6. Handle ambiguous locality assignments.

Create:

```text
localities.parquet
restaurant_locality.parquet
```

Generate a validation map.

### STOP

Show me the map and coverage statistics.

Ask for approval.

---

# PHASE 6 — Deliverable 1

Finalize the **Delhi Gastronomic Dataset**.

Create:

```text
restaurants.parquet
menu_items.parquet
localities.parquet
ingredients.parquet
dish_ingredients.parquet
ingredient_prices.parquet
```

Create an interactive dataset preview for the web application.

The Dataset page should show:

- dataset statistics
- sample rows
- filters
- cuisine distribution
- price distribution
- locality distribution
- restaurant count
- menu-item count

### STOP

Deliverable 1 must be reviewed before building Deliverable 2.

Ask:

> "Deliverable 1 is ready for review. Do you approve moving to the Food Map?"

---

# PHASE 7 — Food Map

Build the second application section.

Requirements:

## Main view

Interactive Delhi map.

Localities should be clickable.

Clicking a locality opens a food profile.

Example:

```text
SAKET

Restaurants: 523

Top cuisines:
1. North Indian
2. Chinese
3. Italian
4. Fast Food
5. Continental

Median dish price: ₹___

Cuisine diversity: ___

Most common dishes:
...
```

Possible visualizations:

- cuisine distribution
- restaurant density
- average/median price
- top dishes
- cuisine diversity

Do not overload the map.

### STOP

Run the application and show the working map.

Ask for approval before moving to the Price Index.

---

# PHASE 8 — Gastronomic Price Index Methodology

Before coding the visualization, validate the methodology.

Primary metric:

\[
GPI_{l,c}
=
\frac{
MedianPrice_{l,c}
}{
MedianPrice_{Delhi,c}
}
\times100
\]

where:

- `l` = locality
- `c` = cuisine

Interpretation:

```text
100 = Delhi benchmark
120 = 20% above benchmark
80 = 20% below benchmark
```

Use median rather than mean as the primary statistic because menu prices are likely to be highly skewed.

Investigate:

- minimum observation thresholds
- outlier handling
- confidence intervals/bootstrap intervals where practical
- cuisine coverage
- locality coverage

Do NOT produce misleading GPI values based on tiny sample sizes.

For example, if a locality has only two Japanese dishes, flag the estimate as unreliable or suppress it.

### STOP

Show me the proposed statistical methodology and example calculations.

Get approval before implementation.

---

# PHASE 9 — Deliverable 3: Price Index Application

Build the Price Index page.

Potential interface:

```text
Cuisine: [ All ▼ ]

Benchmark: Delhi

[Interactive Delhi Price Index Map]

Locality comparison

Locality     GPI     Median Price
----------------------------------
...
```

Allow:

- cuisine selection
- locality comparison
- overall index
- cuisine-specific index
- price distribution

Potential visualizations:

### 1. Choropleth map

Locality → GPI

### 2. Cuisine × locality heatmap

```text
             North Indian  Chinese  Italian
Saket             112        104      121
CP                125        119      133
Rohini             91         95       98
```

### 3. Distribution

Show actual price distributions rather than only the index.

This prevents the index from hiding important variation.

### STOP

Run the application and validate several localities manually.

Ask for approval.

---

# PHASE 10 — Deliverable 4 Data Preparation

Select approximately:

**10–20 dishes**

based on:

- popularity
- geographic coverage
- sufficient observations
- presence across multiple restaurant types/localities
- meaningful variation in price

Do not select dishes arbitrarily.

For each dish, construct observations:

```text
dish
restaurant
locality
price
cuisine
ingredients
preparation techniques
restaurant characteristics
```

Create a canonical dish matching system.

Example:

```text
Butter Chicken
Murgh Makhani
Butter Chicken Masala
```

must be investigated before deciding whether they represent the same analysis category.

### STOP

Show me the proposed 10–20 dishes and their observation counts.

Ask for approval.

---

# PHASE 11 — Ingredient and Technique Extraction

Extract observable features from menu descriptions and dish metadata.

Examples:

### Ingredients

- chicken
- paneer
- cream
- butter
- cheese
- seafood
- nuts
- imported ingredients

### Techniques

- tandoor
- grilled
- smoked
- fermented
- slow-cooked
- baked
- handmade

Maintain confidence levels.

Do not hallucinate ingredients that are not supported by the source.

If an ingredient is inferred rather than explicitly stated, mark it:

```text
source_type = inferred
confidence = ...
```

Prefer explicit evidence.

### STOP

Show sample extraction results and estimated accuracy.

Ask before modeling.

---

# PHASE 12 — Raw Material Price Integration

Where reliable public data is available, integrate ingredient prices.

Example:

```text
ingredient
date
market
price
unit
```

Normalize units:

```text
kg
g
litre
ml
piece
```

Do not pretend that market prices perfectly represent restaurant procurement costs.

The output is:

**estimated raw-material cost**, not actual restaurant cost.

### STOP

Review source quality and methodology before using the data in the final model.

---

# PHASE 13 — Price Driver Model

For each selected dish, investigate:

\[
Price =
f(
ingredients,
techniques,
locality,
restaurant characteristics,
rating,
cuisine,
raw\ material\ prices
)
\]

Start with interpretable models:

1. Linear/regularized regression
2. Random Forest
3. Gradient boosting

Compare performance.

Metrics:

- MAE
- RMSE
- \(R^2\)

Avoid overfitting.

Use appropriate train/test splitting.

If observations from the same restaurant appear in both training and test data, investigate whether this causes leakage.

Prefer grouped splitting by restaurant when appropriate.

---

# PHASE 14 — Explainability

Use SHAP or another interpretable method to investigate which features are associated with predicted price.

The application should communicate:

> **These factors are associated with higher/lower predicted menu prices.**

Do NOT claim:

> "This ingredient causes the restaurant to charge ₹X more."

unless the study design actually establishes causality.

Potential output:

```text
BUTTER CHICKEN

Observed median price: ₹___

Predicted price: ₹___

Price-associated factors:

Ingredient composition     ███████
Locality                   █████
Restaurant positioning     ████
Preparation indicators     ███
Rating                     ██
```

The exact visualization should be determined after seeing model results.

---

# PHASE 15 — Deliverable 4 Application

The user selects:

```text
Dish:
[ Butter Chicken ▼ ]
```

Application displays:

### 1. Dish image

Use 1 representative image or a small gallery.

### 2. Price across Delhi

Map/chart showing price variation.

### 3. Price distribution

Histogram/box plot.

### 4. Ingredients

Detected ingredients.

### 5. Techniques

Detected preparation techniques.

### 6. Price drivers

Model/SHAP visualization.

### 7. Raw-material context

Where reliable:

```text
Estimated raw-material cost
Observed menu price
Difference
```

Clearly label the limitations.

---

# PHASE 16 — Final Application Integration

Only after all four deliverables work independently.

Build the final application:

```text
                    HOME
                     │
       ┌─────────────┼─────────────┐
       │             │             │
   DATASET       FOOD MAP      PRICE INDEX
                                   │
                                   │
                           PRICE DRIVERS
```

Four explicit buttons/pages.

Requirements:

- consistent UI
- responsive enough for desktop
- loading states
- clear labels
- source/provenance information
- methodology information
- no broken visualizations
- no hard-coded analysis results where avoidable

---

# PHASE 17 — Testing

Before final submission, run:

## Data tests

- schema validation
- duplicate detection
- null checks
- range checks
- geographic validation
- price validation
- entity-resolution validation

## Model tests

- train/test leakage checks
- baseline comparison
- MAE/RMSE/R²
- cross-validation where appropriate
- feature importance sanity checks

## Application tests

Test every button.

Test:

- map interaction
- locality selection
- cuisine filters
- price index
- dish selection
- graphs
- empty states
- missing data
- invalid selections

---

# PHASE 18 — Final Documentation

Produce:

### README

- project motivation
- architecture
- setup
- running instructions
- data pipeline
- application screenshots
- deliverables

### DATA_DICTIONARY

Every column:

```text
column
type
description
source
allowed values
missing-value behavior
```

### DATA_SOURCES

For every external source:

- source
- URL
- collection date
- fields obtained
- licensing/access
- limitations

### METHODOLOGY

Explain:

- data integration
- entity resolution
- geographic assignment
- cuisine normalization
- GPI calculation
- dish selection
- ingredient extraction
- price modeling
- limitations

---

# CRITICAL AGENT RULES

## Rule 1 — Never build ahead

After each phase:

**STOP → REPORT → ASK FOR APPROVAL**

---

## Rule 2 — Never silently change methodology

If you discover that a planned method does not work:

STOP.

Explain:

```text
Problem
Why it matters
Possible solutions
Recommended option
```

Ask me to choose/approve.

---

## Rule 3 — Preserve raw data

Never overwrite raw data.

Use:

```text
raw → interim → processed
```

---

## Rule 4 — Never fabricate data

If a field is unavailable:

```text
NULL / UNKNOWN
```

Do not invent it.

---

## Rule 5 — Validate before scaling

Every major pipeline must first work on a small sample.

---

## Rule 6 — Prefer simple methods first

Start with:

- SQL
- Pandas/Polars
- statistical analysis
- interpretable ML

Only introduce complex NLP/LLMs if they solve a demonstrated problem.

---

## Rule 7 — Scientific honesty

Clearly distinguish:

**Observed**

from

**Estimated**

from

**Predicted**

from

**Inferred**

from

**Causal claims**

The project should not make causal claims from observational menu data.

---

# First Action

Do ONLY Phase 0.

Do not collect large amounts of data.

Do not build the Streamlit application.

Do not build ML models.

Do not implement the four deliverables yet.

First:

1. inspect the environment
2. investigate feasible data sources
3. propose the data schema
4. propose the integration architecture
5. identify data-access/licensing risks
6. estimate achievable dataset scale
7. report compute requirements
8. recommend the smallest pilot experiment

Then STOP and ask for explicit approval before proceeding.