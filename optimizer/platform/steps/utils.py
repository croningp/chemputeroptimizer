from networkx import MultiDiGraph

from ...constants import ANALYTICAL_INSTRUMENTS

def find_instrument(graph: MultiDiGraph, method: str) -> str:
    """Get the analytical instrument for the given method
    
    Args:
        method (str): Name of the desired analytical method
        
    Returns:
        str: ID of the analytical instrument on the supplied graph
    """
    for node, data in graph.nodes(data=True):
        if data['class'] == ANALYTICAL_INSTRUMENTS[method]:
            return node
            