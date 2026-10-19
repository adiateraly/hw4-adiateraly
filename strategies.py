"""The three strategies for HW4.

S1  direct         : all documents in the prompt, one call.
S2  think and vote : same prompt, think step by step, ask K times, take the most common answer.
S3  tools          : no documents in the prompt, the model uses lookup and calculate.

All three end with the same line:  ANSWER: <name or yes/no> | <number>
"""

import json
import re
import time
from collections import Counter
from pathlib import Path

import openai

import tools

MODEL = "gpt-5.6-luna"
K = 5                  # number of samples in S2
S2_TEMPERATURE = 1.0   # S2 needs different answers; used only if the model allows it
MAX_ROUNDS = 15        # most model calls in the S3 loop for one question
# The model does not allow tools together with reasoning in Chat Completions.
# So reasoning is switched off for ALL calls, to keep the three strategies the same.
REASONING_EFFORT = "none"

DATA_DIR = Path(__file__).resolve().parent / "data"

# Set to False the first time the model refuses the temperature setting.
STATE = {"temperature_supported": True}

# ---------------------------------------------------------------------------
# data and prompts
# ---------------------------------------------------------------------------


def load_questions():
    with open(DATA_DIR / "questions.json", encoding="utf-8") as handle:
        return json.load(handle)


