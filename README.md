# json-e

**edit structure, not syntax**

---

## A structure-first editor for JSON

`json-e` removes the need to manually write or maintain JSON syntax.  
Instead of editing brackets and commas, you directly manipulate the structure.

---

## Files

### `json-e.py`
Core JSON editor

- Open any JSON file  
- View it as a nested structure  
- Edit values inline  
- Duplicate entire branches (`+`)  
- Add new children inside objects/arrays  
- Delete fields/items (`-`)  
- Rename keys  
- Collapse / expand large structures  

---

### `json-e.image.py`
Image → JSON sidecar generator + editor

- Open an image file  
- Automatically generate structured metadata  

**Fills:**
- filename  
- extension  
- paths  
- size  
- sha256  
- timestamps  
- width / height (optional)  

**Add:**
- summary  
- notes  
- tags  
- annotations  
- training structures  

**Default save name:**

<image_name>.<timestamp>.json


---

## Core idea

Most tools treat JSON as text.  
`json-e` treats JSON as structure.

You don’t write JSON.  
You manipulate it.

---

## Controls

duplicate → copy value or full branch
Add Child → add inside container
        → delete node

✓ → apply value
Rename → rename key
▶ / ▼ → collapse / expand


---

## Use cases

### General
- edit configs safely  
- build structured data without errors  
- avoid syntax issues entirely  

### Creative
- annotate images  
- build datasets  
- store structured ideas  

### Research
- construct datasets  
- manage experiment configs  
- prepare training inputs  
- organize metadata at scale  

---

## Run

```bash
python3 json-e.py
python3 json-e.image.py

Optional:

pip install pillow
Philosophy
structure over syntax
direct manipulation over typing
duplication over repetition
clarity over abstraction
