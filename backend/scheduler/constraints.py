"""Reusable CP-SAT hard constraints, deliberately separate from orchestration."""
from ortools.sat.python import cp_model

def exactly_one_station(model, variables): model.Add(sum(variables)==1)
def minimum_staff(model, variables, minimum): model.Add(sum(variables)>=minimum)
def exact_staff(model, variables, count): model.Add(sum(variables)==count)
def weekly_station_diversity(model, variables, maximum): model.Add(sum(variables)<=maximum)
def fixed_value(model, variable, value=1): model.Add(variable==value)
