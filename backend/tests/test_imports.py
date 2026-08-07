import pytest
from backend.imports.mapping import ColumnMapping, SpreadsheetImporter

def test_fuzzy_identity_requires_confirmation_and_preserves_raw():
    importer=SpreadsheetImporter(ColumnMapping(source_to_target={"Notes":"notes"},identity_name="Name"),[{"id":1,"display_name":"Alex Rivera","employee_number":"10"}])
    source=[{"Name":"Alex River","Notes":"maybe Tuesday"}]
    preview=importer.preview(source); assert preview.requires_confirmation
    with pytest.raises(ValueError): importer.commit(preview)
    importer.confirm_fuzzy_match(2,1); preview=importer.preview(source)
    assert importer.commit(preview)[0]["raw_source"]["Notes"]=="maybe Tuesday"
