CmpE 260 - Spring 2026, Project 
Melang Interpreter

Authors
-------
Mert Seyhan       - 2023400213
Metehan Sarıkaya    - 2023400111

The name Melang comes from our first names (Mert + Metehan) plus "lang".

How to run
----------
Python 3.8 or higher is required. No external libraries needed.

Basic usage:
    python interpreter.py program.txt

With explicit scoping mode (default is static):
    python interpreter.py --scope static program.txt
    python interpreter.py --scope dynamic program.txt

Examples:
    python interpreter.py examples/basics.txt
    python interpreter.py examples/recursion.txt
    python interpreter.py examples/closures.txt
    python interpreter.py --scope static  examples/scope.txt
    python interpreter.py --scope dynamic examples/scope.txt
    python interpreter.py examples/higher_order.txt

Output
------
- print statements write to stdout, one value per line.
- Runtime errors (undefined variable, division by zero, type mismatch)
  are printed to stderr and the interpreter exits with a non-zero code.

File structure
--------------
interpreter.py       main interpreter (lexer + parser + evaluator)
grammar.txt          BNF grammar definition (D1)
ast.txt              AST node documentation (D2)
report.pdf           design report (D5)
README.txt           this file
examples/
    basics.txt       variable declarations, arithmetic, comparisons
    recursion.txt    factorial, fibonacci, gcd
    closures.txt     closures and captured state
    scope.txt        static vs dynamic scoping demo
    higher_order.txt higher-order functions and composition

Implemented features
--------------------
Core: F1-F10 (integers, booleans, arithmetic, comparisons, logical
operators, variables, conditionals, first-class functions, recursion,
closures, static scoping, print)

Bonus:
  B1 - strings: double-quoted literals, + concatenation, length()
  B2 - while loops: while cond do body end
  B3 - lists: [1,2,3] literals, lst[i] indexing, length(), append()
  B4 - both scoping modes via --scope static|dynamic flag
  B5 - runtime type checking with clear error messages
  B6 - higher-order patterns (fold, compose) in examples/higher_order.txt
