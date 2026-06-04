import sys
import gc

import rdflib
from rdflib import Graph
from rdflib.compare import isomorphic

args = sys.argv

old = args[1]
new = args[2]

print('old ttl path is: ', old)
print('new ttl path is: ', new)

graph_old = Graph()
graph_old.parse(old, format='turtle')
graph_new = Graph()
graph_new.parse(new, format='turtle')
diff_graph = graph_old - graph_new
del graph_old
del graph_new
gc.collect()

if diff_graph is None :
    print(f'two ttls are completely same!\n')
    print(f'===============================\n')
else:
    print(f'two ttls are not same!\n')
    for s, p, o in diff_graph:
        print(s, p, o)
    print(f'\n===============================\n')

# if isomorphic(graph_old, graph_new):
#     print(f'two ttls are completely same!\n')
#     print(f'===============================\n')
# else:
#     print(f'two ttls are not same!\n')
#     diff_graph = graph_old - graph_new
#     for s, p, o in diff_graph:
#         print(s, p, o)
#     print(f'\n===============================\n')