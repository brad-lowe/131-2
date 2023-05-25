# pylint: disable=too-few-public-methods

"""
Module with classes for class, field, and method definitions.

In P1, we don't allow overloading within a class;
two methods cannot have the same name with different parameters.
"""

from intbase import InterpreterBase, ErrorType
from type_valuev2 import Type


class MethodDef:
    """
    Wrapper struct for the definition of a member method.
    """

    def __init__(self, method_def):
        method_type = method_def[1]
        if method_type == InterpreterBase.INT_DEF:
            self.type = Type.INT
        elif method_type == InterpreterBase.STRING_DEF:
            self.type = Type.STRING
        elif method_type == InterpreterBase.BOOL_DEF:
            self.type = Type.BOOL
        elif method_type == InterpreterBase.VOID_DEF:
            self.type = Type.NOTHING
        else:
            self.type = Type.CLASS
        self.method_name = method_def[2]
        self.formal_params = method_def[3]
        self.code = method_def[4]

        #print(self)

    def __str__(self):
        return "METHOD\n" + "\n".join([str(self.type), self.method_name, str(self.formal_params), str(self.code)])


class FieldDef:
    """
    Wrapper struct for the definition of a member field.
    """

    def __init__(self, field_def):
        field_type = field_def[1]
        if field_type == InterpreterBase.INT_DEF:
            self.type = Type.INT
        elif field_type == InterpreterBase.STRING_DEF:
            self.type = Type.STRING
        elif field_type == InterpreterBase.BOOL_DEF:
            self.type = Type.BOOL
        elif field_type == InterpreterBase.VOID_DEF:
            self.type = Type.NOTHING
        else:
            self.type = Type.CLASS
        self.field_name = field_def[2]
        self.default_field_value = field_def[3]

        #print(self)

    def __str__(self):
        return "FIELD\n" + "\n".join([str(self.type), self.field_name, self.default_field_value])


class ClassDef:
    """
    Holds definition for a class:
        - list of fields (and default values)
        - list of methods

    class definition: [class classname [field1 field2 ... method1 method2 ...]]
    """

    def __init__(self, class_def, interpreter):
        self.interpreter = interpreter
        self.name = class_def[1]
        self.parent_class = None
        self.children = []
        if class_def[2] == InterpreterBase.INHERITS_DEF:
            self.parent_class = self.interpreter.class_index[class_def[3]]
            self.__create_field_list(class_def[4:])
            self.__create_method_list(class_def[4:])
            self.parent_class.children.append(self)
        else:
            self.__create_field_list(class_def[2:])
            self.__create_method_list(class_def[2:])

    def get_fields(self):
        """
        Get a list of FieldDefs for *all* fields in the class.
        """
        return self.fields

    def get_methods(self):
        """
        Get a list of MethodDefs for *all* fields in the class.
        """
        return self.methods
        
    def is_parent_class_of(self, other):
        if self is other:
            return True
        if self.children == []:
            return False
        for c in self.children:
            if c is other:
                return True
            return c.is_parent_class_of(other)

    def __create_field_list(self, class_body):
        self.fields = []
        fields_defined_so_far = set()
        for member in class_body:
            if member[0] == InterpreterBase.FIELD_DEF:
                if member[2] in fields_defined_so_far:  # redefinition
                    self.interpreter.error(
                        ErrorType.NAME_ERROR,
                        "duplicate field " + member[2],
                        member[0].line_num,
                    )
                self.fields.append(FieldDef(member))
                fields_defined_so_far.add(member[2])
        parent = self.parent_class
        while parent != None:
            self.fields = self.fields + parent.get_fields()
            parent = parent.parent_class

    def __create_method_list(self, class_body):
        self.methods = []
        methods_defined_so_far = set()
        for member in class_body:
            if member[0] == InterpreterBase.METHOD_DEF:
                if member[2] in methods_defined_so_far:  # redefinition
                    self.interpreter.error(
                        ErrorType.NAME_ERROR,
                        "duplicate method " + member[2],
                        member[0].line_num,
                    )
                self.methods.append(MethodDef(member))
                methods_defined_so_far.add(member[2])
