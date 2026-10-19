"""Run the twenty questions, save the results, and make the tables.

  python run.py run --run 1                       all strategies, all questions
  python run.py run --run 1 --strategies S3 --questions Q-09     a small test
  python run.py run --run 1 --resume              skip questions that are already saved
  python run.py vague --questions Q-03 Q-08 Q-09 Q-14 Q-20       part C1
  python run.py tooltokens                        tokens added by the two tool definitions
  python run.py report                            tables for SUBMISSION.md
"""

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

import strategies
import tools

OUTPUTS = Path(__file__).resolve().parent / "outputs"
STRATEGY_FUNCTIONS = {"S1": strategies.run_s1, "S2": strategies.run_s2, "S3": strategies.run_s3}
STRATEGY_NAMES = {"S1": "S1 direct", "S2": f"S2 think and vote (k = {strategies.K})", "S3": "S3 tools"}

# FILL IN before you run "report": price in dollars per 1,000,000 tokens,
# from the OpenAI pricing page for gpt-5.6-luna.
PRICE_INPUT_PER_1M = 0.20
PRICE_OUTPUT_PER_1M = 1.20


# ---------------------------------------------------------------------------
# my rule for a correct answer (written before the first full run)
#   1. the name must match exactly (capital letters do not matter), yes/no too;
#   2. the number must match `value` rounded to `decimals`,
#      with a difference of at most 1 in the last digit.
#   3. no ANSWER line, or the loop hit the round limit = unanswered = not correct.
# ---------------------------------------------------------------------------
def is_correct(answer, question):
    if not answer:
        return False
    name, number = answer
    if name != question["answer"].lower():
        return False
    expected = round(question["value"], question["decimals"])
    return abs(number - expected) <= 10 ** -question["decimals"] + 1e-9


def make_client():
    load_dotenv()
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY is missing. Put it in the .env file.")
    return OpenAI(max_retries=5)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def pick_questions(ids):
    questions = strategies.load_questions()
    if not ids:
        return questions
    chosen = [q for q in questions if q["id"] in ids]
    if len(chosen) != len(set(ids)):
        sys.exit("Unknown question id in --questions")
    return chosen


