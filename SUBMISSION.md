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

<!-- what changed in your plan, and why. "None" is an answer too. -->

### B2 — Tests

```text
<!-- pytest output -->
```

### B3 — The loop

- Round limit, and why:
- Where the logs are:
- Real Q-09 conversation compared with my A3 version, what is different:

### B4 — Three strategies

**What I kept the same:**

<!-- model, temperature, k, prompts, answer format, anything else -->

**My rule for a correct answer** (written before the first full run):

| Run | Strategy | Correct /20 | Unanswered | Input tokens | Output tokens | Median seconds per question | Total seconds | Cost ($) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | S1 direct | | | | | | | |
| 1 | S2 think and vote (k = ) | | | | | | | |
| 1 | S3 tools | | | | | | | |
| 2 | S1 direct | | | | | | | |
| 2 | S2 think and vote (k = ) | | | | | | | |
| 2 | S3 tools | | | | | | | |

**Per question (run 1):**

| Question | S1 | S2 | S3 |
|---|:---:|:---:|:---:|
| Q-01 | | | |
| Q-02 | | | |
| Q-03 | | | |
| Q-04 | | | |
| Q-05 | | | |
| Q-06 | | | |
| Q-07 | | | |
| Q-08 | | | |
| Q-09 | | | |
| Q-10 | | | |
| Q-11 | | | |
| Q-12 | | | |
| Q-13 | | | |
| Q-14 | | | |
| Q-15 | | | |
| Q-16 | | | |
| Q-17 | | | |
| Q-18 | | | |
| Q-19 | | | |
| Q-20 | | | |

---

## Part C — Explain and choose (Hard)

### C1 — Does the tool description matter?

| Question | Calls (your description) | Calls (vague) | Answer (yours) | Answer (vague) |
|---|---:|---:|---|---|
| | | | | |

### C2 — Three mistakes explained

### C3 — Which strategy I would use, and what would change it

### C4 — How sure I can be

### Final questions

1.
2.
3.
4.
5.
6.
7.
8.
