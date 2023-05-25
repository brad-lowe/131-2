"""
Module that contains the Value definition and associated type constructs.
"""

from enum import Enum
from intbase import InterpreterBase, ErrorType


class Type(Enum):
    """Enum for all possible Brewin types."""

    INT = 1
    BOOL = 2
    STRING = 3
    CLASS = 4
    NOTHING = 5
    MISMATCHED_TYPE = 6


# Represents a value, which has a type and its value
class Value:
    """A representation for a value that contains a type tag."""

    def __init__(self, value_type, value=None):
        self.__type = value_type
        self.__value = value

    def type(self):
        return self.__type

    def value(self):
        return self.__value

    def set(self, other):
        self.__type = other.type()
        self.__value = other.value()


# pylint: disable=too-many-return-statements
def create_value(val, actual_type=None):
    """
    Create a Value object from a Python value.
    """
    #print("creating ", val, actual_type)
    if val == InterpreterBase.TRUE_DEF:
        if actual_type == Type.BOOL or actual_type == None:
            return Value(Type.BOOL, True)
        InterpreterBase.error(
            ErrorType.TYPE_ERROR,
            "mismatched type " + str(actual_type),
        )
    if val == InterpreterBase.FALSE_DEF:
        if actual_type == Type.BOOL or actual_type == None:
            return Value(Type.BOOL, False)
        InterpreterBase.error(
            ErrorType.TYPE_ERROR,
            "mismatched type " + str(actual_type),
        )
    if val[0] == '"':
        if actual_type == Type.STRING or actual_type == None:
            return Value(Type.STRING, val.strip('"'))
        InterpreterBase.error(
            ErrorType.TYPE_ERROR,
            "mismatched type " + str(actual_type),
        )
    if val.lstrip('-').isnumeric():
        if actual_type == Type.INT or actual_type == None:
            return Value(Type.INT, int(val))
        InterpreterBase.error(
            ErrorType.TYPE_ERROR,
            "mismatched type " + str(actual_type),
        )
    if val == InterpreterBase.NULL_DEF:
        if actual_type == Type.CLASS or actual_type == None:
            return Value(Type.CLASS, None)
        InterpreterBase.error(
            ErrorType.TYPE_ERROR,
            "mismatched type " + str(actual_type),
        )
    if val == InterpreterBase.NOTHING_DEF:
        if actual_type == Type.NOTHING or actual_type == None:
            return Value(Type.NOTHING, None)
        InterpreterBase.error(
            ErrorType.TYPE_ERROR,
            "mismatched type " + str(actual_type),
        )
    #print("returning none")
    return None