def load_documents_text():
    """All 17 documents as one block of text for S1 and S2."""
    parts = []
    with open(DATA_DIR / "corpus.jsonl", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                doc = json.loads(line)
                parts.append(f"[{doc['id']}] {doc['title']}\n{doc['text']}")
    return "\n\n".join(parts)


RULES = (
    "You answer questions about the Nine Rivers Region. It is a made-up region, "
    "so you must not use any outside knowledge.\n"
    "Rules for your answer:\n"
    "- The last line of your reply must be exactly: ANSWER: <name or yes/no> | <number>\n"
    "- <name or yes/no> is one district name, written as in the question, or the word yes or no.\n"
    "- <number> is one number with no unit, no % sign and no comma. "
    "It is never negative: if the question asks for a difference, give its size.\n"
    "- Round only the final number, to the number of decimal places the user asks for."
)


def system_prompt(strategy):
    if strategy == "S1":
        return (RULES + "\nUse only the documents below. Give the answer directly and briefly.\n\n"
                "DOCUMENTS:\n\n" + load_documents_text())
    if strategy == "S2":
        return (RULES + "\nUse only the documents below. Think step by step. "
                "Write your reasoning, then the final line.\n\n"
                "DOCUMENTS:\n\n" + load_documents_text())
    if strategy == "S3":
        return (RULES + "\nYou have two tools. Use lookup to get every fact. "
                "Use calculate for every calculation. "
                "Do not guess facts and do not do arithmetic in your head. "
                "When you have the numbers, write the final line.")
    raise ValueError(strategy)


def user_prompt(question):
    # Only the question text and the number of decimals. The correct answer is never used.
    return f"{question['question']}\n\nGive the number with {question['decimals']} decimal places."


# ---------------------------------------------------------------------------
# answer line
# ---------------------------------------------------------------------------

_ANSWER_RE = re.compile(r"ANSWER:\s*([^|\n]+?)\s*\|\s*(-?[\d,]*\.?\d+)")


def parse_answer(text):
    """Return (name, number) from the LAST answer line, or None."""
    if not text:
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    name, number = matches[-1]
    name = name.strip().strip("*`'\" ").lower()
    try:
        return name, float(number.replace(",", ""))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# model calls
# ---------------------------------------------------------------------------


def chat(client, messages, tool_list=None, temperature=None):
    """One call to the model. Returns the response object."""
    arguments = {"model": MODEL, "messages": messages, "reasoning_effort": REASONING_EFFORT}
    if tool_list is not None:
        arguments["tools"] = tool_list
    if temperature is not None and STATE["temperature_supported"]:
        arguments["temperature"] = temperature
    try:
        return client.chat.completions.create(**arguments)
    except openai.BadRequestError as problem:
        if "temperature" in str(problem).lower() and "temperature" in arguments:
            STATE["temperature_supported"] = False
            print("NOTE: the model does not allow temperature. Calls are made without it.")
            del arguments["temperature"]
            return client.chat.completions.create(**arguments)
        raise


def _usage(response):
    usage = response.usage
    return (usage.prompt_tokens if usage else 0), (usage.completion_tokens if usage else 0)


def _result(strategy, question, text, answer, seconds, in_tokens, out_tokens, **extra):
    return {
        "strategy": strategy,
        "question_id": question["id"],
        "final_text": text,
        "answer": list(answer) if answer else None,
        "unanswered": answer is None,
        "input_tokens": in_tokens,
        "output_tokens": out_tokens,
        "seconds": round(seconds, 3),
        **extra,
    }


# ---------------------------------------------------------------------------
# the strategies
# ---------------------------------------------------------------------------


def run_s1(client, question):
    started = time.perf_counter()
    messages = [{"role": "system", "content": system_prompt("S1")},
                {"role": "user", "content": user_prompt(question)}]
    response = chat(client, messages)
    text = response.choices[0].message.content or ""
    in_tokens, out_tokens = _usage(response)
    return _result("S1", question, text, parse_answer(text),
                   time.perf_counter() - started, in_tokens, out_tokens)


def run_s2(client, question, k=K):
    started = time.perf_counter()
    messages = [{"role": "system", "content": system_prompt("S2")},
                {"role": "user", "content": user_prompt(question)}]
    samples, votes = [], Counter()
    total_in = total_out = 0
    for _ in range(k):
        response = chat(client, messages, temperature=S2_TEMPERATURE)
        text = response.choices[0].message.content or ""
        in_tokens, out_tokens = _usage(response)
        total_in += in_tokens
        total_out += out_tokens
        parsed = parse_answer(text)
        samples.append({"text": text, "answer": list(parsed) if parsed else None,
                        "input_tokens": in_tokens, "output_tokens": out_tokens})
        if parsed:
            # The vote key rounds the number, so 0.55 and 0.5500 are the same answer.
            votes[(parsed[0], round(parsed[1], question["decimals"]))] += 1
    winner = votes.most_common(1)[0][0] if votes else None  # a tie goes to the first one seen
    vote_list = [{"answer": list(key), "votes": count} for key, count in votes.most_common()]
    return _result("S2", question, samples[-1]["text"] if samples else "", winner,
                   time.perf_counter() - started, total_in, total_out,
                   samples=samples, votes=vote_list, k=k,
                   temperature_used=STATE["temperature_supported"])


def run_s3(client, question, tool_list=None, max_rounds=MAX_ROUNDS):
    """The tool loop. The model asks for tools, our code runs them."""
    tool_list = tool_list if tool_list is not None else tools.TOOLS
    started = time.perf_counter()
    messages = [{"role": "system", "content": system_prompt("S3")},
                {"role": "user", "content": user_prompt(question)}]
    calls, rounds = [], []
    total_in = total_out = 0
    text, hit_limit = "", False

    for round_number in range(1, max_rounds + 1):
        response = chat(client, messages, tool_list=tool_list)
        message = response.choices[0].message
        in_tokens, out_tokens = _usage(response)
        total_in += in_tokens
        total_out += out_tokens
        rounds.append({"round": round_number, "input_tokens": in_tokens,
                       "output_tokens": out_tokens,
                       "tool_calls": len(message.tool_calls or [])})

        if not message.tool_calls:           # the model gave its final answer
            text = message.content or ""
            break
        if round_number == max_rounds:       # still asking for tools: stop
            hit_limit = True
            break

        messages.append(message)             # the model's message, unchanged
        for tool_call in message.tool_calls:  # an answer for EVERY tool_call_id
            call_started = time.perf_counter()
            result = tools.execute_tool(tool_call.function.name, tool_call.function.arguments)
            call_seconds = time.perf_counter() - call_started
            content = json.dumps(result, ensure_ascii=False)
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": content})
            calls.append({"round": round_number, "tool_call_id": tool_call.id,
                          "tool": tool_call.function.name,
                          "arguments": tool_call.function.arguments,
                          "result": result, "seconds": round(call_seconds, 6)})

    answer = None if hit_limit else parse_answer(text)
    return _result("S3", question, text, answer, time.perf_counter() - started,
                   total_in, total_out, calls=calls, rounds=rounds,
                   number_of_rounds=len(rounds), hit_round_limit=hit_limit,
                   conversation=[m if isinstance(m, dict) else m.model_dump(exclude_none=True)
                                 for m in messages[2:]])
