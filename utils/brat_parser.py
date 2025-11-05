# utils/brat_parser.py
import re
from typing import Dict, List, Tuple

def parse_ann_file(txt_path: str, ann_path: str):
    """
    Returns:
      text: full transcript text
      entities: list of dicts {id, label, start, end, text}
      relations: list of dicts {id, label, arg1, arg2}
    """
    with open(txt_path, 'r', encoding='utf-8') as f:
        text = f.read()

    entities = []
    relations = []
    with open(ann_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("T"):
                # example: T1\tDECISION 0 25\tWe decided to extend the deadline
                m = re.match(r'^(T\d+)\t([^\s]+) (\d+) (\d+)\t(.+)$', line)
                if m:
                    tid, label, start, end, txt = m.groups()
                    entities.append({
                        'id': tid,
                        'label': label,
                        'start': int(start),
                        'end': int(end),
                        'text': txt
                    })
                else:
                    # fallback: some annotations have multiple spans
                    parts = line.split('\t')
                    tid = parts[0]
                    label_and_spans = parts[1]
                    txt = parts[2] if len(parts) > 2 else ""
                    label = label_and_spans.split(' ')[0]
                    spans = label_and_spans[len(label)+1:]
                    entities.append({
                        'id': tid,
                        'label': label,
                        'spans': spans,
                        'text': txt
                    })
            elif line.startswith("R"):
                # relation example: R1\tResponsible Arg1:T2 Arg2:T3
                parts = line.split()
                rid = parts[0]
                lab = parts[1].split('\t')[-1]
                # simple parse for Arg1:Tx Arg2:Ty
                args = {}
                for p in parts[1:]:
                    if ':' in p:
                        k, v = p.split(':', 1)
                        args[k] = v
                relations.append({
                    'id': rid,
                    'label': parts[1],
                    'args': args
                })
            # ignore others for now
    return text, entities, relations
