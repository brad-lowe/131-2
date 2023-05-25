"""
Module handling the operations of an object. This contains the meat
of the code to execute various instructions.
"""

from env_v2 import EnvironmentManager
from intbase import InterpreterBase, ErrorType
from type_valuev2 import create_value
from type_valuev2 import Type, Value
from copy import deepcopy


class ObjectDef:
    STATUS_PROCEED = 0
    STATUS_RETURN = 1
    STATUS_NAME_ERROR = 2
    STATUS_TYPE_ERROR = 3
    STATUS_RETURN_DEFAULT = 4

    def __init__(self, interpreter, class_def, trace_output):
        self.interpreter = interpreter  # objref to interpreter object. used to report errors, get input, produce output
        self.class_def = class_def  # take class body from 3rd+ list elements, e.g., ["class",classname", [classbody]]
        self.trace_output = trace_output
        self.__map_fields_to_values()
        self.__map_method_names_to_method_definitions()
        self.__create_map_of_operations_to_lambdas()  # sets up maps to facilitate binary and unary operations, e.g., (+ 5 6)

    def get_most_derived_method(self, method_name, calling_super, line_num_of_caller):
        class_def = self.class_def
        if calling_super:
            class_def = class_def.parent_class
        while class_def.parent_class is not None and \
                method_name not in [x.method_name for x in class_def.get_methods()]:
            class_def = class_def.parent_class

        if method_name not in [x.method_name for x in class_def.get_methods()]:
            self.interpreter.error(
                ErrorType.NAME_ERROR,
                "unknown method " + method_name,
                line_num_of_caller,
            )
        method = None
        for x in class_def.get_methods():
            if x.method_name == method_name:
                method = x
        return class_def, method

    def get_fields_by_class(self, class_def):
        c = self.class_def
        while c is not class_def and c.parent_class is not None:
            c = c.parent_class
        field_names = [x.field_name for x in c.get_fields()]
        #print(self.fields, field_names)
        return {x:self.fields[x] for x in field_names}

    def name_is_parent_class_of(self, parent_name, child_name):
        parent = self.interpreter.class_index[parent_name]
        child = self.interpreter.class_index[child_name]
        return parent.is_parent_class_of(child)

    def call_method(self, method_name, calling_super, actual_params, line_num_of_caller):
        """
        actual_params is a list of Value objects (all parameters are passed by value).

        The caller passes in the line number so we can properly generate an error message.
        The error is then generated at the source (i.e., where the call is initiated).
        """
        class_def, method_info = self.get_most_derived_method(method_name, calling_super, line_num_of_caller)
        fields = self.get_fields_by_class(class_def)
        #print(fields)
        #print(method_info)
        if len(actual_params) != len(method_info.formal_params):
            self.interpreter.error(
                ErrorType.NAME_ERROR,
                "invalid number of parameters in call to " + method_name,
                line_num_of_caller,
            )

        env = (
            EnvironmentManager()
        )  # maintains lexical environment for function; just params for now

        #print(method_info)
        for formal, actual in zip([x[1] for x in method_info.formal_params], actual_params):
            if formal == InterpreterBase.STRING_DEF:
                if actual.type() != Type.STRING:
                    self.interpreter.error(
                        ErrorType.NAME_ERROR, "invalid parameter type", line_num_of_caller
                    )
            if formal == InterpreterBase.INT_DEF:
                if actual.type() != Type.INT:
                    self.interpreter.error(
                        ErrorType.NAME_ERROR, "invalid parameter type", line_num_of_caller
                    )
            if formal == InterpreterBase.BOOL_DEF:
                if actual.type() != Type.BOOL:
                    self.interpreter.error(
                        ErrorType.NAME_ERROR, "invalid parameter type", line_num_of_caller
                    )
            if formal == InterpreterBase.CLASS_DEF:
                if actual.type() != Type.CLASS:
                    self.interpreter.error(
                        ErrorType.NAME_ERROR, "invalid parameter type", line_num_of_caller
                    )
            env.set(formal, actual)
        
        #print(env.environment)
        # since each method has a single top-level statement, execute it.
        status, return_value = self.__execute_statement(env, fields, method_info.code)
        # if the method explicitly used the (return expression) statement to return a value, then return that
        # value back to the caller

        #print(status, return_value)
        if status == ObjectDef.STATUS_RETURN:
            #print(return_value.type(), method_info.type)
            if return_value.type() == method_info.type:
                return return_value
            self.interpreter.error(
                ErrorType.TYPE_ERROR, "invalid return type", line_num_of_caller
            )
        # The method didn't explicitly return a value, so return a default value

        #print(method_info)

        if method_info.type == Type.INT:
            return create_value('0')
        if method_info.type == Type.BOOL:
            return create_value(InterpreterBase.FALSE_DEF)
        if method_info.type == Type.STRING:
            return create_value('""')
        if method_info.type == Type.CLASS:
            return create_value(InterpreterBase.NULL_DEF)

        return Value(InterpreterBase.NOTHING_DEF)

    def __execute_statement(self, env, fields, code):
        """
        returns (status_code, return_value) where:
        - status_code indicates if the next statement includes a return
            - if so, the current method should terminate
            - otherwise, the next statement in the method should run normally
        - return_value is a Value containing the returned value from the function
        """
        #print(env)
        if self.trace_output:
            print(f"{code[0].line_num}: {code}")
        tok = code[0]
        if tok == InterpreterBase.BEGIN_DEF:
            return self.__execute_begin(env, fields, code)
        if tok == InterpreterBase.SET_DEF:
            return self.__execute_set(env, fields, code)
        if tok == InterpreterBase.IF_DEF:
            return self.__execute_if(env, fields, code)
        if tok == InterpreterBase.CALL_DEF:
            return self.__execute_call(env, fields, code)
        if tok == InterpreterBase.WHILE_DEF:
            return self.__execute_while(env, fields, code)
        if tok == InterpreterBase.RETURN_DEF:
            return self.__execute_return(env, fields, code)
        if tok == InterpreterBase.INPUT_STRING_DEF:
            return self.__execute_input(env, fields, code, True)
        if tok == InterpreterBase.INPUT_INT_DEF:
            return self.__execute_input(env, fields, code, False)
        if tok == InterpreterBase.PRINT_DEF:
            return self.__execute_print(env, fields, code)
        if tok == InterpreterBase.LET_DEF:
            return self.__execute_let(env, fields, code)

        self.interpreter.error(
            ErrorType.SYNTAX_ERROR, "unknown statement " + tok, tok.line_num
        )

    # (begin (statement1) (statement2) ... (statementn))
    def __execute_begin(self, env, fields, code):
        for statement in code[1:]:
            status, return_value = self.__execute_statement(env, fields, statement)
            if status == ObjectDef.STATUS_RETURN or status == ObjectDef.STATUS_RETURN_DEFAULT:
                return (
                    status,
                    return_value,
                )  # could be a valid return of a value or an error
        # if we run thru the entire block without a return, then just return proceed
        # we don't want the calling block to exit with a return
        return ObjectDef.STATUS_PROCEED, None

    # (call object_ref/me methodname param1 param2 param3)
    # where params are expressions, and expresion could be a value, or a (+ ...)
    # statement version of a method call; there's also an expression version of a method call below
    def __execute_call(self, env, fields, code):
        return ObjectDef.STATUS_PROCEED, self.__execute_call_aux(
            env, fields, code, code[0].line_num
        )

    # (set varname expression), where expresion could be a value, or a (+ ...)
    def __execute_set(self, env, fields, code):
        #print(code)
        #print(env)
        val = self.__evaluate_expression(env, fields, code[2], code[0].line_num)
        #print(val.value())
        self.__set_variable_aux(env, fields, code[1], val, code[0].line_num)
        return ObjectDef.STATUS_PROCEED, None

    # (return expression) where expresion could be a value, or a (+ ...)
    def __execute_return(self, env, fields, code):
        if len(code) == 1:
            # [return] with no return expression
            return ObjectDef.STATUS_RETURN_DEFAULT, create_value(InterpreterBase.NOTHING_DEF)
        return ObjectDef.STATUS_RETURN, self.__evaluate_expression(
            env, fields, code[1], code[0].line_num
        )

    # (print expression1 expression2 ...) where expresion could be a variable, value, or a (+ ...)
    def __execute_print(self, env, fields, code):
        output = ""
        #print(env.environment)
        for expr in code[1:]:
            # TESTING NOTE: Will not test printing of object references
            term = self.__evaluate_expression(env, fields, expr, code[0].line_num)
            val = term.value()
            typ = term.type()
            if typ == Type.BOOL:
                val = "true" if val else "false"
            # document - will never print out an object ref
            output += str(val)
        self.interpreter.output(output)
        return ObjectDef.STATUS_PROCEED, None

    # (inputs target_variable) or (inputi target_variable) sets target_variable to input string/int
    def __execute_input(self, env, fields, code, get_string):
        inp = self.interpreter.get_input()
        if get_string:
            val = Value(Type.STRING, inp)
        else:
            val = Value(Type.INT, int(inp))

        self.__set_variable_aux(env, fields, code[1], val, code[0].line_num)
        return ObjectDef.STATUS_PROCEED, None

    # helper method used to set either parameter variables or member fields; parameters currently shadow
    # member fields
    def __set_variable_aux(self, env, fields, var_name, value, line_num, is_let=False):
        # parameter shadows fields
        #print(var_name)
        #print(value)
        if value.type() == Type.NOTHING:
            self.interpreter.error(
                ErrorType.TYPE_ERROR, "can't assign to nothing " + var_name, line_num
            )
        
        # let shadows everything else
        if is_let:
            env.set(var_name, value)
            return

        param_val = env.get(var_name)
        #print(param_val.value())
        #print(value)
        if param_val is not None:
            if param_val.type() != value.type():
                self.interpreter.error(
                    ErrorType.TYPE_ERROR, "mismatched types " + str(param_val.type()) + " " + str(value.type()), line_num
                )
            env.set(var_name, value)
            return

        if var_name not in fields:
            self.interpreter.error(
                ErrorType.NAME_ERROR, "unknown variable " + var_name, line_num
            )
        if fields[var_name].type() != value.type():
            #print(value, value.type(), value.value())
            #print(self.fields[var_name], self.fields[var_name].type())
            self.interpreter.error(
                ErrorType.TYPE_ERROR, "mismatched types " + str(fields[var_name].type()) + " " + str(value.type()), line_num
            )
        #print(fields[var_name].value())
        #if fields[var_name].type() == Type.CLASS:
        #    if not fields[var_name].value.value().is_parent_class_of(value.value()):
        #        self.interpreter.error(
        #            ErrorType.TYPE_ERROR, "incompatible classes", line_num
        #        )
        fields[var_name] = value
        self.fields[var_name] = value

    # (if expression (statement) (statement) ) where expresion could be a boolean constant (e.g., true), member
    # variable without ()s, or a boolean expression in parens, like (> 5 a)
    def __execute_if(self, env, fields, code):
        condition = self.__evaluate_expression(env, fields, code[1], code[0].line_num)
        if condition.type() != Type.BOOL:
            self.interpreter.error(
                ErrorType.TYPE_ERROR,
                "non-boolean if condition " + ' '.join(x for x in code[1]),
                code[0].line_num,
            )
        if condition.value():
            status, return_value = self.__execute_statement(
                env, fields, code[2]
            )  # if condition was true
            return status, return_value
        if len(code) == 4:
            status, return_value = self.__execute_statement(
                env, fields, code[3]
            )  # if condition was false, do else
            return status, return_value
        return ObjectDef.STATUS_PROCEED, None

    # (while expression (statement) ) where expresion could be a boolean value, boolean member variable,
    # or a boolean expression in parens, like (> 5 a)
    def __execute_while(self, env, fields, code):
        while True:
            condition = self.__evaluate_expression(env, fields, code[1], code[0].line_num)
            if condition.type() != Type.BOOL:
                self.interpreter.error(
                    ErrorType.TYPE_ERROR,
                    "non-boolean while condition " + ' '.join(x for x in code[1]),
                    code[0].line_num,
                )
            if not condition.value():  # condition is false, exit loop immediately
                return ObjectDef.STATUS_PROCEED, None
            # condition is true, run body of while loop
            status, return_value = self.__execute_statement(env, fields, code[2])
            if status == ObjectDef.STATUS_RETURN or status == ObjectDef.STATUS_RETURN_DEFAULT:
                return (
                    status,
                    return_value,
                )  # could be a valid return of a value or an error

    # given an expression, return a Value object with the expression's evaluated result
    # expressions could be: constants (true, 5, "blah"), variables (e.g., x), arithmetic/string/logical expressions
    # like (+ 5 6), (+ "abc" "def"), (> a 5), method calls (e.g., (call me foo)), or instantiations (e.g., new dog_class)
    def __evaluate_expression(self, env, fields, expr, line_num_of_statement):
        #print("evaluating", expr)
        if not isinstance(expr, list):
            # locals shadow member variables
            val = env.get(expr)
            #print("val is", val)
            if val is not None and val.type() != Type.MISMATCHED_TYPE:
                return val
            if expr in fields:
                #print("field is", self.fields[expr].type(), self.fields[expr].value())
                return fields[expr]
            # need to check for variable name and get its value too
            #print("creating value", expr)
            value = create_value(expr)
            #print("checking value", value)
            if value is None:
                self.interpreter.error(
                    ErrorType.NAME_ERROR,
                    "invalid variable " + expr,
                    line_num_of_statement,
                )
            else:
                #print(value, value.type, "bad")
                if value.type() is not Type.MISMATCHED_TYPE:
                    return value
                self.interpreter.error(
                    ErrorType.TYPE_ERROR,
                    "invalid type for variable " + expr,
                    line_num_of_statement,
                )

        operator = expr[0]
        if operator in self.binary_op_list:
            operand1 = self.__evaluate_expression(env, fields, expr[1], line_num_of_statement)
            operand2 = self.__evaluate_expression(env, fields, expr[2], line_num_of_statement)
            if operand1.type() == operand2.type() and operand1.type() == Type.INT:
                if operator not in self.binary_ops[Type.INT]:
                    self.interpreter.error(
                        ErrorType.TYPE_ERROR,
                        "invalid operator applied to ints",
                        line_num_of_statement,
                    )
                return self.binary_ops[Type.INT][operator](operand1, operand2)
            if operand1.type() == operand2.type() and operand1.type() == Type.STRING:
                if operator not in self.binary_ops[Type.STRING]:
                    self.interpreter.error(
                        ErrorType.TYPE_ERROR,
                        "invalid operator applied to strings",
                        line_num_of_statement,
                    )
                return self.binary_ops[Type.STRING][operator](operand1, operand2)
            if operand1.type() == operand2.type() and operand1.type() == Type.BOOL:
                if operator not in self.binary_ops[Type.BOOL]:
                    self.interpreter.error(
                        ErrorType.TYPE_ERROR,
                        "invalid operator applied to bool",
                        line_num_of_statement,
                    )
                return self.binary_ops[Type.BOOL][operator](operand1, operand2)
            if operand1.type() == operand2.type() and operand1.type() == Type.CLASS:
                if operator not in self.binary_ops[Type.CLASS]:
                    self.interpreter.error(
                        ErrorType.TYPE_ERROR,
                        "invalid operator applied to class",
                        line_num_of_statement,
                    )
                return self.binary_ops[Type.CLASS][operator](operand1, operand2)
            if operand1.type() != operand2.type() and operand1.type() != Type.CLASS and operand2.type() != Type.CLASS:
                self.interpreter.error(
                    ErrorType.TYPE_ERROR,
                    "cannot perform operation on different primitive types",
                    line_num_of_statement,
                )
            # error what about an obj reference and null
            self.interpreter.error(
                ErrorType.TYPE_ERROR,
                f"operator {operator} applied to two incompatible types",
                line_num_of_statement,
            )
        if operator in self.unary_op_list:
            operand = self.__evaluate_expression(env, fields, expr[1], line_num_of_statement)
            if operand.type() == Type.BOOL:
                if operator not in self.unary_ops[Type.BOOL]:
                    self.interpreter.error(
                        ErrorType.TYPE_ERROR,
                        "invalid unary operator applied to bool",
                        line_num_of_statement,
                    )
                return self.unary_ops[Type.BOOL][operator](operand)

        # handle call expression: (call objref methodname p1 p2 p3)
        if operator == InterpreterBase.CALL_DEF:
            return self.__execute_call_aux(env, fields, expr, line_num_of_statement)
        # handle new expression: (new classname)
        if operator == InterpreterBase.NEW_DEF:
            return self.__execute_new_aux(env, expr, line_num_of_statement)

    # (new classname)
    def __execute_new_aux(self, _, code, line_num_of_statement):
        obj = self.interpreter.instantiate(code[1], line_num_of_statement)
        return Value(Type.CLASS, obj)

    # this method is a helper used by call statements and call expressions
    # (call object_ref/me methodname p1 p2 p3)
    def __execute_call_aux(self, env, fields, code, line_num_of_statement):
        # determine which object we want to call the method on
        calling_super = False
        obj_name = code[1]
        if obj_name == InterpreterBase.ME_DEF:
            obj = self
        elif obj_name == InterpreterBase.SUPER_DEF:
            obj = self
            calling_super = True
        else:
            obj = self.__evaluate_expression(
                env, fields, obj_name, line_num_of_statement
            ).value()
        # prepare the actual arguments for passing
        if obj is None:
            self.interpreter.error(
                ErrorType.FAULT_ERROR, "null dereference", line_num_of_statement
            )
        actual_args = []
       # print("args are", code)
        for expr in code[3:]:
            actual_args.append(
                self.__evaluate_expression(env, fields, expr, line_num_of_statement)
            )
        return obj.call_method(code[2], calling_super, actual_args, line_num_of_statement)

    def __execute_let(self, env, fields, code):

        env_let = deepcopy(env)

        var_set = set()
        var_list = []

        for var in code[1]:
            if var[0] == InterpreterBase.BOOL_DEF:
                actual_type = Type.BOOL
            elif var[0] == InterpreterBase.INT_DEF:
                actual_type = Type.INT
            elif var[0] == InterpreterBase.STRING_DEF:
                actual_type = Type.STRING
            elif var[0] == InterpreterBase.BOOL_DEF:
                actual_type = Type.BOOL
            else:
                actual_type = Type.CLASS

            val = create_value(var[2], actual_type)
            #print(val.value())

            var_set.add(var[1])
            var_list.append(var[1])
            if len(var_list) != len(var_set):
                self.interpreter.error(
                    ErrorType.NAME_ERROR, "cannot have 2 of the same variable in let statement", code[0].line_num
                )

            self.__set_variable_aux(env_let, fields, var[1], val, code[0].line_num, True)
        for statement in code[2:]:
            status, return_value = self.__execute_statement(env_let, fields, statement)
            if status == ObjectDef.STATUS_RETURN or status == ObjectDef.STATUS_RETURN_DEFAULT:
                return (
                    status,
                    return_value,
                )  # could be a valid return of a value or an error
        # if we run thru the entire block without a return, then just return proceed
        # we don't want the calling block to exit with a return
        return ObjectDef.STATUS_PROCEED, None

    def __map_method_names_to_method_definitions(self):
        self.methods = {}
        for method in self.class_def.get_methods():
            self.methods[method.method_name] = method

    def __map_fields_to_values(self):
        self.fields = {}
        for field in self.class_def.get_fields():
            self.fields[field.field_name] = create_value(field.default_field_value, field.type)

    def __create_map_of_operations_to_lambdas(self):
        self.binary_op_list = [
            "+",
            "-",
            "*",
            "/",
            "%",
            "==",
            "!=",
            "<",
            "<=",
            ">",
            ">=",
            "&",
            "|",
        ]
        self.unary_op_list = ["!"]
        self.binary_ops = {}
        self.binary_ops[Type.INT] = {
            "+": lambda a, b: Value(Type.INT, a.value() + b.value()),
            "-": lambda a, b: Value(Type.INT, a.value() - b.value()),
            "*": lambda a, b: Value(Type.INT, a.value() * b.value()),
            "/": lambda a, b: Value(
                Type.INT, a.value() // b.value()
            ),  # // for integer ops
            "%": lambda a, b: Value(Type.INT, a.value() % b.value()),
            "==": lambda a, b: Value(Type.BOOL, a.value() == b.value()),
            "!=": lambda a, b: Value(Type.BOOL, a.value() != b.value()),
            ">": lambda a, b: Value(Type.BOOL, a.value() > b.value()),
            "<": lambda a, b: Value(Type.BOOL, a.value() < b.value()),
            ">=": lambda a, b: Value(Type.BOOL, a.value() >= b.value()),
            "<=": lambda a, b: Value(Type.BOOL, a.value() <= b.value()),
        }
        self.binary_ops[Type.STRING] = {
            "+": lambda a, b: Value(Type.STRING, a.value() + b.value()),
            "==": lambda a, b: Value(Type.BOOL, a.value() == b.value()),
            "!=": lambda a, b: Value(Type.BOOL, a.value() != b.value()),
            ">": lambda a, b: Value(Type.BOOL, a.value() > b.value()),
            "<": lambda a, b: Value(Type.BOOL, a.value() < b.value()),
            ">=": lambda a, b: Value(Type.BOOL, a.value() >= b.value()),
            "<=": lambda a, b: Value(Type.BOOL, a.value() <= b.value()),
        }
        self.binary_ops[Type.BOOL] = {
            "&": lambda a, b: Value(Type.BOOL, a.value() and b.value()),
            "|": lambda a, b: Value(Type.BOOL, a.value() or b.value()),
            "==": lambda a, b: Value(Type.BOOL, a.value() == b.value()),
            "!=": lambda a, b: Value(Type.BOOL, a.value() != b.value()),
        }
        self.binary_ops[Type.CLASS] = {
            "==": lambda a, b: Value(Type.BOOL, a.value() == b.value()),
            "!=": lambda a, b: Value(Type.BOOL, a.value() != b.value()),
        }

        self.unary_ops = {}
        self.unary_ops[Type.BOOL] = {
            "!": lambda a: Value(Type.BOOL, not a.value()),
        }
