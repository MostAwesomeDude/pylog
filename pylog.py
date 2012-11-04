from parsley import makeGrammar

g = open("prolog.parsley").read()

parser = makeGrammar(g, {})

READ = object()
REF = object()
STR = object()
WRITE = object()


def arity(term):
    return len(term[1])


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
