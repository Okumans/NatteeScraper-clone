from dotenv import load_dotenv
from typing import Final
from natteescraper import NatteScraper, LoginPostData, DEFAULT_LINKED_DIR
from pydantic import HttpUrl, TypeAdapter
from argparse import ArgumentParser
from pathlib import Path
from colorama import Fore, Style, init
import os

from utils import link_erunner, process_input, write_etest, write_file, strikethrough

if __name__ == "__main__":
    init(autoreset=True)
    load_dotenv()

    # Initialize environment variables
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

    # Validate essential environment variables
    assert USERNAME is not None, "GRADER_USERNAME environment variable is not set."
    assert PASSWORD is not None, "GRADER_PASSWORD environment variable is not set."

    POST_DATA: Final = LoginPostData(
        utf8="✓",
        authenticity_token=None,
        login=USERNAME,
        password=PASSWORD,
        commit="login",
    )

    # Set up argument parsing
    parser = ArgumentParser(
        description="Script for scraping and generating test cases from NatteGrader."
    )
    parser.add_argument(
        "--generate-input-file",
        type=Path,
        help="Generate an input file for the selected problem in the specified directory.",
    )
    parser.add_argument(
        "--file-type",
        type=str,
        default=".cpp",
        help="Specify the file extension for the generated input file.",
    )
    parser.add_argument(
        "--link-erunner",
        action="store_true",
        default=False,
        help="Link the generated file with an easy-runner compatible erunner cache.",
    )

    args = parser.parse_args()

    if (
        isinstance(args.generate_input_file, Path)
        and not args.generate_input_file.exists()
    ):
        raise FileNotFoundError(
            "The specified directory for generating an input file does not exist."
        )

    if not os.path.isdir(LINKED_DIR):
        os.mkdir(LINKED_DIR)

    scraper = NatteScraper(POST_DATA, ROOT_URL, LOGIN_URL, TESTCASE_URL)

    # Retrieve and display test case names
    testnames = list(reversed(scraper.get_testnames()))
    for index, testname in enumerate(testnames, 1):
        if testname.removeprefix("[").lower().startswith("dig"):
            print(Fore.RED + Style.DIM + strikethrough(f"{index}) {testname}"))
        else:
            print(Fore.BLUE + f"{index}) " + Fore.GREEN + testname)

    # Process input to retrieve the appropriate test case index
    raw_input = input(
        Fore.YELLOW + "Enter the test case index or type the test case name: "
    )
    index = process_input(raw_input, testnames)

    # Generate test file in easy-runner single file format
    filename = testnames[index].split(" ")[0].strip("[]")
    write_etest(
        Path(LINKED_DIR).joinpath(f"{filename}.etest"), testnames[index], scraper
    )

    # Generate and link an input file if specified
    if isinstance(args.generate_input_file, Path):
        new_filename: str = filename + args.file_type
        write_file(args.generate_input_file.joinpath(new_filename))

        if args.link_erunner:
            target_erunner_cache_path = args.generate_input_file.joinpath(
                "erunner_cache.json"
            )
            link_erunner(target_erunner_cache_path, Path(LINKED_DIR), new_filename)
