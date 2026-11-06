import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

import pytest


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def metadata_rule(monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[2] / "datahubirodsruleset"
    decorator = load_module("metadata_upload_decorator", root / "decorator.py")
    instance = {
        "1_Identifier": {"datasetIdentifier": {}, "datasetIdentifierType": {}},
        "8_Date": {"datasetDate": {}, "datasetDateType": {}},
    }
    read = Mock(side_effect=[json.dumps(instance), json.dumps({"@id": "old-schema"})])
    upload = Mock()
    modules = {
        "datahubirodsruleset": ModuleType("datahubirodsruleset"),
        "datahubirodsruleset.decorator": decorator,
        "datahubirodsruleset.formatters": SimpleNamespace(
            format_instance_collection_path=lambda ctx, project, collection: "instance.json",
            format_schema_collection_path=lambda ctx, project, collection: "schema.json",
        ),
        "datahubirodsruleset.utils": SimpleNamespace(read_data_object_from_irods=read, iput_wrapper=upload),
    }
    with patch.dict(sys.modules, modules):
        rule = load_module("metadata_upload_rule", root / "customizable_metadata/update_metadata_during_ingest.py")

    files = []
    create_file = tempfile.NamedTemporaryFile

    def tracked_file(*args, **kwargs):
        file = create_file(*args, dir=tmp_path, **kwargs)
        files.append(file)
        return file

    monkeypatch.setattr(tempfile, "NamedTemporaryFile", tracked_file)
    return rule, upload, files


def invoke(rule):
    rule.update_metadata_during_ingest(["P000000001", "C000000001", "prefix/P000000001C000000001", "1"], Mock(), None)


def test_metadata_is_readable_by_upload_process_before_tempfile_closes(metadata_rule):
    rule, upload, files = metadata_rule
    documents = {}

    def read_upload(ctx, source, destination, project, overwrite):
        # Opening by pathname models iput reading outside the buffered writer.
        documents[destination] = json.loads(Path(source).read_text())

    upload.side_effect = read_upload
    invoke(rule)
    handle = "https://hdl.handle.net/prefix/P000000001C000000001"
    assert documents["instance.json"]["@id"] == handle + "instance.1"
    assert documents["instance.json"]["schema:isBasedOn"] == handle + "schema.1"
    assert documents["schema.json"]["@id"] == handle + "schema.1"
    assert len(files) == 2
    assert all(file.closed and not Path(file.name).exists() for file in files)


@pytest.mark.parametrize("failed_upload", [1, 2])
def test_temporary_metadata_is_closed_when_upload_fails(metadata_rule, failed_upload):
    rule, upload, files = metadata_rule
    upload.side_effect = [None] * (failed_upload - 1) + [RuntimeError("upload failed")]
    with pytest.raises(RuntimeError, match="upload failed"):
        invoke(rule)
    assert len(files) == failed_upload
    assert all(file.closed and not Path(file.name).exists() for file in files)