def run_one(client, strategy, question, **options):
    try:
        result = STRATEGY_FUNCTIONS[strategy](client, question, **options)
    except Exception as problem:  # one bad question must not stop the whole run
        result = {"strategy": strategy, "question_id": question["id"], "final_text": "",
                  "answer": None, "unanswered": True, "input_tokens": 0, "output_tokens": 0,
                  "seconds": 0.0, "error": f"{type(problem).__name__}: {problem}"}
    result["correct"] = is_correct(result["answer"], question)
    return result


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------
def command_run(args):
    client = make_client()
    folder = OUTPUTS / f"run{args.run}"
    questions = pick_questions(args.questions)
    for strategy in args.strategies:
        for question in questions:
            path = folder / strategy / f"{question['id']}.json"
            if args.resume and path.exists():
                print(f"skip   {strategy} {question['id']} (already saved)")
                continue
            result = run_one(client, strategy, question)
            save_json(path, result)
            mark = "OK " if result["correct"] else "BAD"
            print(f"{mark} {strategy} {question['id']}  answer={result['answer']}  "
                  f"tokens={result['input_tokens']}+{result['output_tokens']}  "
                  f"{result['seconds']:.1f}s" + (f"  ERROR {result['error']}" if "error" in result else ""))
    save_json(folder / "meta.json", {
        "model": strategies.MODEL, "k": strategies.K,
        "s2_temperature_wanted": strategies.S2_TEMPERATURE,
        "temperature_supported": strategies.STATE["temperature_supported"],
        "max_rounds": strategies.MAX_ROUNDS,
        "reasoning_effort": strategies.REASONING_EFFORT,
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")})


def command_vague(args):
    client = make_client()
    vague_tools = tools.tools_with_vague_lookup()
    for question in pick_questions(args.questions):
        result = run_one(client, "S3", question, tool_list=vague_tools)
        save_json(OUTPUTS / "c1_vague" / f"{question['id']}.json", result)
        print(f"{question['id']}  calls={len(result.get('calls', []))}  "
              f"rounds={result.get('number_of_rounds')}  answer={result['answer']}  "
              f"correct={result['correct']}")


def command_tooltokens(_args):
    client = make_client()
    messages = [{"role": "system", "content": strategies.system_prompt("S3")},
                {"role": "user", "content": "Say hello."}]
    counts = {}
    for label, tool_list in (("without_tools", None), ("with_tools", tools.TOOLS)):
        response = strategies.chat(client, messages, tool_list=tool_list)
        counts[label] = response.usage.prompt_tokens
    counts["added_by_tool_definitions"] = counts["with_tools"] - counts["without_tools"]
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("o200k_base")
        counts["tiktoken_estimate_of_the_json"] = len(encoding.encode(json.dumps(tools.TOOLS)))
    except Exception:
        pass
    save_json(OUTPUTS / "tool_tokens.json", counts)
    print(json.dumps(counts, indent=2))


def load_run(run_number):
    """{strategy: {question_id: result}} for one run, or None if the run is missing."""
    folder = OUTPUTS / f"run{run_number}"
    if not folder.exists():
        return None
    return {s: {p.stem: load_json(p) for p in sorted((folder / s).glob("Q-*.json"))}
            for s in STRATEGY_FUNCTIONS if (folder / s).exists()}


def cost_of(in_tokens, out_tokens):
    if PRICE_INPUT_PER_1M is None or PRICE_OUTPUT_PER_1M is None:
        sys.exit("Fill in PRICE_INPUT_PER_1M and PRICE_OUTPUT_PER_1M at the top of run.py first.")
    return in_tokens * PRICE_INPUT_PER_1M / 1e6 + out_tokens * PRICE_OUTPUT_PER_1M / 1e6


def command_report(_args):
    questions = strategies.load_questions()
    by_id = {q["id"]: q for q in questions}
    runs = {n: load_run(n) for n in (1, 2)}
    lines = ["## Summary table", "",
             "| Run | Strategy | Correct /20 | Unanswered | Input tokens | Output tokens | "
             "Median seconds per question | Total seconds | Cost ($) |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for number, data in runs.items():
        if not data:
            continue
        for strategy, results in data.items():
            rows = list(results.values())
            in_t = sum(r["input_tokens"] for r in rows)
            out_t = sum(r["output_tokens"] for r in rows)
            seconds = [r["seconds"] for r in rows]
            lines.append(
                f"| {number} | {STRATEGY_NAMES[strategy]} | {sum(r['correct'] for r in rows)} | {sum(r['unanswered'] for r in rows)} | {in_t:,} | {out_t:,} | "
                f"{statistics.median(seconds):.1f} | {sum(seconds):.1f} | {cost_of(in_t, out_t):.4f} |")

    if runs[1]:
        lines += ["", "## Per question (run 1)", "", "| Question | S1 | S2 | S3 |", "|---|:---:|:---:|:---:|"]
        for q in questions:
            marks = []
            for s in ("S1", "S2", "S3"):
                r = runs[1].get(s, {}).get(q["id"])
                marks.append("-" if r is None else ("✓" if r["correct"] else "✗"))
            lines.append(f"| {q['id']} | " + " | ".join(marks) + " |")

    lines += ["", "## Wrong or unanswered answers (for C2)", ""]
    for number, data in runs.items():
        for strategy, results in (data or {}).items():
            for qid, r in results.items():
                if not r["correct"]:
                    q = by_id[qid]
                    lines.append(f"- run {number} {strategy} {qid}: model answer {r['answer']}, "
                                 f"expected {q['answer']} | {q['value']}"
                                 + (f", votes {r['votes']}" if "votes" in r else "")
                                 + (", HIT ROUND LIMIT" if r.get("hit_round_limit") else ""))

    lines += ["", "## Most expensive question per strategy (for C2)", ""]
    for number, data in runs.items():
        for strategy, results in (data or {}).items():
            qid, r = max(results.items(), key=lambda item: item[1]["input_tokens"] + item[1]["output_tokens"])
            lines.append(f"- run {number} {strategy}: {qid} with {r['input_tokens']:,} input and "
                         f"{r['output_tokens']:,} output tokens")

    if runs[1] and "S3" in runs[1]:
        lines += ["", "## S3 rounds and tool calls (run 1, for the final questions)", "",
                  "| Question | Rounds | Tool calls | Input tokens per round |", "|---|---:|---:|---|"]
        for qid, r in runs[1]["S3"].items():
            per_round = ", ".join(str(x["input_tokens"]) for x in r.get("rounds", []))
            lines.append(f"| {qid} | {r.get('number_of_rounds', '-')} | {len(r.get('calls', []))} | {per_round} |")

    if runs[1] and runs[2]:
        lines += ["", "## Questions where run 1 and run 2 differ (for C4)", ""]
        for strategy in STRATEGY_FUNCTIONS:
            a, b = runs[1].get(strategy, {}), runs[2].get(strategy, {})
            changed = [qid for qid in a if qid in b and a[qid]["correct"] != b[qid]["correct"]]
            lines.append(f"- {strategy}: {changed if changed else 'none'}")

    vague_folder = OUTPUTS / "c1_vague"
    if vague_folder.exists() and runs[1] and "S3" in runs[1]:
        lines += ["", "## C1 table", "",
                  "| Question | Calls (your description) | Calls (vague) | Answer (yours) | Answer (vague) |",
                  "|---|---:|---:|---|---|"]
        for path in sorted(vague_folder.glob("Q-*.json")):
            vague, mine = load_json(path), runs[1]["S3"].get(path.stem)
            if mine:
                lines.append(f"| {path.stem} | {len(mine.get('calls', []))} | {len(vague.get('calls', []))} | "
                             f"{mine['answer']} {'✓' if mine['correct'] else '✗'} | "
                             f"{vague['answer']} {'✓' if vague['correct'] else '✗'} |")

    text = "\n".join(lines) + "\n"
    (OUTPUTS / "report.md").write_text(text, encoding="utf-8")
    print(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--run", type=int, required=True, choices=[1, 2])
    run.add_argument("--strategies", nargs="+", default=["S1", "S2", "S3"], choices=["S1", "S2", "S3"])
    run.add_argument("--questions", nargs="*", default=None)
    run.add_argument("--resume", action="store_true")
    run.set_defaults(function=command_run)
    vague = sub.add_parser("vague")
    vague.add_argument("--questions", nargs="+", required=True)
    vague.set_defaults(function=command_vague)
    sub.add_parser("tooltokens").set_defaults(function=command_tooltokens)
    sub.add_parser("report").set_defaults(function=command_report)
    args = parser.parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
