from collections import deque, namedtuple

from parsley import makeGrammar


class Functor(namedtuple("Functor", "name, terms")):

    @property
    def arity(self):
        return len(self.terms)


Variable = namedtuple("Variable", "name")

ast_types = {
    "Functor": Functor,
    "Variable": Variable,
}

g = open("prolog.parsley").read()

parser = makeGrammar(g, ast_types)

READ = object()
REF = object()
STR = object()
WRITE = object()


def number_term(term):
    """
    Convert a term of functors and variables into a numbered term, returning
    the register roots.
    """

    q = deque([term])
    register = 0
    registers = {}

    # Breadth-first. Number all of the terms.
    while q:
        t = q.pop()
        if t not in registers:
            registers[t] = register
            register += 1
        if isinstance(t, Functor):
            for inner in t.terms:
                if inner not in registers:
                    q.appendleft(inner)
                    registers[inner] = register
                    register += 1

    s = [term]
    functors = []

    # And now depth-first. Everything is numbered, so just copy out the
    # numbers and save all of the roots.
    while s:
        t = s.pop()
        for inner in t.terms:
            if isinstance(inner, Functor):
                s.append(inner)
        r = registers[t]
        t = t._replace(terms=tuple(registers[x] for x in t.terms))
        functors.append((r, t))

    functors.sort()
    return functors


def compile_query(term):
    roots = number_term(term)
    instructions = []
    seen = set()

    for register, functor in reversed(roots):
        if register in seen:
            instructions.append(("set_value", register))
        else:
            seen.add(register)
            instructions.append(("put_structure",
                (functor.name, functor.arity), register))

            for register in functor.terms:
                if register in seen:
                    instructions.append(("set_value", register))
                else:
                    seen.add(register)
                    instructions.append(("set_variable", register))

    return instructions


def compile_program(term):
    roots = number_term(term)
    instructions = []
    seen = set()

    for register, functor in roots:
        instructions.append(("get_structure", (functor.name, functor.arity),
            register))

        for register in functor.terms:
            if register in seen:
                instructions.append(("unify_value", register))
            else:
                seen.add(register)
                instructions.append(("unify_variable", register))

    return instructions


class WAM(object):
    """
    Warren's Abstract Machine.
    """

    fail = False

    def __init__(self):
        self.heap = []
        self.pdl = []

    def deref(self, address):
        """
        Dereference an address on the heap.
        """

        tag, value = self.heap[address]
        if tag is REF and value != address:
            return self.deref(value)
        return address

    def bind(self, address1, address2):
        self.heap[address1] = REF, address2

    def unify(self, address1, address2):
        """
        Unify two addresses on the PDL.
        """

        self.pdl.append(address1)
        self.pdl.append(address2)

        self.fail = False

        while self.pdl and not self.fail:
            d1 = self.deref(self.pdl.pop())
            d2 = self.deref(self.pdl.pop())

            if d1 != d2:
                t1, v1 = self.heap[d1]
                t2, v2 = self.heap[d2]
                if t1 is REF or t2 is REF:
                    self.bind(d1, d2)
                else:
                    f1, n1 = self.heap[v1]
                    f2, n2 = self.heap[v2]
                    if f1 == f2 and n1 == n2:
                        for i in range(n1):
                            self.pdl.append(v1 + i + 1)
                            self.pdl.append(v2 + i + 1)
                    else:
                        self.fail = True
                        break

    # VM instructions.

    def put_structure(self, fn, i):
        h = len(self.heap)
        ptr = STR, h + 1
        self.heap.append(ptr)
        self.heap.append(fn)
        self.x[i] = ptr

    def set_variable(self, i):
        ptr = REF, len(self.heap)
        self.heap.append(ptr)
        self.x[i] = ptr

    def set_value(self, i):
        self.heap.append(self.x[i])

    def get_structure(self, fn, i):
        addr = self.deref(self.x[i])
        tag, value = self.heap[addr]

        if tag is REF:
            self.heap.append((STR, len(self.heap) + 1))
            self.heap.append(fn)
            self.bind(addr, len(self.heap) - 2)
            self.mode = WRITE
        elif tag is STR:
            if self.heap[value] == fn:
                self.s = value + 1
                self.mode = READ
            else:
                self.fail = True
        else:
            self.fail = True

    def unify_variable(self, i):
        if self.mode is READ:
            self.x[i] = self.heap[self.s]
        elif self.mode is WRITE:
            ptr = REF, len(self.heap)
            self.heap.append(ptr)
            self.x[i] = ptr
        self.s += 1

    def unify_value(self, i):
        if self.mode is READ:
            self.unify(self.x[i], self.s)
        elif self.mode is WRITE:
            self.heap.append(self.x[i])
        self.s += 1

    # Compiling functions.

    def load(self, instructions):
        rv = []
        for inst in instructions:
            method = getattr(self, inst)
            rv.append((method,) + inst[1:])
        return rv
