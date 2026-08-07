def status_explanation(status:str)->str:
    return {"OPTIMAL":"A valid schedule with the best configured fairness score was found.","FEASIBLE":"A valid schedule was found.","INFEASIBLE":"No hard-valid schedule exists."}.get(status,status)
