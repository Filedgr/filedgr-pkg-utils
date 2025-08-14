from pydantic import BaseModel

from filedgr_pkg_utils.mixins.without_keys_mixin import WithoutKeysMixin


class ExampleObject(BaseModel, WithoutKeysMixin):
    firstname:str
    lastname: str

def test_without_keys_mixin():
    example = ExampleObject(
        firstname="John",
        lastname="Doe",
    )

    result = example.without_keys(dictionary=example.model_dump(mode="json"), exclude=["firstname"])
    assert "firstname" not in result
