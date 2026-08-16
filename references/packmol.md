# Packmol gate

Packmol is a geometry initializer, not a force-field validator. Use a fixed seed, explicit input molecule files, exact requested molecule counts, and a box derived from sourced composition and density assumptions. Record the requested and actual box, atom counts, minimum distances, return code, and input/output hashes. If the target box cannot be packed, expand only under the declared bounded policy and retain the original request.
