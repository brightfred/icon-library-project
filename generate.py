#!/usr/bin/env python3
"""
OpenMark Icons — Generation CLI
Reads queue.json and generates icons until the queue is empty.

Usage:
  python generate.py                        # run full queue, auto-push
  python generate.py --once                 # process one icon then stop
  python generate.py --no-push              # generate but skip git push
  python generate.py --dry-run              # print queue and exit
  python generate.py --backend omnisvg      # use OmniSVG instead of Ollama
  python generate.py --backend ollama       # explicitly use Ollama (default)
  python generate.py --backend finetuned    # use fine-tuned local model
"""

import argparse
import sys
from pipeline import create_backend, IconGenerator, QueueManager


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OpenMark icon generation worker"
    )
    parser.add_argument(
        "--backend",
        default="ollama",
        choices=["ollama", "omnisvg", "finetuned"],
        help="Generation backend to use (default: ollama)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process one icon then exit",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Generate but skip git commit and push",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the queue and exit without generating",
    )
    return parser.parse_args()


def dry_run(queue: QueueManager):
    entries = queue.read()
    if not entries:
        print("Queue is empty.")
        return
    print(f"Queue ({len(entries)} icons):")
    for i, e in enumerate(entries, 1):
        retry = f"  [retry: {e.retry_reason}]" if e.retry_reason else ""
        print(f"  {i:3}. {e.name:<45} {e.concept}{retry}")


def main():
    args    = parse_args()
    queue   = QueueManager()

    if args.dry_run:
        dry_run(queue)
        sys.exit(0)

    if queue.count() == 0:
        print("Queue is empty. Add icons with:")
        print("  python queue_manager.py add science-laser 'laser beam emitter'")
        print("  python queue_manager.py starter")
        sys.exit(0)

    backend   = create_backend(args.backend)
    generator = IconGenerator(
        backend   = backend,
        auto_push = not args.no_push,
    )
    stats = generator.run(once=args.once)

    sys.exit(0 if stats.failed == 0 else 1)


if __name__ == "__main__":
    main()