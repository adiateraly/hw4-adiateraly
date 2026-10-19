# HW4 — submission

**AI assistance:** I used Claude (an AI assistant) to help me plan the steps, to write the code and the tests, and to help me write the English text in this file. I ran the code myself on my own computer with my own API key. Every number in the tables comes from my own runs and my own logs.

---

## Part A — Plan on paper (Easy)

> Commit this whole part before any `.py` file exists.

### A1 — The steps

I use the question Q-09 as my example: *"Which district has the higher population density in 2025, Brightwater or Millbrook, and by how many residents per square kilometre?"*

| # | Step | What goes in (types) | What comes out (types) | When it goes wrong | Tool, loop, or model? |
|---|---|---|---|---|---|
| 1 | **Plan the question.** Decide which facts are needed and which formula to use. | `question: str` | A plan: a list of facts `[(district: str, field: str), ...]` and a formula as text. For Q-09: 4 facts (population and area of two districts) and "population / area". | The question is not clear: the model takes the most likely meaning and says its assumption. It names a district that does not exist: the error comes back from step 3. | model |
| 2 | **Run the tool requests.** Take each request from the model, check it, run it, and send the result back. Count the rounds. | One tool request: `id: str`, `name: str`, `arguments: str` (a string of JSON) | One tool message: `tool_call_id: str` (same id) and `content: str` (the result as JSON text) | The arguments are not valid JSON, are not an object, miss a name, have an extra name, or have a wrong type: no tool runs, and an error text is sent back for that id. The tool name is unknown: error text for that id. Every id always gets an answer. After 15 rounds the loop stops and the question is marked unanswered. | loop (`strategies.py`) |
| 3 | **Find one fact** in the 2025 profiles. | `district: str`, `field: str` (one of 10 field names) | `{district: str, field: str, value: int or float, unit: str, source: str, note: str (only sometimes)}` | Nothing found (name with a typing mistake): `{"error": str}` with the closest names. Two found (a short name like "Oss"): error that lists both names, nothing is guessed. Unknown field: error with the list of fields. Archived profile: it is never used. A correction notice exists: the corrected value is returned and the source says so. A different unit (cubic metres): converted to megalitres and a note says so. Wrong type, empty or very long text: error. | tool `lookup` |
| 4 | **Do arithmetic.** | `expression: str`, for example `"44675 / 921.4"` | `{expression: str, result: int or float}` | Not valid arithmetic, a name, a function call, a string, or an attribute: error, nothing is run. A comma in a number: error with a hint. Division by zero: error. A number or a power above 1e15 (like `9**9**9`): error before it is worked out. Empty text, wrong type, more than 200 characters: error. | tool `calculate` |
| 5 | **Compare, round and write the answer.** | The results of steps 3 and 4 (numbers) and the plan | `str` that ends with the line `ANSWER: <name or yes/no> \| <number>` | Two numbers are almost the same: the model uses the unrounded numbers from `calculate`. A tool error it cannot fix: it asks again with a corrected input. If it gives no answer line, step 6 marks the question unanswered. | model |
| 6 | **Check the answer.** | `text: str` and the question record (`answer: str`, `value: float`, `decimals: int`) | `(name: str, number: float)` or `None`, and `correct: bool` | There is no `ANSWER:` line, or the number cannot be read: `None`, so the question is unanswered and not correct. | code (`run.py`) |

**How the steps connect:**

```text
question (str)
     |
     v
[1 Plan] ----------------------------------------------+
     |  the model asks for a tool                       |
     v                                                  |
[2 Loop] --arguments (str)--> [3 lookup]    --fact (dict)--+--> back to the model (tool message)
     |   \--arguments (str)--> [4 calculate] --result (dict)-+
     |                                                  |
     |   (the model asks again: at most 15 rounds)      |
     v                                                  |
[5 Compare, round, write] <-----------------------------+
     |  text with the line "ANSWER: name | number"
     v
[6 Check] --> (name, number) --> correct: yes or no
```

Why this split is complete and has no overlap: every question needs the same six jobs. Someone has to decide what to find (1), pass the messages and keep control (2), read the documents (3), do arithmetic (4), judge and write the answer (5), and score it (6). Each job has exactly one owner and each owner does only that job. Step 3 only reads, step 4 only calculates, and step 5 never does arithmetic itself.

**What I am assuming:**

- Population means the 2025 census. Growth between censuses uses the 2020 census as the start: `(pop2025 / pop2020 - 1) * 100`.
- The budget is the 2025 budget. Water use is household use in calendar year 2025. A year has 365 days (2025 is not a leap year). One megalitre is 1,000 cubic metres and one cubic metre is 1,000 litres.
- Archived (2019) profiles NR-13 and NR-14 are never used. A correction notice wins over the profile it corrects (NR-16 changes the area of Brightwater from 912.4 to 921.4).
- NR-08 (Lindenmoor) gives water in cubic metres, so `lookup` changes it to megalitres. The tariff of 142.35 tenge per cubic metre (NR-15) is for 2025 and is the same in every district.
- In the Stonecairn and Coldharbour profiles the text says "up from", but the numbers are smaller than in 2020. I use the numbers, not the words.
- Density is residents per km2. Road density is km of road per km2.
- Rounding happens only in step 5, on the final number, to the number of decimals the question asks for. All tools keep full precision (up to 10 decimals).
- Lookup names must match exactly (capital letters do not matter). A wrong name is never guessed. The model must ask again with the right name.
- **The assumption my solution is most sensitive to:** archived profiles are ignored and the correction notice wins. For Q-09 the wrong area (912.4) would give Brightwater a density of 48.96 and a difference of only 0.08 (which rounds to 0.1). The right area (921.4) gives 48.49 and a difference of 0.56 (which rounds to 0.6). The winner is the same, but the number is wrong.

