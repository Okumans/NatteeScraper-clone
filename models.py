from json import dumps
from pydantic import BaseModel
from typing import Dict, List, Optional
from pathlib import Path


class ModelRefTest(BaseModel):
    input: Path
    expected_output: Optional[Path] = None


class ModelStringTest(BaseModel):
    input: str
    expected_output: str


class Test(BaseModel):
    StringTest: Optional[ModelStringTest] = None
    RefTest: Optional[ModelRefTest] = None


class FileCache(BaseModel):
    source_hash: str
    tests: List[Test]


class ErunnerCache(BaseModel):
    binary_dir_path: Path
    files: Dict[str, FileCache]
    languages_config: Dict[str, str]
