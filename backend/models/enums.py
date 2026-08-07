from enum import StrEnum


class EmploymentType(StrEnum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    MANAGER = "MANAGER"


class Weekday(StrEnum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"


class PaidStatusType(StrEnum):
    PTO = "PTO"
    TRAINING = "TRAINING"
    LEAVE = "LEAVE"
    OTHER = "OTHER"


class RuleStrength(StrEnum):
    HARD = "HARD"
    SOFT = "SOFT"


class ShiftCode(StrEnum):
    STANDARD = "STANDARD"
    FIRST_TRACKS = "FIRST_TRACKS"
    NIGHT_SKI = "NIGHT_SKI"
    WEATHER = "WEATHER"
    FORECASTER = "FORECASTER"
    CUSTOM = "CUSTOM"
