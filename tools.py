"""The two tools for HW4: lookup and calculate.

Both tools return a dict. They never raise an error to the caller.
If something goes wrong, they return {"error": "..."} that the model can read.
"""

import ast
import copy
import difflib
import functools
import json
import math
import re
from pathlib import Path

CORPUS_PATH = Path(__file__).resolve().parent / "data" / "corpus.jsonl"

# ---------------------------------------------------------------------------
# lookup
# ---------------------------------------------------------------------------

FIELDS = {
    "population_2025": "residents counted in the 2025 census",
    "population_2020": "residents counted in the 2020 census",
    "area_km2": "area in square kilometres",
    "budget_million_tenge": "2025 budget in million tenge",
    "water_use_megalitres": "household water use in 2025 in megalitres",
    "schools": "number of schools",
    "pupils": "number of pupils in the 2025/26 school year",
    "paved_road_km": "length of paved road in km",
    "founded_year": "year the district was founded",
    "water_tariff_tenge_per_m3": "2025 household water price in tenge per cubic metre",
}

UNITS = {
    "population_2025": "residents",
    "population_2020": "residents",
    "area_km2": "square kilometres",
    "budget_million_tenge": "million tenge",
    "water_use_megalitres": "megalitres",
    "schools": "schools",
    "pupils": "pupils",
    "paved_road_km": "km",
    "founded_year": "year",
    "water_tariff_tenge_per_m3": "tenge per cubic metre",
}

MAX_TEXT_LENGTH = 100  # longest district or field text we accept

# Each pattern is used on the text of one 2025 profile.
_NUMBER = r"([\d,]+(?:\.\d+)?)"
_POPULATION_PATTERNS = [
    # (regex, index of the 2025 group, index of the 2020 group)
    (r"recorded " + _NUMBER + r" residents; the 2020 census had recorded " + _NUMBER, 1, 2),
    (r"Census population: " + _NUMBER + r" in 2020 and " + _NUMBER + r" in 2025", 2, 1),
    (r"counted " + _NUMBER + r" residents, up from " + _NUMBER + r" at the 2020 census", 1, 2),
]


def _to_number(text):
    """'1,284.6' -> 1284.6 and '7,413' -> 7413."""
    text = text.replace(",", "")
    return float(text) if "." in text else int(text)


def _first(pattern, text):
    match = re.search(pattern, text)
    return _to_number(match.group(1)) if match else None


def _parse_profile(text):
    """Read the facts of one 2025 profile. Missing facts stay None."""
    facts = {
        "founded_year": _first(r"[Ff]ounded in (\d{4})", text),
        "area_km2": _first(_NUMBER + r" square kilometres", text),
        "budget_million_tenge": _first(_NUMBER + r" million tenge", text),
        "schools": _first(r"(\d+) schools", text),
        "pupils": _first(_NUMBER + r" pupils", text),
        "paved_road_km": _first(_NUMBER + r" km", text),
        "population_2025": None,
        "population_2020": None,
        "water_use_megalitres": None,
    }
    for pattern, i_2025, i_2020 in _POPULATION_PATTERNS:
        match = re.search(pattern, text)
        if match:
            facts["population_2025"] = _to_number(match.group(i_2025))
            facts["population_2020"] = _to_number(match.group(i_2020))
            break
    megalitres = re.search(_NUMBER + r" megalitres", text)
    cubic_metres = re.search(_NUMBER + r" cubic metres of water", text)
    if megalitres:
        facts["water_use_megalitres"] = _to_number(megalitres.group(1))
    elif cubic_metres:
        # One district gives cubic metres. 1 megalitre = 1,000 cubic metres.
        facts["water_use_megalitres"] = _to_number(cubic_metres.group(1)) / 1000
    return facts


@functools.lru_cache(maxsize=1)
def _load_data():
    """Read the corpus once. Archived profiles are skipped. Corrections are applied."""
    districts = {}
    corrections = []
    tariff = None
    with open(CORPUS_PATH, encoding="utf-8") as handle:
        documents = [json.loads(line) for line in handle if line.strip()]

    for doc in documents:
        title, text, doc_id = doc["title"], doc["text"], doc["id"]
        if "ARCHIVED" in title or "ARCHIVED" in text:
            continue  # old profile, superseded
        profile = re.fullmatch(r"(\w+) district profile \(2025\)", title)
        correction = re.match(r"Correction notice - (\w+)", title)
        if profile:
            name = profile.group(1)
            districts[name] = {"doc": doc_id, "facts": _parse_profile(text), "notes": {}}
        elif correction:
            corrections.append((correction.group(1), doc_id, text))
        elif title == "Household water tariff":
            tariff = (_first(r"tariff is " + _NUMBER + r" tenge per cubic metre", text), doc_id)

    # A correction notice takes precedence over the profile it corrects.
    for name, doc_id, text in corrections:
        if name not in districts:
            continue
        area = re.search(r"correct area is " + _NUMBER + r" square kilometres", text)
        if area:
            district = districts[name]
            district["facts"]["area_km2"] = _to_number(area.group(1))
            district["notes"]["area_km2"] = (
                f"corrected by {doc_id}; the profile {district['doc']} has a typing error",
                f"{district['doc']} (corrected by {doc_id})",
            )

    # The water use of one district is written in cubic metres. Say so in a note.
    for name, district in districts.items():
        text = _profile_text(district["doc"], documents)
        cubic_metres = re.search(_NUMBER + r" cubic metres of water", text)
        if cubic_metres:
            district["notes"]["water_use_megalitres"] = (
                f"{district['doc']} gives {cubic_metres.group(1)} cubic metres; "
                "converted to megalitres (1 megalitre = 1,000 cubic metres)",
                district["doc"],
            )
    return districts, tariff


