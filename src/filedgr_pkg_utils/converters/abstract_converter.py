import abc
from abc import ABC
from typing import TypeVar, Generic, Type

DTO = TypeVar('DTO')
MODEL = TypeVar('MODEL')


class AbstractConverter(ABC, Generic[MODEL, DTO]):

    @abc.abstractmethod
    def convert_request_to_model(self, request) -> MODEL:
        pass

    @abc.abstractmethod
    def convert_model_to_dto(self, model: MODEL, return_type: Type) -> DTO:
        pass

    @abc.abstractmethod
    def convert_dto_to_model(self, dto: DTO) -> MODEL:
        pass
