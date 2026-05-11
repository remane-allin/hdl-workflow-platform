# Register Map Contract

Prefer each register entry to state:

- name
- offset
- width
- access
- reset
- description
- fields

Prefer each field entry to state:

- name
- lsb
- msb
- access
- reset
- side effects

Flag these early:

- overlapping offsets
- overlapping fields
- undefined reset values
- missing access type
- write semantics that the scoreboard cannot observe yet
