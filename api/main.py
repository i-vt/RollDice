from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import random
import re
from typing import Optional

app = FastAPI(
    title="DnD Dice Roller API",
    description="Roll any combination of DnD dice. Supports standard notation like 2d6+3, d20, 4d6kh3",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VALID_DICE = [2, 4, 6, 8, 10, 12, 20, 100]

class RollRequest(BaseModel):
    notation: str = Field(..., example="2d6+3", description="Dice notation like 2d6, d20, 4d6kh3, 2d10+5")
    label: Optional[str] = Field(None, example="Attack Roll", description="Optional label for this roll")

class SingleDieResult(BaseModel):
    die: int
    value: int
    kept: bool

class RollResponse(BaseModel):
    notation: str
    label: Optional[str]
    dice_results: list[SingleDieResult]
    modifier: int
    subtotal: int
    total: int
    breakdown: str
    success: bool

def parse_single_group(token: str):
    """
    Parse a single dice group token, e.g. '2d6', '4d6kh3', 'd20'.
    Returns (count, sides, keep_info).
    Does NOT handle numeric-only tokens (those are modifiers).
    """
    token = token.strip().lower()
    pattern = r'^(\d*)d(\d+)(?:(kh|kl)(\d+))?$'
    match = re.match(pattern, token, re.IGNORECASE)
    if not match:
        raise ValueError(f"Invalid dice group: '{token}'. Use formats like d20, 2d6, 4d6kh3")

    count_str, sides_str, keep_type, keep_count_str = match.groups()
    count = int(count_str) if count_str else 1
    sides = int(sides_str)

    if count < 1 or count > 100:
        raise ValueError("Die count must be between 1 and 100")
    if sides not in VALID_DICE:
        raise ValueError(f"Invalid die type d{sides}. Valid dice: {', '.join(f'd{d}' for d in VALID_DICE)}")

    keep_info = None
    if keep_type and keep_count_str:
        keep_n = int(keep_count_str)
        if keep_n < 1 or keep_n >= count:
            raise ValueError(f"Keep count must be between 1 and {count - 1}")
        keep_info = (keep_type.lower(), keep_n)

    return count, sides, keep_info


def parse_notation(notation: str):
    """
    Parse full dice notation supporting multiple dice groups and a flat modifier.
    Examples:
      d20, 2d6, 4d6kh3, 2d6+3, 1d4+3d6, 1d4+2d6+1d8+5, 2d20kh1-1
    Returns list of (count, sides, keep_info) and a flat integer modifier.
    """
    notation = notation.strip().lower().replace(" ", "")
    if not notation:
        raise ValueError("Notation cannot be empty")

    # Tokenise: split on + and -, keeping the sign with each token.
    # e.g. "1d4+3d6-1" -> ["1d4", "+3d6", "-1"]
    tokens = re.split(r'(?=[+-])', notation)
    tokens = [t for t in tokens if t]  # drop empty strings

    groups = []   # list of (count, sides, keep_info)
    modifier = 0  # flat numeric modifier total

    for token in tokens:
        sign = 1
        if token.startswith('+'):
            token = token[1:]
        elif token.startswith('-'):
            sign = -1
            token = token[1:]

        if re.fullmatch(r'\d+', token):
            # Pure number → flat modifier
            modifier += sign * int(token)
        elif 'd' in token:
            if sign == -1:
                raise ValueError(f"Negative dice groups are not supported: '-{token}'")
            count, sides, keep_info = parse_single_group(token)
            groups.append((count, sides, keep_info))
        else:
            raise ValueError(f"Invalid token in notation: '{token}'")

    if not groups:
        raise ValueError("Notation must include at least one dice group (e.g. d20, 2d6)")

    return groups, modifier


def roll_dice(notation: str, label: Optional[str] = None) -> RollResponse:
    groups, modifier = parse_notation(notation)

    all_dice_results: list[SingleDieResult] = []
    group_breakdown_parts = []

    for count, sides, keep_info in groups:
        rolls = [random.randint(1, sides) for _ in range(count)]

        kept_indices = set(range(count))
        if keep_info:
            keep_type, keep_n = keep_info
            sorted_indices = sorted(range(count), key=lambda i: rolls[i])
            kept_indices = set(sorted_indices[-keep_n:] if keep_type == 'kh' else sorted_indices[:keep_n])

        group_results = [
            SingleDieResult(die=sides, value=v, kept=(i in kept_indices))
            for i, v in enumerate(rolls)
        ]
        all_dice_results.extend(group_results)

        kept_vals = [r.value for r in group_results if r.kept]
        kept_str = "+".join(str(v) for v in kept_vals)
        group_part = f"({kept_str})"
        if keep_info:
            dropped = [r.value for r in group_results if not r.kept]
            group_part += f"[dropped:{','.join(str(v) for v in dropped)}]"
        group_breakdown_parts.append(group_part)

    subtotal = sum(r.value for r in all_dice_results if r.kept)
    total = subtotal + modifier

    breakdown_lhs = "+".join(group_breakdown_parts)
    if modifier > 0:
        breakdown = f"{breakdown_lhs} + {modifier} = {total}"
    elif modifier < 0:
        breakdown = f"{breakdown_lhs} - {abs(modifier)} = {total}"
    else:
        breakdown = f"{breakdown_lhs} = {total}"

    return RollResponse(
        notation=notation,
        label=label,
        dice_results=all_dice_results,
        modifier=modifier,
        subtotal=subtotal,
        total=total,
        breakdown=breakdown,
        success=True
    )


@app.get("/", tags=["Info"])
def root():
    return {
        "service": "DnD Dice Roller API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "roll": "POST /roll",
            "quick_roll": "GET /roll/{notation}",
            "supported_dice": "GET /dice"
        }
    }


@app.get("/dice", tags=["Info"])
def get_supported_dice():
    """Returns all supported dice types"""
    return {
        "supported_dice": [f"d{d}" for d in VALID_DICE],
        "notation_examples": [
            {"notation": "d20", "description": "Single d20"},
            {"notation": "2d6", "description": "Two d6"},
            {"notation": "4d6kh3", "description": "Roll 4d6, keep highest 3"},
            {"notation": "2d20kh1", "description": "Advantage (roll 2d20, keep highest)"},
            {"notation": "2d20kl1", "description": "Disadvantage (roll 2d20, keep lowest)"},
            {"notation": "1d8+5", "description": "d8 plus 5 modifier"},
            {"notation": "2d6-1", "description": "Two d6 minus 1"},
        ]
    }


@app.post("/roll", response_model=RollResponse, tags=["Dice"])
def roll_dice_post(request: RollRequest):
    """
    Roll dice using standard dice notation.
    
    Supports: d20, 2d6, 4d6kh3 (keep highest), 2d20kl1 (keep lowest), 2d6+3 (modifiers)
    """
    try:
        return roll_dice(request.notation, request.label)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/roll/{notation}", response_model=RollResponse, tags=["Dice"])
def roll_dice_get(notation: str, label: Optional[str] = None):
    """
    Quick dice roll via URL path.
    
    Example: /roll/2d6+3, /roll/d20, /roll/4d6kh3
    """
    try:
        return roll_dice(notation, label)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/roll/multi", tags=["Dice"])
def roll_multiple(requests: list[RollRequest]):
    """Roll multiple dice at once (e.g., for full ability score generation)"""
    if len(requests) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 dice groups per request")
    results = []
    for req in requests:
        try:
            results.append(roll_dice(req.notation, req.label))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Error in '{req.notation}': {str(e)}")
    return {"rolls": results, "count": len(results)}
