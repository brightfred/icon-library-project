#!/usr/bin/env python3
"""
OpenMark Icons — Queue Manager CLI

Usage:
  python queue_manager.py list                              # show queue
  python queue_manager.py count                            # count queue
  python queue_manager.py add science-laser "laser beam"  # add one icon
  python queue_manager.py add-batch icons.txt             # add from file
  python queue_manager.py clear                           # clear queue
  python queue_manager.py requeue                         # move rejected back to queue
  python queue_manager.py starter                         # load starter icon set

Batch file format (one per line):
  science-laser: coherent laser beam emitter with lens
  engineering-pump: centrifugal pump with impeller and casing
"""

import sys
from datetime import datetime
from pipeline import QueueManager, QueueEntry
from pathlib import Path


# ── Starter icon set ──────────────────────────────────────────────────────────

STARTER_ICONS = [
    # science
    ("science-spectrometer",   "optical spectrometer with prism and wavelength lines"),
    ("science-telescope",      "refracting telescope with lens barrel and eyepiece"),
    ("science-thermometer",    "laboratory thermometer with bulb and graduated scale"),
    ("science-prism",          "triangular glass prism refracting light"),
    ("science-petri-dish",     "petri dish with lid viewed from above"),
    ("science-test-tube",      "glass test tube in a rack"),
    ("science-bunsen-burner",  "bunsen burner with gas nozzle and flame"),
    ("science-balance-scale",  "analytical balance with two suspended pans"),
    ("science-ph-meter",       "pH meter probe with digital display"),
    ("science-laser",          "laser emitter with coherent beam lines"),
    ("science-sonar",          "sonar pulse wave emanating from a source point"),
    ("science-barometer",      "mercury barometer tube with scale"),
    # engineering
    ("engineering-turbine",    "wind turbine tower with three blades"),
    ("engineering-piston",     "engine piston with connecting rod in cylinder"),
    ("engineering-wrench",     "adjustable wrench with jaw and handle"),
    ("engineering-caliper",    "vernier caliper with sliding jaw"),
    ("engineering-drill",      "power drill with bit and chuck"),
    ("engineering-conveyor",   "conveyor belt with rollers"),
    ("engineering-motor",      "electric motor with shaft and housing"),
    ("engineering-sensor",     "industrial sensor probe with signal waves"),
    ("engineering-pump",       "centrifugal pump with impeller and casing"),
    ("engineering-compressor", "air compressor tank with motor on top"),
    # environment
    ("environment-glacier",    "glacier with melting drips and surface cracks"),
    ("environment-wildfire",   "wildfire with flame and rising smoke plume"),
    ("environment-coral",      "branching coral reef with polyp texture"),
    ("environment-rain",       "raincloud with falling drops below"),
    ("environment-snowflake",  "six-pointed snowflake crystal"),
    ("environment-pollution",  "factory smokestacks emitting particle clouds"),
    ("environment-tide",       "tidal wave with directional flow lines"),
    ("environment-erosion",    "cliff face with eroding particles falling away"),
    # aquaculture
    ("aquaculture-algae",      "branching algae fronds"),
    ("aquaculture-oyster",     "oyster shell open with pearl inside"),
    ("aquaculture-salinity",   "salinity meter probe submerged in water"),
    ("aquaculture-feeding",    "automatic fish feeder dispensing pellets"),
    ("aquaculture-cage",       "offshore aquaculture cage floating on surface"),
]


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_list(queue: QueueManager):
    entries = queue.read()
    if not entries:
        print("Queue is empty.")
        return
    print(f"Queue ({len(entries)} icons):")
    for i, e in enumerate(entries, 1):
        retry = f"  [retry: {e.retry_reason}]" if e.retry_reason else ""
        print(f"  {i:3}. {e.name:<45} {e.concept}{retry}")


def cmd_count(queue: QueueManager):
    print(queue.count())


def cmd_add(queue: QueueManager, name: str, concept: str):
    entry = QueueEntry(name=name, concept=concept)
    added = queue.add(entry)
    if added:
        print(f"Added: {name} — {concept}")
    else:
        print(f"Already in queue: {name}")


def cmd_add_batch(queue: QueueManager, filepath: str):
    path = Path(filepath)
    if not path.exists():
        print(f"File not found: {filepath}")
        sys.exit(1)

    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            name, concept = line.split(":", 1)
        else:
            name    = line.replace(" ", "-")
            concept = line
        entries.append(QueueEntry(name=name.strip(), concept=concept.strip()))

    added = queue.add_many(entries)
    print(f"Added {added} icon(s) from {filepath}")


def cmd_clear(queue: QueueManager):
    count = queue.clear()
    print(f"Cleared {count} icon(s) from queue.")


def cmd_requeue(queue: QueueManager):
    added = queue.requeue_rejected()
    if added:
        print(f"Requeued {added} rejected icon(s).")
    else:
        print("Nothing to requeue.")


def cmd_starter(queue: QueueManager):
    entries = [QueueEntry(name=n, concept=c) for n, c in STARTER_ICONS]
    added   = queue.add_many(entries)
    print(f"Added {added} starter icon(s) to queue.")


# ── CLI entrypoint ────────────────────────────────────────────────────────────

COMMANDS = {
    "list":      lambda q, args: cmd_list(q),
    "count":     lambda q, args: cmd_count(q),
    "clear":     lambda q, args: cmd_clear(q),
    "requeue":   lambda q, args: cmd_requeue(q),
    "starter":   lambda q, args: cmd_starter(q),
    "add":       lambda q, args: cmd_add(q, args[0], " ".join(args[1:])),
    "add-batch": lambda q, args: cmd_add_batch(q, args[0]),
}


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    cmd  = args[0]
    rest = args[1:]

    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}")
        print(f"Available: {', '.join(COMMANDS.keys())}")
        sys.exit(1)

    queue = QueueManager()
    COMMANDS[cmd](queue, rest)


if __name__ == "__main__":
    main()