# Ingredient and technique extraction — manual audit

Hand check of random explicit extractions from the 20 selected dishes (plan Phase 11). Each row was judged
correct if the dish name or description really states the ingredient, technique or descriptor.

## Round 1 (seed 11, 60 extractions, before fixes)

55 of 60 correct (92%). Errors:

| Extraction | Text | Problem | Fix |
|---|---|---|---|
| MUTTON | "Mozzarella and Goat Cheese" | goat → mutton | "goat cheese" is a fixed phrase, counted as cheese |
| CHEESE | "cottage cheese chunks" (×2) | cottage cheese is paneer | "cottage cheese" / "Indian cheese" → paneer |
| DEEP_FRIED | "stir-fried with onions" | hyphen split the phrase | hyphens treated as spaces, "stir fried" phrase handled first |
| CREAM | "blended to creamy perfection" | texture word, not cream | not fixed (counted as an error) |

Also fixed after round 1: "fried rice" no longer triggers deep-fried, "ice cream" no longer triggers cream, and
basil was removed from the premium-ingredient list (it is standard on a margherita).

## Round 2 (seed 23, 60 extractions, after the fixes above)

57 of 60 correct (95%). Errors:

| Extraction | Text | Problem | Fix |
|---|---|---|---|
| SIGNATURE | "flavored with special mountain herbs" | "special" as an ordinary adjective | not fixed |
| CHEESE | "Fresh Indian Cheese (Paneer)" | Indian cheese is paneer | fixed after round 2 |
| ONION | "Prepared without onion & garlic" | negation | simple negation rule added: "without / no / minus X (and Y)" |

## What this does not measure

- **Recall.** Ingredients that are present but described with a word outside the lexicon are missed. Recall
  was not audited.
- **Matching noise.** A few rows are matched to the wrong canonical dish (for example "Shahi Paneer Lababdar"
  as shahi paneer). Those are dish-matching errors, not extraction errors.

Precision of the explicit extraction is therefore about 92–95% on these dishes. The models use explicit
features only; recipe-inferred ingredients are stored with confidence 0.60 and do not vary within a dish.
