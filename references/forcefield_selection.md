# Force-field selection

Build a candidate registry before selecting a force field. Each candidate records source URL or archive, local path, SHA256, license, atom types, masses, charges, LJ terms, bonded terms, 1-4 behavior, combination rule, cross terms, validated solvent/salt systems, and known limitations.

Selection is a gate, not a ranking by convenience. If any required term is NOT_REPORTED or SOURCE_UNKNOWN, the candidate is incomplete. A candidate can be retained as a sensitivity model but cannot silently become the primary model.

Use a component-prefixed atom-type namespace. Preserve native files and produce namespaced derived files with an input manifest.
