from fuzzywuzzy import process
from pathlib import Path
import os

from models import ErunnerCache, FileCache, ModelRefTest, Test
from natteescraper import NatteScraper


def strikethrough(text: str) -> str:
    """Apply strikethrough effect to the given text."""
    return "".join([char + "\u0336" for char in text])


def process_input(raw_input: str, testnames: list[str], threshold: float = 0.8) -> int:
    """A function for getting input from user. (exit program when condition not corrected.)"""

    if raw_input.isdigit():
        index = int(raw_input) - 1
        assert 0 <= index < len(testnames)

        return index
    else:
        testname_parts = [testname.split(" ", 1) for testname in testnames]

        # Extract names and nicknames with their indices
        names_with_indices = [
            (name.split(" ")[0].strip("[]").lower(), i)
            for i, (name, _) in enumerate(testname_parts)
        ]

        nicknames_with_indices = [
            (
                (
                    desc.split(":", 1)[1].strip().lower()
                    if "." in desc
                    else desc.strip().lower()
                ),
                i,
            )
            for i, (_, desc) in enumerate(testname_parts)
        ]

        # Find best matches
        result_problem_name = process.extractOne(raw_input, names_with_indices)

        result_problem_nickname = process.extractOne(raw_input, nicknames_with_indices)

        # Set defaults
        result_problem_name = result_problem_name or ((" ", -1), 0)
        result_problem_nickname = result_problem_nickname or ((" ", -1), 0)

        # Get the best result
        best_result = max(result_problem_name, result_problem_nickname)

        # sasitfy pyright
        assert isinstance(best_result, tuple)
        assert len(best_result) == 2

        (matched_value, index), score = best_result
        if score > threshold * 100:
            print(f"Match: {testnames[index]}")
            return index

        print(f'Unable to find testcase named "{matched_value}"')
        quit()


def write_etest(file_path: Path, testname: str, scraper: NatteScraper):
    with open(file_path, "w+") as file:
        file.write("#disable:standalone\n")
        file.write("#enable:explicit-newline\n")
        file.write("#enable:trim\n\n")

        for testcase in scraper.get_testcases(testname):

            if testcase.input.count("\n") < 2:
                file.write("{" + testcase.input.replace("\n", "\\n") + "} -> ")
            else:
                file.write(
                    "{\n"
                    + "\\n\n".join(
                        [f"  {line}" for line in testcase.input.splitlines()]
                    )
                    + "\\n\n} -> "
                )

            if testcase.output.count("\n") < 2:
                file.write("{" + testcase.output.replace("\n", "\\n") + "}\n")
            else:
                file.write(
                    "{\n"
                    + "\\n\n".join(
                        [f"  {line}" for line in testcase.output.splitlines()]
                    )
                    + "\\n\n}\n"
                )


def write_file(file_path: Path) -> bool:
    """return true if file is written succesfully, false if not."""
    if file_path.exists():
        print(
            f"File named {os.path.basename(file_path)} already exists. Do you wish to replace it. (Y/n): ",
            end="",
        )

        if input() != "Y":
            return False

    # create a new file
    open(file_path, "w")
    return True


def link_erunner(
    target_erunner_cache_path: Path, target_directory: Path, filename: str
):
    if target_erunner_cache_path.exists():
        erunner_cache_json = ""

        with open(target_erunner_cache_path, "r") as file:
            erunner_cache = ErunnerCache.model_validate_json(file.read())

            erunner_cache.files[filename] = FileCache(
                source_hash="NEED_RECOMPILATION",
                tests=[
                    Test(
                        RefTest=ModelRefTest(
                            input=target_directory.joinpath(
                                f"{os.path.splitext(filename)[0]}.etest"
                            )
                        ),
                    )
                ],
            )

            erunner_cache_json = erunner_cache.model_dump_json(
                exclude_none=True, indent=2
            )

        with open(target_erunner_cache_path, "w") as file:
            file.write(erunner_cache_json)

    else:
        print(f"erunner_cache.json file not exists at {target_erunner_cache_path}.")