def _profile_text(doc_id, documents):
    for doc in documents:
        if doc["id"] == doc_id:
            return doc["text"]
    return ""


def _short(text):
    text = str(text)
    return text if len(text) <= 40 else text[:37] + "..."


def _district_error(asked, names):
    """Build a clear error for a district name that did not match."""
    lowered = asked.casefold()
    prefix = [n for n in names if lowered and len(lowered) >= 2 and n.casefold().startswith(lowered)]
    if len(prefix) > 1:
        return (f"'{_short(asked)}' matches more than one district: "
                f"{', '.join(prefix)}. Use the full name.")
    close = difflib.get_close_matches(lowered, [n.casefold() for n in names], n=2, cutoff=0.6)
    suggestions = [n for n in names if n.casefold() in close]
    if prefix and prefix[0] not in suggestions:
        suggestions.insert(0, prefix[0])
    if suggestions:
        return f"no district named {_short(asked)}; did you mean {' or '.join(suggestions)}?"
    return f"no district named {_short(asked)}; the districts are: {', '.join(names)}"


def lookup(district, field):
    """Return one fact about one district from the 2025 profiles."""
    try:
        if not isinstance(district, str) or not district.strip():
            return {"error": "district must be a non-empty text"}
        if not isinstance(field, str) or not field.strip():
            return {"error": "field must be a non-empty text"}
        if len(district) > MAX_TEXT_LENGTH or len(field) > MAX_TEXT_LENGTH:
            return {"error": f"district and field must be shorter than {MAX_TEXT_LENGTH} characters"}

        field = field.strip()
        if field not in FIELDS:
            return {"error": f"unknown field '{_short(field)}'; use one of: {', '.join(FIELDS)}"}

        districts, tariff = _load_data()
        names = sorted(districts, key=lambda n: list(districts).index(n))
        asked = district.strip()

        if asked.casefold() == "region":
            if field != "water_tariff_tenge_per_m3":
                return {"error": "district 'region' only works with field water_tariff_tenge_per_m3"}
            matched = None
        else:
            matched = next((n for n in names if n.casefold() == asked.casefold()), None)
            if matched is None:
                return {"error": _district_error(asked, names)}

        if field == "water_tariff_tenge_per_m3":
            if tariff is None or tariff[0] is None:
                return {"error": "the water tariff was not found in the documents"}
            return {"district": matched or "region", "field": field, "value": tariff[0],
                    "unit": UNITS[field], "source": tariff[1],
                    "note": "the same price in every district"}

        entry = districts[matched]
        value = entry["facts"].get(field)
        if value is None:
            return {"error": f"the 2025 profile of {matched} has no value for {field}"}
        result = {"district": matched, "field": field, "value": value,
                  "unit": UNITS[field], "source": entry["doc"]}
        if field in entry["notes"]:
            note, source = entry["notes"][field]
            result["note"] = note
            result["source"] = source
        return result
    except Exception as problem:  # the tool must never crash
        return {"error": f"lookup failed: {type(problem).__name__}"}


# ---------------------------------------------------------------------------
# calculate
# ---------------------------------------------------------------------------

MAX_EXPRESSION_LENGTH = 200
MAX_ABS_VALUE = 1e15
MAX_DIGITS_OF_POWER = 15  # a power may not have more than about 15 digits


class CalculationError(Exception):
    """A problem the model can understand."""


def _check_size(value):
    if isinstance(value, complex) or not math.isfinite(value):
        raise CalculationError("the result is not a normal number")
    if abs(value) > MAX_ABS_VALUE:
        raise CalculationError("a number is too large (limit is 1e15)")
    return value


def _power(base, exponent):
    if base == 0 and exponent < 0:
        raise CalculationError("division by zero")
    if base < 0 and exponent != int(exponent):
        raise CalculationError("a negative number with a fractional power is not allowed")
    if abs(exponent) > 1000:
        raise CalculationError("the power is too large (limit is 1000)")
    # Check the size BEFORE the power is worked out, so 9**9**9 never runs.
    if abs(base) > 1 and abs(exponent) * math.log10(abs(base)) > MAX_DIGITS_OF_POWER:
        raise CalculationError("the result of the power would be too large (limit is 1e15)")
    return base ** exponent


def _divide(left, right):
    if right == 0:
        raise CalculationError("division by zero")
    return left / right


_BINARY = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: _divide,
    ast.Pow: _power,
}
_UNARY = {ast.UAdd: lambda a: +a, ast.USub: lambda a: -a}