### A2 — The two tools

#### `lookup`

```json
{
  "type": "function",
  "function": {
    "name": "lookup",
    "description": "Find ONE fact about ONE district of the Nine Rivers Region (a made-up region) in its official 2025 profile. Returns the value, its unit and the id of the document it came from. Old ARCHIVED profiles are never used, correction notices are already applied, and water use is always given in megalitres. Call it once for each district and each field. Districts: Ossbridge, Ossford, Tarnvale, Kelmarsh, Brightwater, Stonecairn, Harrowfield, Lindenmoor, Redfen, Ashgrove, Millbrook, Coldharbour. Write the district exactly like this. For the water price use district 'region' and field 'water_tariff_tenge_per_m3'.",
    "parameters": {
      "type": "object",
      "properties": {
        "district": {
          "type": "string",
          "description": "District name, for example Millbrook, or 'region' for the water price."
        },
        "field": {
          "type": "string",
          "enum": [
            "population_2025",
            "population_2020",
            "area_km2",
            "budget_million_tenge",
            "water_use_megalitres",
            "schools",
            "pupils",
            "paved_road_km",
            "founded_year",
            "water_tariff_tenge_per_m3"
          ],
          "description": "Which fact to find: population_2025 = residents counted in the 2025 census; population_2020 = residents counted in the 2020 census; area_km2 = area in square kilometres; budget_million_tenge = 2025 budget in million tenge; water_use_megalitres = household water use in 2025 in megalitres; schools = number of schools; pupils = number of pupils in the 2025/26 school year; paved_road_km = length of paved road in km; founded_year = year the district was founded; water_tariff_tenge_per_m3 = 2025 household water price in tenge per cubic metre"
        }
      },
      "required": [
        "district",
        "field"
      ],
      "additionalProperties": false
    }
  }
}
```

| Case | What the tool returns |
|---|---|
| success | `{"district": "Millbrook", "field": "population_2025", "value": 37203, "unit": "residents", "source": "NR-11"}` |
| corrected value | `{"district": "Brightwater", "field": "area_km2", "value": 921.4, "unit": "square kilometres", "source": "NR-05 (corrected by NR-16)", "note": "..."}` |
| different unit | `{"district": "Lindenmoor", "field": "water_use_megalitres", "value": 2151.4, "unit": "megalitres", "source": "NR-08", "note": "NR-08 gives 2,151,400 cubic metres; converted to megalitres ..."}` |
| water price | `{"district": "region", "field": "water_tariff_tenge_per_m3", "value": 142.35, "unit": "tenge per cubic metre", "source": "NR-15", "note": "..."}` |
| name with a typing mistake | `{"error": "no district named Ossbrige; did you mean Ossbridge?"}` |
| short name that fits two districts | `{"error": "'Oss' matches more than one district: Ossbridge, Ossford. Use the full name."}` |
| name that is not close to any district | `{"error": "no district named xyz; the districts are: Ossbridge, Ossford, ..."}` |
| unknown field | `{"error": "unknown field 'mayor'; use one of: population_2025, ..."}` |
| 'region' with another field | `{"error": "district 'region' only works with field water_tariff_tenge_per_m3"}` |
| empty, wrong type, or longer than 100 characters | `{"error": "district must be a non-empty text"}` (or a similar short message) |
| old (archived) profile | Never returned. The tool only reads 2025 profiles. |

**Worst thing it could do with strange or dangerous input:** Nothing dangerous. It reads one fixed file in the project, and it never uses the input as a file name or as code. A very long input is refused (limit 100 characters), and the error message repeats at most 40 characters of the input. The worst case is an error message that does not help the model.

#### `calculate`

```json
{
  "type": "function",
  "function": {
    "name": "calculate",
    "description": "Work out an arithmetic expression exactly. Use it for EVERY calculation: add, subtract, multiply, divide, percentages and powers. Allowed: numbers, + - * / ** and brackets. Write numbers without commas, for example 44675 / 921.4. No variables and no functions. Do not round in the middle of a calculation; round only the final answer.",
    "parameters": {
      "type": "object",
      "properties": {
        "expression": {
          "type": "string",
          "description": "The arithmetic expression, for example 44675 / 921.4"
        }
      },
      "required": [
        "expression"
      ],
      "additionalProperties": false
    }
  }
}
```

