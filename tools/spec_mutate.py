#!/usr/bin/env python3
"""Apply constraint changes to a copy of an OpenAPI spec (structure-aware, no text substitution).
Usage: spec_mutate.py in.yaml out.yaml path.to.key=VALUE [...]   (VALUE is parsed as YAML: 1000, false, "x")"""
import os, sys
from decimal import Decimal
import yaml
sys.path.insert(0, os.path.dirname(__file__))
import gen_testdata


class _Dumper(yaml.SafeDumper):
    pass


_Dumper.add_representer(Decimal, lambda dumper, v: dumper.represent_scalar('tag:yaml.org,2002:float', format(v, 'f')))   # keep 0.00001 plain
src, dst, *changes = sys.argv[1:]
d, _ = gen_testdata.load_spec(src)
for ch in changes:
    key, val = ch.split('=', 1)
    node = d
    parts = key.split('.')
    for p in parts[:-1]:
        node = node[p]
    node[parts[-1]] = yaml.load(val, Loader=gen_testdata._Loader)
    print(f'changed {key} -> {val}')
yaml.dump(d, open(dst, 'w'), Dumper=_Dumper, sort_keys=False)
