import ast
import operator
import re
from typing import Optional

class SafeCalculator:
    """Безопасный калькулятор без eval()"""
    
    ALLOWED_NODES = (
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub
    )
    
    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }
    
    @classmethod
    def calculate(cls, expression: str) -> Optional[str]:
        """Безопасное вычисление математического выражения"""
        expr = expression.replace(' ', '').replace('^', '**')
        
        if not re.match(r'^[0-9+\-*/().]+$', expr):
            return None
        
        try:
            node = ast.parse(expr, mode='eval')
            
            for n in ast.walk(node):
                if type(n) not in cls.ALLOWED_NODES:
                    return None
            
            result = cls._eval(node.body)
            
            if isinstance(result, float):
                if result.is_integer():
                    return str(int(result))
                return f"{result:.2f}".rstrip('0').rstrip('.')
            return str(result)
        except:
            return None
    
    @classmethod
    def _eval(cls, node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            left = cls._eval(node.left)
            right = cls._eval(node.right)
            return cls.OPERATORS[type(node.op)](left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = cls._eval(node.operand)
            return cls.OPERATORS[type(node.op)](operand)
        raise ValueError(f"Unsupported node: {type(node)}")