| Case | What the tool returns |
|---|---|
| success | `{"expression": "44675 / 921.4", "result": 48.4859995659}` |
| not allowed part (call, attribute, name, string, True, complex number) | `{"error": "only numbers, + - * / ** and brackets are allowed (found: Call)"}` |
| number with a comma, or bad syntax | `{"error": "this is not a valid arithmetic expression; write numbers without commas, for example 44675 / 921.4"}` |
| division by zero | `{"error": "division by zero"}` |
| number or power too large (`9**9**9`, `10**400`) | `{"error": "the power is too large (limit is 1000)"}` or `{"error": "the result of the power would be too large (limit is 1e15)"}`, given before the power is worked out |
| empty, wrong type, or longer than 200 characters | `{"error": "expression must be a non-empty text"}` (or a similar short message) |

**Worst thing it could do with strange or dangerous input:** If I used `eval`, the model could run any Python code, for example delete files or read my API key. With `ast` I only allow numbers and the operators `+ - * / **`, so no code can run. The worst case is a wrong answer because the model wrote a wrong formula, or a small delay for a long expression. Long expressions (over 200 characters) and huge powers are refused.

### A3 — Q-09 by hand

I read NR-05 (Brightwater), NR-11 (Millbrook) and NR-16 (the correction). NR-05 says the area is 912.4, but NR-16 says this is a typing error and the right area is 921.4. The user message below is the question and the rule for the number of decimals. The system message is left out to keep the example short.

```json
[
  {
    "role": "user",
    "content": "Which district has the higher population density in 2025, Brightwater or Millbrook, and by how many residents per square kilometre?\n\nGive the number with 1 decimal places."
  },
  {
    "role": "assistant",
    "content": null,
    "tool_calls": [
      {
        "id": "call_1",
        "type": "function",
        "function": {
          "name": "lookup",
          "arguments": "{\"district\": \"Brightwater\", \"field\": \"population_2025\"}"
        }
      },
      {
        "id": "call_2",
        "type": "function",
        "function": {
          "name": "lookup",
          "arguments": "{\"district\": \"Brightwater\", \"field\": \"area_km2\"}"
        }
      },
      {
        "id": "call_3",
        "type": "function",
        "function": {
          "name": "lookup",
          "arguments": "{\"district\": \"Millbrook\", \"field\": \"population_2025\"}"
        }
      },
      {
        "id": "call_4",
        "type": "function",
        "function": {
          "name": "lookup",
          "arguments": "{\"district\": \"Millbrook\", \"field\": \"area_km2\"}"
        }
      }
    ]
  },
  {
    "role": "tool",
    "tool_call_id": "call_1",
    "content": "{\"district\": \"Brightwater\", \"field\": \"population_2025\", \"value\": 44675, \"unit\": \"residents\", \"source\": \"NR-05\"}"
  },
  {
    "role": "tool",
    "tool_call_id": "call_2",
    "content": "{\"district\": \"Brightwater\", \"field\": \"area_km2\", \"value\": 921.4, \"unit\": \"square kilometres\", \"source\": \"NR-05 (corrected by NR-16)\", \"note\": \"corrected by NR-16; the profile NR-05 has a typing error\"}"
  },
  {
    "role": "tool",
    "tool_call_id": "call_3",
    "content": "{\"district\": \"Millbrook\", \"field\": \"population_2025\", \"value\": 37203, \"unit\": \"residents\", \"source\": \"NR-11\"}"
  },
  {
    "role": "tool",
    "tool_call_id": "call_4",
    "content": "{\"district\": \"Millbrook\", \"field\": \"area_km2\", \"value\": 758.6, \"unit\": \"square kilometres\", \"source\": \"NR-11\"}"
  },
  {
    "role": "assistant",
    "content": null,
    "tool_calls": [
      {
        "id": "call_5",
        "type": "function",
        "function": {
          "name": "calculate",
          "arguments": "{\"expression\": \"44675 / 921.4\"}"
        }
      },
      {
        "id": "call_6",
        "type": "function",
        "function": {
          "name": "calculate",
          "arguments": "{\"expression\": \"37203 / 758.6\"}"
        }
      }
    ]
  },
  {
    "role": "tool",
    "tool_call_id": "call_5",
    "content": "{\"expression\": \"44675 / 921.4\", \"result\": 48.4859995659}"
  },
  {
    "role": "tool",
    "tool_call_id": "call_6",
    "content": "{\"expression\": \"37203 / 758.6\", \"result\": 49.0416556815}"
  },
  {
    "role": "assistant",
    "content": null,
    "tool_calls": [
      {
        "id": "call_7",
        "type": "function",
        "function": {
          "name": "calculate",
          "arguments": "{\"expression\": \"49.0416556815 - 48.4859995659\"}"
        }
      }
    ]
  },
  {
    "role": "tool",
    "tool_call_id": "call_7",
    "content": "{\"expression\": \"49.0416556815 - 48.4859995659\", \"result\": 0.5556561156}"
  },
  {
    "role": "assistant",
    "content": "Millbrook has the higher density: about 49.04 residents per km2. Brightwater has about 48.49. The difference is about 0.56, which is 0.6 with 1 decimal place.\nANSWER: Millbrook | 0.6"
  }
]
```

**My arithmetic:**

