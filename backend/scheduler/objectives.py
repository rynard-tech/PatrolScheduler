"""Lexicographic objective helpers. Higher-priority stages are solved first."""
def fairness_cost(person, station:str) -> int:
    return int(person.history.get(station,0))

def preference_cost(person, pattern:tuple[int,...]) -> int:
    try: return person.preferences.index(pattern)
    except ValueError: return len(person.preferences)+1
