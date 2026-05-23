from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from .graph import KnowledgeGraphMerger
import json

merger = KnowledgeGraphMerger()


def get_entity_data(request, entity_name):
    format_type = request.GET.get('format', 'html')
    view_type = request.GET.get('view', 'full')

    graph = merger.build_unified_graph(entity_name)

    if graph['statistics']['total_edges'] == 0 and graph['statistics']['total_nodes'] <= 1:
        if format_type == 'json':
            return JsonResponse({'error': f'Сущность "{entity_name}" не найдена'}, status=404)
        elif format_type == 'cypher':
            return HttpResponse('// No data found', content_type='text/plain')
        else:
            return render(request, 'entity_graph.html', {
                'entity_name': entity_name,
                'entity_display': entity_name.title(),
                'statistics': graph['statistics'],
                'nodes': [],
                'edges': [],
                'graph_json': json.dumps(graph, ensure_ascii=False, indent=2),
                'edges_by_type': {},
                'view_type': view_type
            })

    context = {
        'entity_name': entity_name,
        'entity_display': graph['entity'],
        'statistics': graph['statistics'],
        'nodes': graph['nodes'],
        'edges': graph['edges'],
        'graph_json': json.dumps(graph, ensure_ascii=False, indent=2),
        'edges_by_type': graph.get('edges_by_type', {}),
        'view_type': view_type
    }

    if format_type == 'json':
        return JsonResponse(graph, json_dumps_params={'ensure_ascii': False, 'indent': 2})
    elif format_type == 'graph':
        simple_graph = {
            'nodes': graph['nodes'],
            'links': [
                {
                    'source': edge['source'],
                    'target': edge['target'],
                    'label': edge.get('property_label', edge['property'])
                }
                for edge in graph['edges']
            ]
        }
        return JsonResponse(simple_graph, json_dumps_params={'ensure_ascii': False})
    elif format_type == 'cypher':
        cypher = generate_cypher_queries(graph)
        return HttpResponse(cypher, content_type='text/plain')
    else:
        return render(request, 'entity_graph.html', context)


def generate_cypher_queries(graph):
    nodes_set = set()
    for edge in graph['edges']:
        nodes_set.add(edge['source'])
        nodes_set.add(edge['target'])

    queries = ["// Neo4j Cypher queries for " + graph['entity']]
    queries.append("\n// Create nodes")

    for node in nodes_set:
        safe_name = node.replace("'", "\\'")
        queries.append(f"MERGE (n:Entity {{name: '{safe_name}'}}) SET n.name = '{safe_name}'")

    queries.append("\n// Create relationships")
    for edge in graph['edges']:
        safe_source = edge['source'].replace("'", "\\'")
        safe_target = edge['target'].replace("'", "\\'")
        rel_type = (edge.get('property_label', edge['property']).upper()
                    .replace(' ', '_').replace('-', '_'))
        rel_type = ''.join(c for c in rel_type if c.isalnum() or c == '_')

        props = []
        if edge.get('property'):
            props.append(f"property: '{edge['property']}'")
        if edge.get('property_label'):
            props.append(f"label: '{edge['property_label']}'")
        if edge.get('sources'):
            sources = "', '".join(edge['sources'])
            props.append(f"sources: ['{sources}']")

        props_str = f" {{{', '.join(props)}}}" if props else ""

        queries.append(
            f"MATCH (a:Entity {{name: '{safe_source}'}}), (b:Entity {{name: '{safe_target}'}}) "
            f"MERGE (a)-[r:{rel_type}]->(b) SET r += {props_str}"
        )

    return ';\n'.join(queries) + ';'


def export_neo4j(request, entity_name):
    graph = merger.build_unified_graph(entity_name)
    cypher = generate_cypher_queries(graph)

    response = HttpResponse(cypher, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="{entity_name}_neo4j.cypher"'
    return response
