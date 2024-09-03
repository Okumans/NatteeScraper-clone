from dotenv import load_dotenv
from typing import Final, cast, Tuple
from natteescraper import NatteScraper, LoginPostData, DEFAULT_LINKED_DIR
from pydantic import HttpUrl, TypeAdapter
from argparse import ArgumentParser
from pathlib import Path
from fuzzywuzzy import process
from models import ErunnerCache, FileCache, ModelRefTest, Test
import os


def strikethrough(text: str) -> str:
    return "".join([char + "\u0336" for char in text])


if __name__ == "__main__":
    load_dotenv()

    # setup environment variables
    USERNAME: Final = os.getenv("GRADER_USERNAME")
    PASSWORD: Final = os.getenv("GRADER_PASSWORD")

    LINKED_DIR: Final = (
        buffer if (buffer := os.getenv("LINKED_DIR")) else DEFAULT_LINKED_DIR
    )
    ROOT_URL: Final = (
        TypeAdapter(HttpUrl).validate_python(buffer)
        if (buffer := os.getenv("ROOT_URL"))
        else None
    )
    LOGIN_URL: Final = (
        TypeAdapter(HttpUrl).validate_python(buffer)
        if (buffer := os.getenv("LOGIN_URL"))
        else None
    )
    TESTCASE_URL: Final = (
        TypeAdapter(HttpUrl).validate_python(buffer)
        if (buffer := os.getenv("TESTCASE_URL"))
        else None
    )

    assert USERNAME is not None
    assert PASSWORD is not None

    POST_DATA: Final = LoginPostData(
        utf8="✓",
        authenticity_token=None,
        login=USERNAME,
        password=PASSWORD,
        commit="login",
    )

    # get arguments
    parser = ArgumentParser(
        description="Script for scraping and generating a testcase from NatteGrader."
    )

    parser.add_argument(
        "--generate-input-file",
        type=Path,
        help="Generate a input file for choosed problem at inputed directory.",
    )

    parser.add_argument(
        "--file-type",
        type=str,
        default=".cpp",
        help="Specify file type for input file generated.",
    )

    parser.add_argument(
        "--link-erunner",
        action="store_true",
        default=False,
        help="Specify file type for input file generated.",
    )

    args = parser.parse_args()

    if (
        isinstance(args.generate_input_file, Path)
        and not args.generate_input_file.exists()
    ):
        raise FileNotFoundError("Unable to find directory for generating a input file.")

    if not os.path.isdir(LINKED_DIR):
        os.mkdir(LINKED_DIR)

    scraper = NatteScraper(POST_DATA, ROOT_URL, LOGIN_URL, TESTCASE_URL)

    testnames = list(reversed(scraper.get_testnames()))
    for index, testname in enumerate(testnames, 1):
        if testname.removeprefix("[").lower().startswith("dig"):
            print(strikethrough(f"{index}) {testname}"))
        else:
            print(f"{index}) {testname}")

    raw_input = input("Get testcases from test-index or just type the name: ")

    if raw_input.isdigit():
        index = int(raw_input) - 1
        assert 0 <= index < len(testnames)
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
        if best_result[1] > 80:
            print(f"Match: {testnames[index]}")
        else:
            print(f'Unable to find testcase named "{matched_value}"')
            quit()

    filename = (
        testnames[index].split(" ")[0].strip().removeprefix("[").removesuffix("]")
    )

    # write in easy-runner single file test format.
    # testcases from natteescraper can be use to write in other test file format.

    with open(os.path.join(LINKED_DIR, f"{filename}.etest"), "w+") as file:
        file.write("#disable:standalone\n")
        file.write("#enable:explicit-newline\n")
        file.write("#enable:trim\n\n")

        for testcase in scraper.get_testcases(testnames[index - 1]):
            is_newlined = False

            if testcase.input.count("\n") < 2:
                file.write("{" + testcase.input.replace("\n", "\\n") + "} -> ")
            else:
                is_newlined = True
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

    if isinstance(args.generate_input_file, Path):
        new_filename: str = filename + args.file_type

        if args.generate_input_file.joinpath(new_filename).exists():
            print(
                f"File named {new_filename} already exists. Do you wish to replace it. (Y/n): ",
                end="",
            )

            if input() != "Y":
                exit()

        # create a new file
        open(args.generate_input_file.joinpath(new_filename), "w")

        if args.link_erunner:
            target_erunner_cache_path = args.generate_input_file.joinpath(
                "erunner_cache.json"
            )

            if target_erunner_cache_path.exists():
                erunner_cache_json = ""

                with open(target_erunner_cache_path, "r") as file:
                    erunner_cache = ErunnerCache.model_validate_json(file.read())

                    erunner_cache.files[new_filename] = FileCache(
                        source_hash="NEED_RECOMPILATION",
                        tests=[
                            Test(
                                RefTest=ModelRefTest(
                                    input=Path(
                                        os.path.join(LINKED_DIR, f"{filename}.etest")
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
                print(
                    f"erunner_cache.json file not exists at {args.generate_input_file}."
                )
