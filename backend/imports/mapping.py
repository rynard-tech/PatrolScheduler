"""Spreadsheet mapping/preview boundary; importing never silently merges identities."""
from __future__ import annotations
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from io import BytesIO
from typing import Any, Iterable
from openpyxl import load_workbook
from pydantic import BaseModel, Field

class ColumnMapping(BaseModel):
    source_to_target: dict[str, str]
    identity_employee_number: str | None = None
    identity_name: str | None = None

class PreviewRecord(BaseModel):
    row_number: int
    raw: dict[str, Any]
    normalized: dict[str, Any]
    identity_status: str
    employee_id: int | None = None
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

class ImportPreview(BaseModel):
    records: list[PreviewRecord]
    matched: int
    unresolved: int
    ambiguous: int
    requires_confirmation: bool

def _name(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())

@dataclass
class SpreadsheetImporter:
    mapping: ColumnMapping
    employees: list[dict[str, Any]]
    fuzzy_threshold: float = .82
    _confirmed: dict[int, int] = field(default_factory=dict)

    def preview(self, source: bytes | Iterable[dict[str, Any]]) -> ImportPreview:
        rows = self._rows(source); records=[]
        by_number={str(e.get("employee_number")):e for e in self.employees if e.get("employee_number")}
        by_name={_name(e.get("display_name")):[] for e in self.employees}
        for e in self.employees: by_name.setdefault(_name(e.get("display_name")), []).append(e)
        for number, raw in enumerate(rows, 2):
            normalized={target:raw.get(source_col) for source_col,target in self.mapping.source_to_target.items()}
            exact=[]
            if self.mapping.identity_employee_number and raw.get(self.mapping.identity_employee_number) is not None:
                found=by_number.get(str(raw[self.mapping.identity_employee_number])); exact=[found] if found else []
            source_name=_name(raw.get(self.mapping.identity_name)) if self.mapping.identity_name else ""
            if not exact and source_name: exact=by_name.get(source_name, [])
            if len(exact)==1: status, employee, candidates="MATCHED",exact[0],[]
            else:
                candidates=[{"employee_id":e["id"],"display_name":e["display_name"],"score":round(SequenceMatcher(None,source_name,_name(e["display_name"])).ratio(),3)} for e in self.employees if source_name and SequenceMatcher(None,source_name,_name(e["display_name"])).ratio()>=self.fuzzy_threshold]
                candidates.sort(key=lambda x:x["score"], reverse=True); employee=None
                status="AMBIGUOUS" if len(exact)>1 or len(candidates)>1 else "UNRESOLVED"
            if number in self._confirmed: status="CONFIRMED"; employee={"id":self._confirmed[number]}
            records.append(PreviewRecord(row_number=number,raw=raw,normalized=normalized,identity_status=status,employee_id=employee["id"] if employee else None,candidates=candidates))
        return ImportPreview(records=records,matched=sum(r.identity_status in {"MATCHED","CONFIRMED"} for r in records),unresolved=sum(r.identity_status=="UNRESOLVED" for r in records),ambiguous=sum(r.identity_status=="AMBIGUOUS" for r in records),requires_confirmation=any(r.identity_status in {"UNRESOLVED","AMBIGUOUS"} for r in records))

    def confirm_fuzzy_match(self, row_number:int, employee_id:int) -> None:
        if employee_id not in {e["id"] for e in self.employees}: raise ValueError("unknown employee")
        self._confirmed[row_number]=employee_id

    def commit(self, preview:ImportPreview) -> list[dict[str,Any]]:
        if preview.requires_confirmation: raise ValueError("all unresolved or ambiguous identities require explicit confirmation")
        return [{**r.normalized,"employee_id":r.employee_id,"raw_source":r.raw} for r in preview.records]

    def _rows(self, source):
        if not isinstance(source,(bytes,bytearray)): return list(source)
        sheet=load_workbook(BytesIO(source),data_only=True,read_only=True).active
        values=sheet.iter_rows(values_only=True); headers=[str(v) for v in next(values)]
        return [dict(zip(headers,row)) for row in values]
