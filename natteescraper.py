from typing import Literal, Final
from bs4.element import Tag
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl, TypeAdapter
from requests import Response
from requests import Session


DEFAULT_ROOT_URL: Final = "https://cedt-grader.nattee.net"
DEFAULT_LOGIN_URL: Final = "https://cedt-grader.nattee.net/login/login"
DEFAULT_TESTCASE_URL: Final = "https://cedt-grader.nattee.net/testcases/show_problem"
DEFAULT_LINKED_DIR: Final = "./LinkedTests"


class LoginPostData(BaseModel, extra="allow"):
    utf8: Literal["✓"]  # constant
    authenticity_token: str | None  # get from index page
    login: str  # change this to your username
    password: str  # change this to your password
    commit: Literal["login"]  # constant


class TestCase(BaseModel):
    input: str
    output: str


class NatteScraper:
    def __init__(
        self,
        post_data: LoginPostData,
        root_url: HttpUrl | None = None,
        login_url: HttpUrl | None = None,
        testcases_url: HttpUrl | None = None,
    ):
        self.root_url = (
            TypeAdapter(HttpUrl).validate_python(DEFAULT_ROOT_URL)
            if root_url is None
            else root_url
        )

        self.login_url = (
            TypeAdapter(HttpUrl).validate_python(DEFAULT_LOGIN_URL)
            if login_url is None
            else login_url
        )

        self.testcases_url = (
            TypeAdapter(HttpUrl).validate_python(DEFAULT_TESTCASE_URL)
            if testcases_url is None
            else testcases_url
        )

        self.post_data = post_data
        self.session: Session | None = None
        self.testcases = self.__get_avaliable_testcases(self.__setup_login())

    def get_testcases(self, raw_testcase: str) -> list[TestCase]:
        input_cases: list[str] = []
        output_cases: list[str] = []

        if self.session and raw_testcase in self.testcases:
            tests_page = self.session.get(
                f"{self.testcases_url}/{self.testcases[raw_testcase]}"
            )

            for index, raw_case in enumerate(
                BeautifulSoup(tests_page.text, "html.parser").findAll("textarea")
            ):
                assert isinstance(raw_case, Tag)

                if not (index % 2):
                    input_cases.append(raw_case.text)
                else:
                    output_cases.append(raw_case.text)

        return [
            TestCase(input=input, output=output)
            for (input, output) in zip(input_cases, output_cases)
        ]

    def get_testnames(self) -> list[str]:
        return list(self.testcases)

    def __setup_login(self) -> Response:
        self.session = Session()
        index_page = self.session.get(DEFAULT_ROOT_URL)

        ruby_authenticity_token = BeautifulSoup(index_page.text, "html.parser").find(
            "input", attrs={"name": "authenticity_token"}
        )

        if not isinstance(ruby_authenticity_token, Tag):
            raise Exception("Unable to find ruby_authenticity_token")

        if not isinstance((buffer := ruby_authenticity_token.get("value")), str):
            raise Exception('Unable to find field "value" in ruby_authenticity_token')

        self.post_data.authenticity_token = buffer

        return self.session.post(DEFAULT_LOGIN_URL, dict(self.post_data))

    def __get_avaliable_testcases(self, response: Response) -> dict[str, str]:
        selector = BeautifulSoup(response.text, "html.parser").find(
            "select", attrs={"id": "submission_problem_id"}
        )

        # map between testcase name and the testcase id
        testcases: dict[str, str] = {}

        if not isinstance(selector, Tag):
            raise Exception("Unable to find selector")

        # skip the first item (defualt)
        for child in selector.contents[1:]:
            if isinstance(child, Tag):
                if type(buffer := child.get("value")) is str:
                    testcases[child.text] = buffer

        return testcases

    def __del__(self):
        if self.session:
            self.session.close()