- Brightwater: 44,675 / 921.4. First, 921.4 x 48 = 44,227.2. Then 44,675 - 44,227.2 = 447.8. Then 447.8 / 921.4 = 0.486. So the density is 48.486 residents per km2.
- Millbrook: 37,203 / 758.6. First, 758.6 x 49 = 37,171.4. Then 37,203 - 37,171.4 = 31.6. Then 31.6 / 758.6 = 0.0417. So the density is 49.0417 residents per km2.
- Difference: 49.0417 - 48.4860 = 0.5557. Millbrook is higher. With 1 decimal place the answer is 0.6.
- Check with the wrong area from NR-05: 44,675 / 912.4 = 48.96 and the difference is only 0.08, which would give 0.1. So the correction notice matters.
- The final answer is `ANSWER: Millbrook | 0.6`.

### A4 — Why I split it this way

Another way is to make one tool for each calculation: `density(district)`, `growth(district)`, `water_per_resident(district)`, `budget_per_resident(district)`, and so on. The model would only choose a tool and a district, and my code would know every formula.

I did not choose this for four reasons. First, the twenty questions need more than ten different formulas, and some of them do not fit any ready tool (for example sums in Q-06 and Q-16, the growth projection in Q-18, and the range of three districts in Q-11). A new kind of question would need new code. Second, every tool definition is sent in every request, so ten or more tools make every request longer and more expensive. Third, the tools would overlap: `density` and `road_density` both read area and population, so I could not say which tool owns the reading of a fact. A fix in one place would not fix the others. Fourth, I want to test whether the model can plan the formula itself. With `lookup` and `calculate` the model keeps this job, but it cannot make arithmetic mistakes or read a wrong document. This gives me two small tools that do not overlap, and I can test each one alone.

---

## Part B — Build it and run it (Medium)

### What I changed from Part A while coding

The two tools, their definitions and the loop (limit of 15 rounds) are the same as in Part A. One thing was new. When I tried S3, the model refused tools together with reasoning in the Chat Completions API (error 400: "Function tools with reasoning_effort are not supported"). So I set `reasoning_effort` to `none` for all calls of all three strategies. I did this for S1 and S2 too, so the comparison stays fair.

### B2 — Tests

```text
=========== test session starts ===========
platform win32 -- Python 3.13.9, pytest-9.1.1, pluggy-1.7.0 -- C:\Users\KUNYA\Documents\hw4-adiateraly\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\KUNYA\Documents\hw4-adiateraly
plugins: anyio-4.15.1
collected 18 items

tests/test_tools.py::test_lookup_finds_a_correct_2025_number PASSED [  5%]
tests/test_tools.py::test_lookup_misspelled_name_gives_a_helpful_error PASSED [ 11%]
tests/test_tools.py::test_lookup_keeps_the_two_similar_names_apart PASSED [ 16%]
tests/test_tools.py::test_lookup_never_uses_an_archived_profile PASSED [ 22%]
tests/test_tools.py::test_lookup_applies_the_correction_notice PASSED [ 27%]
tests/test_tools.py::test_lookup_changes_cubic_metres_to_megalitres PASSED [ 33%]
tests/test_tools.py::test_lookup_unknown_field_and_bad_input_do_not_crash PASSED [ 38%]
tests/test_tools.py::test_lookup_water_price_and_region PASSED [ 44%]
tests/test_tools.py::test_lookup_reads_every_fact_of_every_district PASSED [ 50%]
tests/test_tools.py::test_calculate_gets_the_right_number PASSED [ 55%]
tests/test_tools.py::test_calculate_follows_the_order_of_operations PASSED [ 61%]
tests/test_tools.py::test_calculate_refuses_code_without_running_it PASSED [ 66%]
tests/test_tools.py::test_calculate_refuses_attribute_access PASSED [ 72%]
tests/test_tools.py::test_calculate_refuses_a_huge_power_fast PASSED [ 77%]
tests/test_tools.py::test_calculate_handles_division_by_zero PASSED [ 83%]
tests/test_tools.py::test_calculate_refuses_other_strange_input PASSED [ 88%]
tests/test_tools.py::test_execute_tool_runs_a_good_request PASSED [ 94%]
tests/test_tools.py::test_execute_tool_refuses_bad_requests_without_running_anything PASSED [100%]

=========== 18 passed in 0.24s ===========
```

### B3 — The loop

- Round limit, and why: 15 rounds (one round is one call to the model). In the worst case a question needs about 8 lookups and 3 calculations. If the model asks for one tool per round, that is 11 rounds, plus 1 round for the final answer. I added 3 rounds for the case where a tool returns an error and the model must ask again. A limit that is too low would cut good answers. A limit that is too high would let a confused model spend money. In run 1 the most rounds one question needed was 4 (Q-03, Q-04, Q-11 and Q-17), so no question came close to the limit.
- Where the logs are: `outputs/run1/S3/Q-01.json` to `Q-20.json` (and `outputs/run2/S3/` for the second run). Each file has every tool call with its id, tool name, arguments, result and seconds, the tokens of every round, and the whole conversation. The logs of S1 and S2 are in `outputs/run1/S1/`, `outputs/run1/S2/` and the same for run 2.
- Real Q-09 conversation compared with my A3 version, what is different (log: `outputs/run1/S3/Q-09.json`): the first part is the same as my hand version. In round 1 the model asked for the same 4 lookups at once (population and area of Brightwater and Millbrook), and the results are the same as mine, including `921.4` with the source "NR-05 (corrected by NR-16)". The difference is in the calculations. I planned 3 rounds of tools: two divisions, then one more calculation with their results. The real model did all 3 calculations in round 2, at the same time: `44675 / 921.4` (48.4859995659), `37203 / 758.6` (49.0416556815) and `44675 / 921.4 - 37203 / 758.6`. So it did not wait for the first two results. It wrote the numbers again in the third expression, and it put Brightwater first, so the tool returned a negative number, `-0.5556561156`. The model understood from the sign that Millbrook is higher and answered `ANSWER: Millbrook | 0.6`. In total the real run had 3 calls to the model and 7 tool calls (my hand version had 4 calls to the model and 7 tool calls). All 7 tool calls worked with no error, the input tokens were 3,240 and the output tokens were 218.

