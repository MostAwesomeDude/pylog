from pprint import pprint

from pylog import compile_program, compile_query, parser, WAM

q = parser("p(Z, h(Z, W), f(W))").functor()
p = parser("p(f(X), h(Y, f(a)), Y)").functor()

q = compile_query(q)
p = compile_program(p)

m = WAM()
pprint(list(enumerate(m.heap)))
pprint(m.x)
pprint(m.pdl)
m.run(q)
pprint(list(enumerate(m.heap)))
pprint(m.x)
pprint(m.pdl)
m.run(p)
pprint(list(enumerate(m.heap)))
pprint(m.x)
pprint(m.pdl)
