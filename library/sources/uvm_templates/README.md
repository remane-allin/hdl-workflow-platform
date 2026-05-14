# UVM Template Sources

This directory stores reusable Loop2 UVM template database entries. These
entries are indexed by `library/indexes/template_index.yaml` and can be queried
with `hdlflow get-template-detail`.

The templates describe reusable structure and code shape. They are not direct
copies of external or reference projects. Project-specific protocol behavior,
register maps, scoreboards, coverage bins, and sequences must be generated from
the normalized spec before Loop2 closure.