### B4 — Three strategies

**What I kept the same:**

- Model: `gpt-5.6-luna` for everything, through the Chat Completions API.
- The same 20 questions in the same order, from `data/questions.json`.
- The same rules text for the answer format (the `RULES` text in `strategies.py`) and the same user message: the question and "Give the number with N decimal places". N comes from the `decimals` field. The correct answer and the correct number are never put in a prompt.
- The same last line for every strategy: `ANSWER: <name or yes/no> | <number>`, and the same code that reads it and checks it (`parse_answer` and `is_correct`).
- S1 and S2 get the same 17 documents in the same prompt. S3 gets no documents, only the two tools. S2 differs from S1 only by "Think step by step" and k = 5.
- S2: k = 5 samples, asked one after the other, the most common answer wins (the number is rounded to the `decimals` of the question before voting; a tie goes to the answer seen first). Temperature 1.0 is asked for in S2 only. The model accepted it (`temperature_supported: true` in `outputs/run1/meta.json`).
- S1 and S3 use the default settings of the model, except `reasoning_effort`. I did not set a maximum number of tokens. `reasoning_effort` is `none` for every call of every strategy, so the model only "thinks" in the visible text, which is what the S2 prompt asks for.
- S3: the same two tool definitions in every request, at most 15 rounds.
- Time is measured with `time.perf_counter` around the whole work for one question (all 5 calls in S2, all rounds and tool calls in S3). Tokens come from the `usage` field of every call. Cost = input tokens x input price + output tokens x output price. I did not use a discount for cached tokens. Prices used: $0.20 per 1,000,000 input tokens and $1.20 per 1,000,000 output tokens (the constants at the top of `run.py`).

**My rule for a correct answer** (written before the first full run):

1. The name must match exactly (capital letters do not matter). For yes/no questions the word must be yes or no.
2. The number must match `value` rounded to `decimals`. A difference of 1 in the last digit is allowed. For example, with 2 decimals the answer 17.60 or 17.62 is correct for 17.61.
3. A reply with no `ANSWER:` line, or an S3 question that hit the round limit, is "unanswered" and counts as not correct.

Why this rule and why twenty questions: the twenty questions are given by the course, so I can compare my results with other students. They have many types (comparisons, sums, yes/no, percent, a unit trap, an archived profile and a correction notice). The rule is strict about the name, because a wrong district is a real mistake. It allows 1 digit of difference in the number, because a model can round a long number in a slightly different way and this is not a real mistake. I ran everything twice, because one run cannot show how much the results change by chance. Twenty questions are few. I say in C4 what this means.

| Run | Strategy | Correct /20 | Unanswered | Input tokens | Output tokens | Median seconds per question | Total seconds | Cost ($) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | S1 direct | 4 | 2 | 45,540 | 564 | 1.3 | 31.1 | 0.0098 |
| 1 | S2 think and vote (k = 5) | 15 | 0 | 228,400 | 9,551 | 8.7 | 185.4 | 0.0571 |
| 1 | S3 tools | 18 | 0 | 68,393 | 3,808 | 4.5 | 95.4 | 0.0182 |
| 2 | S1 direct | 5 | 2 | 45,540 | 582 | 1.2 | 30.1 | 0.0098 |
| 2 | S2 think and vote (k = 5) | 18 | 0 | 228,400 | 9,487 | 8.4 | 173.3 | 0.0571 |
| 2 | S3 tools | 18 | 0 | 70,897 | 3,869 | 4.8 | 103.9 | 0.0188 |

**Per question (run 1):**

| Question | S1 | S2 | S3 |
|---|:---:|:---:|:---:|
| Q-01 | ✗ | ✓ | ✓ |
| Q-02 | ✗ | ✓ | ✓ |
| Q-03 | ✗ | ✓ | ✓ |
| Q-04 | ✓ | ✓ | ✓ |
| Q-05 | ✗ | ✗ | ✓ |
| Q-06 | ✗ | ✓ | ✓ |
| Q-07 | ✗ | ✓ | ✓ |
| Q-08 | ✗ | ✓ | ✓ |
| Q-09 | ✗ | ✓ | ✓ |
| Q-10 | ✓ | ✓ | ✓ |
| Q-11 | ✗ | ✓ | ✓ |
| Q-12 | ✗ | ✓ | ✓ |
| Q-13 | ✗ | ✓ | ✓ |
| Q-14 | ✗ | ✗ | ✓ |
| Q-15 | ✗ | ✗ | ✓ |
| Q-16 | ✓ | ✓ | ✓ |
| Q-17 | ✓ | ✗ | ✗ |
| Q-18 | ✗ | ✓ | ✓ |
| Q-19 | ✗ | ✓ | ✓ |
| Q-20 | ✗ | ✗ | ✗ |

