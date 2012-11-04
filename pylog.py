from parsley import makeGrammar

g = open("prolog.parsley").read()

parser = makeGrammar(g, {})
