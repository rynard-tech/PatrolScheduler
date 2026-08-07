import argparse, json
from .fixtures import synthetic_problem
from .scheduler.deployment_solver import solve
from .scheduler.validation import validate

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--json-only",action="store_true"); args=parser.parse_args()
    problem=synthetic_problem(); result=solve(problem); payload=result.to_dict(); payload["validation"]=validate(problem,result)
    payload["summaries"]={"preference":"synthetic work patterns use each employee's first configured choice","fairness":"deployment objective minimizes season-to-date station exposure"}
    print(json.dumps(payload,indent=2))
    if not args.json_only:
        print("\nDATE       EMPLOYEE             STATION       SHIFT")
        for a in result.assignments: print(f"{a.date} {a.employee_name:<20} {a.station:<13} {a.shift_type}")
    raise SystemExit(0 if payload["validation"]["valid"] else 1)
if __name__=="__main__": main()