def _evaluate(node):
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant):
        if type(node.value) in (int, float):  # bool, str and complex are refused
            return _check_size(node.value)
        raise CalculationError("only plain numbers are allowed")
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _check_size(_UNARY[type(node.op)](_evaluate(node.operand)))
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        left = _evaluate(node.left)
        right = _evaluate(node.right)
        return _check_size(_BINARY[type(node.op)](left, right))
    raise CalculationError(
        "only numbers, + - * / ** and brackets are allowed "
        f"(found: {type(node).__name__})")


def calculate(expression):
    """Work out an arithmetic expression safely. No eval, no exec."""
    try:
        if not isinstance(expression, str) or not expression.strip():
            return {"error": "expression must be a non-empty text"}
        if len(expression) > MAX_EXPRESSION_LENGTH:
            return {"error": f"expression is too long (limit is {MAX_EXPRESSION_LENGTH} characters)"}
        tree = ast.parse(expression.strip(), mode="eval")
        value = _evaluate(tree)
        if isinstance(value, float):
            value = round(value, 10)
            if value.is_integer():
                value = int(value)
        return {"expression": expression.strip(), "result": value}
    except CalculationError as problem:
        return {"error": str(problem)}
    except SyntaxError:
        return {"error": "this is not a valid arithmetic expression; "
                         "write numbers without commas, for example 44675 / 921.4"}
    except RecursionError:
        return {"error": "the expression is too deeply nested"}
    except Exception as problem:  # the tool must never crash
        return {"error": f"calculation failed: {type(problem).__name__}"}


# ---------------------------------------------------------------------------
# tool definitions (this is exactly what is sent to the model)
# ---------------------------------------------------------------------------

LOOKUP_DESCRIPTION = (
    "Find ONE fact about ONE district of the Nine Rivers Region (a made-up region) "
    "in its official 2025 profile. Returns the value, its unit and the id of the "
    "document it came from. Old ARCHIVED profiles are never used, correction notices "
    "are already applied, and water use is always given in megalitres. "
    "Call it once for each district and each field. "
    "Districts: Ossbridge, Ossford, Tarnvale, Kelmarsh, Brightwater, Stonecairn, "
    "Harrowfield, Lindenmoor, Redfen, Ashgrove, Millbrook, Coldharbour. "
    "Write the district exactly like this. "
    "For the water price use district 'region' and field 'water_tariff_tenge_per_m3'."
)

CALCULATE_DESCRIPTION = (
    "Work out an arithmetic expression exactly. Use it for EVERY calculation: "
    "add, subtract, multiply, divide, percentages and powers. "
    "Allowed: numbers, + - * / ** and brackets. Write numbers without commas, "
    "for example 44675 / 921.4. No variables and no functions. "
    "Do not round in the middle of a calculation; round only the final answer."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup",
            "description": LOOKUP_DESCRIPTION,
            "parameters": {
                "type": "object",
                "properties": {
                    "district": {
                        "type": "string",
                        "description": "District name, for example Millbrook, or 'region' for the water price.",
                    },
                    "field": {
                        "type": "string",
                        "enum": list(FIELDS),
                        "description": "Which fact to find: "
                        + "; ".join(f"{name} = {meaning}" for name, meaning in FIELDS.items()),
                    },
                },
                "required": ["district", "field"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": CALCULATE_DESCRIPTION,
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The arithmetic expression, for example 44675 / 921.4",
                    }
                },
                "required": ["expression"],
                "additionalProperties": False,
            },
        },
    },
]

VAGUE_LOOKUP_DESCRIPTION = "Looks things up."  # used only in part C1

TOOL_FUNCTIONS = {"lookup": lookup, "calculate": calculate}


def tools_with_vague_lookup():
    """Same tools, but the lookup description is one vague line (part C1)."""
    vague = copy.deepcopy(TOOLS)
    vague[0]["function"]["description"] = VAGUE_LOOKUP_DESCRIPTION
    return vague


def execute_tool(name, raw_arguments):
    """Check a tool request from the model and run it.

    `raw_arguments` is the string of JSON the model sent. Nothing runs
    until the JSON and the argument names and types are checked.
    """
    if name not in TOOL_FUNCTIONS:
        return {"error": f"unknown tool '{_short(name)}'; use lookup or calculate"}
    try:
        arguments = json.loads(raw_arguments)
    except (TypeError, ValueError):
        return {"error": "the arguments are not valid JSON"}
    if not isinstance(arguments, dict):
        return {"error": "the arguments must be a JSON object, for example {\"expression\": \"1 + 2\"}"}

    schema = next(t["function"]["parameters"] for t in TOOLS if t["function"]["name"] == name)
    for key in schema["required"]:
        if key not in arguments:
            return {"error": f"missing argument '{key}'"}
    for key, value in arguments.items():
        if key not in schema["properties"]:
            return {"error": f"unknown argument '{_short(key)}'"}
        if not isinstance(value, str):
            return {"error": f"argument '{key}' must be a string"}
    try:
        return TOOL_FUNCTIONS[name](**arguments)
    except Exception as problem:  # last safety net
        return {"error": f"tool failed: {type(problem).__name__}"}
