import base64
import hashlib

from gcsfs import GCSFileSystem

from arti import CompositeKey, Fingerprint
from arti.partitions import Int32Key
from arti.storage.google.cloud.storage import GCSFile
from arti.types import Collection, Int32, Struct
from tests.arti.dummies import DummyFormat


def test_GCSFile() -> None:
    f = GCSFile(bucket="test", path="folder/file")
    assert f.qualified_path == "test/folder/file"


def test_GCSFile_discover_partitions(gcs: GCSFileSystem, gcs_bucket: str) -> None:
    storage = GCSFile(
        bucket=gcs_bucket,
        path="{i.key}",
        format=DummyFormat(),
        type=Collection(element=Struct(fields={"i": Int32()}), partition_by=("i",)),
    )
    expected_keys = {CompositeKey(i=Int32Key(key=i)) for i in [0, 1]}
    gcs.pipe({storage.qualified_path.format(**keys): b"data" for keys in expected_keys})
    for partition in storage.discover_partitions():
        assert partition.keys in expected_keys
        assert partition.qualified_path == storage.qualified_path.format(**partition.keys)
        assert partition.content_fingerprint == Fingerprint.from_string(
            base64.b64encode(hashlib.md5(b"data").digest()).decode()
        )
