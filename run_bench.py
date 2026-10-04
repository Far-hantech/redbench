#!/usr/bin/env python3
"""Run RedBench.

Examples:
  python run_bench.py --target mock
  python run_bench.py --target ollama --model qwen3:14b
  python run_bench.py --target openai --model gpt-4o-mini   (needs OPENAI_API_KEY)
"""
import argparse
import json
from pathlib import Path

from redbench.defenses import DEFENSES
from redbench.runner import load_attacks, render_markdown, run_benchmark
from redbench.targets import MockTarget, OllamaTarget, OpenAICompatibleTarget

ROOT = Path(__file__).parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="mock", choices=["mock", "ollama", "openai"])
    ap.add_argument("--model", default="")
    ap.add_argument("--defenses", default=",".join(DEFENSES))
    ap.add_argument("--attacks", default=str(ROOT / "attacks" / "attacks.jsonl"))
    ap.add_argument("--out", default=str(ROOT / "results"))
    args = ap.parse_args()

    if args.target == "mock":
        target = MockTarget()
    elif args.target == "ollama":
        target = OllamaTarget(model=args.model or "qwen3:14b")
    else:
        target = OpenAICompatibleTarget(model=args.model or "gpt-4o-mini")

    attacks = load_attacks(args.attacks)
    result = run_benchmark(target, attacks, args.defenses.split(","))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(result, indent=2))
    md = render_markdown(result)
    (out / "results.md").write_text(md)
    print(md)
    print(f"Wrote {out / 'results.json'} and {out / 'results.md'}")


if __name__ == "__main__":
    main()
