# import functools
# from typing import Type, Any
#
# from filedgr_pkg_utils.converters.abstract_converter import AbstractConverter
#
#
# def handle_convertion(converter: AbstractConverter,
#                       return_type: Type = Any):
#     def decorator_handle_convertion(func):
#         @functools.wraps(func)
#         def wrapper(cls, *args, **kwargs):
#             try:
#                 input_to_dto = converter.convert_dto_to_model(dto=kwargs['dto'])
#                 value = func(cls, , *args, **kwargs)
#                 return value
#             except Exception as exc:
#                 _log.exception(exc)
#                 if rollback:
#                     session.rollback()
#                 raise exc
#             finally:
#                 session.close()
#
#         return wrapper
#
#     return decorator_handle_convertion
