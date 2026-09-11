# Day 03 — AST Parser & Code Extraction

## Objective

The third day focused on understanding Python source code structurally using
Python's Abstract Syntax Tree (AST).

---

## 1. AST Parser

`ASTParser` was implemented to read Python source files and convert them into
an AST.

The parser:

1. Reads the source file.
2. Uses UTF-8 encoding.
3. Converts the source into an AST.
4. Reports readable errors when parsing fails.

---

## 2. Encoding Error Handling

The parser handles UTF-8 decoding failures separately.

Instead of exposing a raw Python exception, the analyzer reports a clear
message identifying the affected file.

---

## 3. Syntax Error Handling

Invalid Python source code is handled using `SyntaxError`.

The resulting error includes:

- File path
- Line number
- Syntax error message

This allows project analysis to identify problematic files without producing
an unclear traceback.

---

## 4. Code Extraction

`CodeExtractor` was used to inspect the AST and extract structural
information.

The extractor identifies:

- Functions
- Async functions
- Classes
- Imports
- Function calls
- Conditions
- Loops
- Return statements

---

## 5. Function Information

Functions are represented with information such as:

- Function name
- Source line
- Parameter names

Both normal and asynchronous functions are supported.

---

## 6. Import Detection

The AST visitor detects:

- `import module`
- `from module import something`

Import information is stored as module names.

---

## 7. AST Visitor Pattern

Python's `ast.NodeVisitor` was used instead of manually processing source
code text.

This provides a structured representation of the source code and creates a
strong foundation for future static-analysis features.

---

## Result

Code Guardian AI gained a reliable structural understanding of Python source
files.

The analyzer could now move beyond simple file scanning and reason about
actual Python code structures.