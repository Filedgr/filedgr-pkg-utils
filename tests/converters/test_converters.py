from typing import Type

from pydantic import BaseModel

from filedgr_pkg_utils.converters.abstract_converter import AbstractConverter, MODEL


class ExampleModel(BaseModel):
    name: str
    age: int

class ExampleDto(BaseModel):
    name_and_age: str


class ExampleConverter(AbstractConverter[ExampleModel, ExampleDto]):

    def convert_dto_to_model(self, dto: ExampleDto) -> ExampleModel:
        return ExampleModel(name="eric", age=31)

    def convert_model_to_dto(self, model: ExampleModel, return_type: Type[ExampleDto]) -> ExampleDto:
        return ExampleDto(name_and_age="eric40")

    def convert_request_to_model(self, request) -> ExampleModel:
        return ExampleModel(name="eric", age=31)

def test_converter():
    converter = ExampleConverter()