---

## Part C — Explain and choose (Hard)

### C1 — Does the tool description matter?

I ran S3 again on five questions with the `lookup` description changed to one line: `"Looks things up."`. The field names and their meanings in the parameters stayed the same. The model, the questions and the answer format also stayed the same. I chose Q-03 (a unit trap), Q-08 (needs the water price), Q-09 (a correction notice), Q-14 (an archived profile) and Q-20 (many facts).

| Question | Calls (your description) | Calls (vague) | Answer (yours) | Answer (vague) |
|---|---:|---:|---|---|
| Q-03 | 7 | 5 | lindenmoor 5.3 ✓ | lindenmoor 5.3 ✓ |
| Q-08 | 4 | 4 | brightwater 72.46 ✓ | brightwater 72.46 ✓ |
| Q-09 | 7 | 5 | millbrook 0.6 ✓ | millbrook 0.6 ✓ |
| Q-14 | 5 | 5 | ashgrove 4.9 ✓ | ashgrove 4.9 ✓ |
| Q-20 | 7 | 10 | ashgrove 890 ✗ | ashgrove 2993 ✓ |

What changed: very little. Four answers were the same. The number of calls was the same in two questions, 2 lower in two questions (Q-03 and Q-09) and 3 higher in Q-20. I did not open the logs to see why the number of calls changed.

Why the description mattered so little here: my code does the hard work, not the description. `lookup` already ignores archived profiles, applies the correction notice and changes cubic metres to megalitres, so the model does not need to know this. The model still saw the list of field names, with their meanings, in the `field` parameter. This was enough to choose the right field, and even to use the district `region` for the water price in Q-08. The long description would matter more for things that the code cannot guess, for example the exact spelling of the 12 district names. Here the model spelled all names right.

The Q-20 result looks like a big win for the vague description, but I do not trust it. With my own description S3 gave 890 in both runs, and with the vague one it gave 2993 once. One run per question cannot show that the vague description is better. It could be luck. In C2 I show why Q-20 fails in my normal runs.

### C2 — Three mistakes explained

**S1, Q-09 (wrong in both runs).** The right answer is Millbrook, 0.6 (49.04 against 48.49 residents per km2). In `outputs/run1/S1/Q-09.json` the model wrote: "Brightwater has the higher population density by 0.4 residents per square kilometre. ANSWER: Brightwater | 0.4". The log shows `output_tokens: 30`, so the model wrote no steps. It gave the answer straight away, and it even picked the wrong district. In run 2 it was wrong again (brightwater, 0.2). The old area in NR-05 (912.4) does not explain this: with 912.4 Brightwater would have 48.96 and Millbrook would still be higher. So the most likely reason is that the model did the two divisions (44,675 / 921.4 and 37,203 / 758.6) in its head and got them wrong. I cannot see its numbers because S1 shows no steps.

The principle: a language model writes one token after another. It has no exact division inside. With no steps, it guesses a number that looks right. A division like 37,203 / 758.6 has many small steps, and every step can go wrong. Here the two densities are close, so a small error changes the winner. This fits the rest of S1: it was right in both runs only on Q-04 (a small division), Q-10 (it only compares two years) and Q-16 (an addition). It had 4 and 5 correct answers out of 20 in total.

**S2, Q-14 (wrong in run 1, right in run 2).** The right answer is Ashgrove, 4.9 (Tarnvale uses 199.83 litres and Ashgrove 204.69 litres per resident per day, so the difference is 4.85). In `outputs/run1/S2/Q-14.json` the five samples gave: Ashgrove 4.7 (2 samples), Tarnvale 0.0, Tarnvale 0.2 and Ashgrove 0.0. The vote picked Ashgrove 4.7, which is wrong. Two things went wrong:

- Three samples made the same unit mistake. For example: "5,207 megalitres ÷ 71,388 residents ÷ 365 days × 1,000 = 0.2 litres per resident per day". One megalitre is 1,000,000 litres, not 1,000, so these samples were 1,000 times too small.
- The two samples with 4.7 did the long divisions in their heads and rounded in the middle: they wrote 199.9 and 204.6 (the right values are 199.83 and 204.69). The difference of these two rounded numbers is 4.7, not 4.9. Both samples made the same kind of error, so they agreed on the same wrong number.

Why voting fixes some mistakes and not others: asking five times and voting removes random mistakes. If each sample goes wrong in a different way, the wrong answers are spread out, and the right answer, which repeats, wins. Voting cannot remove a mistake that is shared by the samples (a bias). Here three samples made the same unit mistake, and two made the same rounding mistake, so the vote copied the mistake. It also fails when no sample is right: the answer 4.9 did not appear in any of the five samples. And it fails when every answer is different. In Q-05 (run 1) the five samples gave 14222, 14338, 14296, 14345 and 14346, one vote each, so the first one won, and it was wrong. For numbers with 5 digits and 0 decimals, the model must be exact, and mental arithmetic is not exact. The price is also high: S2 sent 228,400 input tokens against 45,540 for S1, which is 5.0 times more, because the same long prompt is sent five times. I also did not run "think step by step" without voting, so I cannot say how much of S2's improvement (4 to 15 and 5 to 18) comes from the voting and how much from the steps.

**S3, Q-17 (wrong in run 1, right in run 2).** The right answer is Harrowfield, 884 (11,276.03 against 10,391.57 tenge per resident). In `outputs/run1/S3/Q-17.json` the model did 5 lookups in round 1, and all results were right (for example Harrowfield 7146 megalitres and 90212 residents, Ossbridge 3862 megalitres and 52904 residents, tariff 142.35). Then:

- Round 2: it sent `abs((7146*1000*142.35/90212)-(3862*1000*142.35/52904))`. My tool refused it: "only numbers, + - * / ** and brackets are allowed (found: Call)". The tool worked as I designed it.
- Round 3: the model tried a trick and sent `((7146*1000*142.35/90212)-(3862*1000*142.35/52904))**2**0.5`. It probably wanted the absolute value. But in Python `a**2**0.5` means `a**(2**0.5)`, not `(a**2)**0.5`. The tool returned `14697.0543064582`, which is the exact value of the wrong formula.
- Round 4: the model wrote "paid more, by 14697 tenge per resident". The right difference is 884.

Why a calculator removes some mistakes: the arithmetic inside `calculate` is exact and runs in code, so for the expressions it accepts, the error of the calculation is zero. The model cannot reach that on its own, as S1 and S2 showed. But the tool cannot check the formula. It did the wrong formula perfectly. In run 2 S3 got Q-17 right, so this was a random slip and not a fixed error. S3 also failed Q-20 in both runs (890 instead of 2993). In `outputs/run1/S3/Q-20.json` the model did 6 lookups, including the budget and population of Ossbridge, but only one calculation: `(10488.1*1000000/58760)-(16021.7*1000000/90212)` = 889.93. It never worked out Ossbridge per resident (175,497 tenge), which is the lowest of the three, and it wrote that Harrowfield is "the lowest". So the calculator removes arithmetic mistakes, but it does not remove planning mistakes.

Why the loop needed several rounds and why every round costs more: the model can only ask for a calculation after it has the numbers, and an error needs one more round (Q-17 had 4 rounds because of the error in round 2). Every round sends the whole conversation again: the system text, the question, the 600 tokens of tool definitions, and all earlier tool calls and results. In Q-17 the input tokens per round were 833, 1,203, 1,278 and 1,386. Round 2 added the five lookup results (+370), round 3 added the error message (+75), and round 4 added the second calculation (+108). So the cost grows with every round.

### C3 — Which strategy I would use, and what would change it

I would use **S3 (tools)** for this problem.

| | S1 direct | S2 think and vote | S3 tools |
|---|---:|---:|---:|
| Correct /20 (run 1, run 2) | 4, 5 | 15, 18 | 18, 18 |
| Cost for 20 questions (run 1) | $0.0098 | $0.0571 | $0.0182 |
| Total time (run 1) | 31.1 s | 185.4 s | 95.4 s |

S3 had the best accuracy in both runs, the second lowest cost and the second lowest time. It gets facts from the tool (no reading of 17 documents by the model, and no mistakes with archived profiles, because the code ignores them) and does the arithmetic in code, which the principles say is exact.

Why I did not choose S1: it is cheap ($0.0098) and fast (1.3 seconds per question), but it got only 4 and 5 answers right out of 20. A cheap wrong answer has no value here, because the questions need arithmetic on big numbers (see Q-09).

Why I did not choose S2: it costs 3.1 times more than S3 ($0.0571 against $0.0182) and takes 1.9 times longer (185.4 s against 95.4 s). It is not more accurate than S3 (15 and 18 against 18 and 18). It has no calculator, so the mental arithmetic mistakes stay (Q-14), and voting cannot fix shared mistakes.

Situations that would change my choice:

1. **Questions with no arithmetic and few documents** (like Q-10, which all three strategies got right in both runs). Then I would use S1, because it is the cheapest and the fastest.
2. **1,000 times more documents.** Now the 17 documents are about 2,200 tokens, and S1 and S2 send them with every call. With 1,000 times more, they would not fit in the prompt. I would use S3 with a lookup that searches an index (see final question 6).
3. **A strict time limit** (an answer in about one second). S1 has a median of 1.3 seconds, S3 has 4.5 seconds. I would use S1 and accept the mistakes.
4. **A very small budget** with some mistakes allowed: S1 costs about half of S3. If the questions have no tools and a lot of arithmetic, I would use S2 instead of S1, because it was much better than S1 (15 and 18 against 4 and 5).

### C4 — How sure can I be?

**How different were my two runs?** S1 had 4 and 5 correct, S2 had 15 and 18, S3 had 18 and 18. The totals look stable for S3, but the questions changed: S3 failed Q-17 in run 1 and Q-08 in run 2 (in run 2 its answer was 72456.15 instead of 72.46, a unit slip). In total, the answer of 3 questions changed for S1 (Q-01, Q-03, Q-17), 3 for S2 (Q-14, Q-15, Q-17) and 2 for S3 (Q-08, Q-17). So about 2 or 3 questions out of 20 (10 to 15 percent) can flip between two runs of the same strategy.

**Is the difference between the two best strategies bigger than that?** No. S3 had 18 and 18 and S2 had 15 and 18. The average difference is 1.5 questions, and S2 itself moved by 3 questions between its two runs. If I put both runs together, S3 was right 36 times out of 40 (90%) and S2 33 times out of 40 (82.5%). The difference is 7.5 points, and its standard error is about 7.7 points, so it is not clear. This is a rough number, because the runs use the same 20 questions. S1 is a different case: its average is 4.5 against 16.5 for S2 and 18 for S3. That is a gap of 12 or more questions, much bigger than any change between runs. So I am sure that S1 is the worst for this problem. I am not sure that S3 is more accurate than S2. The cost and time differences are large and equal in both runs (S2 costs 3.1 times more than S3 and takes 1.9 times longer), so I am more sure about those.

**How many questions would I need?** With an accuracy of about 90% on 20 questions, the standard error is already about 6.7 points. To trust a difference of 7.5 points (90% against 82.5%) at the usual 95% level, I need about 160 questions per strategy, from the usual formula for two proportions. I would also repeat every run a few times, because the answers of the same question change between runs. Twenty questions are enough to see big gaps (S1 against the rest) and not enough to rank S2 and S3.

### Final questions

1. **When the model sends a `tool_calls` message, what has actually run so far?** Nothing has run. The message is only a request written by the model, with a tool name, the arguments and an id. My loop runs the functions, and then sends back a `tool` message with the same id. In Q-17 round 1, the model asked for 5 lookups at once, and they only ran when my code called them (each took about 0.00005 seconds).
2. **Why does `arguments` arrive as a string, and what goes wrong if you pass it straight into your function?** The model only writes text, so the API gives the arguments as a string of JSON text. If I pass the string into `lookup`, it fails, because a string is not a dictionary with `district` and `field`. The JSON can also be broken, or have missing or extra names. So `execute_tool` first does `json.loads`, then checks that it is an object with the right names and types, and returns an error text to the model if not (there is a test for this).
3. **How many tokens do your two tool definitions add to every S3 request?** About 600 tokens. I measured it with `python run.py tooltokens`: the same request had 187 input tokens without the tools and 787 with them. A count of the tool JSON with tiktoken gave 602, which is almost the same. About 600 of the 820 input tokens in the first round of an S3 question are the tool definitions, and they are sent again in every round (3 or 4 rounds per question, so about 1,800 to 2,400 tokens per question).
4. **How much more did S2 cost than S1?** S2 cost $0.0571 and S1 cost $0.0098 in run 1, so S2 cost 5.8 times more (the same in run 2). The input tokens are 228,400 against 45,540, which is 5.0 times more, because S2 sends the same prompt with all documents 5 times. The output tokens are 9,551 against 564, which is 17 times more, because S2 writes its steps. Output tokens also cost 6 times more than input tokens (1.20 against 0.20 dollars per million).
5. **Which question needed the most rounds in S3, and why?** Four questions needed 4 rounds in run 1: Q-03, Q-04, Q-11 and Q-17. Q-11 needed the most tool calls (10) and the most input tokens (4,775), because it needs two facts for each of three districts. For Q-17 I know the reason from the log: the first calculation used `abs()`, my tool refused it, and the model had to try again in round 3.
6. **What would you change in `lookup` if there were 100,000 documents?** Now `lookup` reads the 17 documents when it starts, finds the facts with regular expressions, and keeps everything in memory. This works only because there are few documents and three fixed formats. With 100,000 documents I would build an index once (a database or a search index, with BM25 or embeddings) and keep the district, the year and the archived or corrected status of each document in it. Then `lookup` would ask the index for the best few passages, skip archived ones, and return a short result, so that the S3 requests do not become big. I would still check an exact name first (Ossbridge and Ossford are close).
7. **What stops your `calculate` from running dangerous code? Could the model still make it misbehave?** `calculate` reads the text with `ast.parse` and only allows numbers and the operators `+ - * / **` with brackets. Names, calls, attributes and strings are refused and never run, and there is no `eval`. Numbers above 1e15, huge powers (checked before they are worked out) and expressions over 200 characters are refused. The model can still make it give a wrong result with a valid formula: in Q-17 it sent `...**2**0.5` and the tool returned 14697.05 instead of 884.46, which is exact for that formula but wrong for the question.
8. **For which kind of question did tools help most, and for which did they not help at all?** Tools helped most with questions that have a long chain of arithmetic on big numbers: S3 got 18 of 20 in both runs, against 4 and 5 for S1. They did not help with questions that need almost no arithmetic, like Q-10 (compare two years), where all three strategies were right in both runs, so S3 only cost more. They also did not help when the mistake was in the plan or the formula and not in the arithmetic: Q-20 (890 instead of 2993 in both runs) and Q-17 in run 1.
