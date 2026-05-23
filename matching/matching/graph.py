import requests
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List
from difflib import SequenceMatcher
import re
from collections import defaultdict


# ValueMatcher для объединения похожих значений
class ValueMatcher:
    def __init__(self, similarity_threshold=0.85):
        self.threshold = similarity_threshold

    def normalize(self, text: str) -> str:
        if not text:
            return ""
        text = str(text).lower()
        text = re.sub(r'[^\w\s]', '', text)
        text = ' '.join(text.split())
        return text

    def are_similar(self, val1: str, val2: str) -> bool:
        if not val1 or not val2:
            return False

        n1 = self.normalize(val1)
        n2 = self.normalize(val2)

        if n1 == n2:
            return True

        if n1 in n2 or n2 in n1:
            return True

        ratio = SequenceMatcher(None, n1, n2).ratio()
        return ratio >= self.threshold

    def merge_values(self, values_dict: Dict[str, List[str]]) -> Dict[str, Dict]:
        merged = {}

        for prop, values in values_dict.items():
            merged[prop] = {}
            used = set()

            for i, val in enumerate(values):
                if val in used:
                    continue

                similar = [val]
                for other in values[i+1:]:
                    if other in used:
                        continue
                    if self.are_similar(val, other):
                        similar.append(other)
                        used.add(other)

                used.add(val)
                merged_value = min(similar, key=len) if len(similar) > 1 else val
                merged[prop][merged_value] = similar

        return merged


class WikidataClient:
    SPARQL_URL = "https://query.wikidata.org/sparql"

    def get_entity(self, entity_name: str) -> Dict[str, Any]:
        try:
            search_query = f"""
            SELECT ?item ?itemLabel WHERE {{
              ?item rdfs:label ?itemLabel.
              FILTER(CONTAINS(LCASE(?itemLabel), LCASE("{entity_name}")))
            }}
            LIMIT 1
            """

            headers = {"Accept": "application/sparql-results+json", "User-Agent": "KnowledgeGraphMerger/1.0"}
            response = requests.get(self.SPARQL_URL, params={"query": search_query}, headers=headers, timeout=10)

            if response.status_code != 200:
                return {'error': 'SPARQL query failed'}

            data = response.json()
            if not data["results"]["bindings"]:
                return {'error': 'Not found'}

            qid = data["results"]["bindings"][0]["item"]["value"].split("/")[-1]
            entity_label = data["results"]["bindings"][0].get("itemLabel", {}).get("value", entity_name)

            props_query = f"""
            SELECT ?propertyLabel ?valueLabel WHERE {{
              wd:{qid} ?p ?value.
              ?property wikibase:directClaim ?p.
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
            }}
            """

            response = requests.get(self.SPARQL_URL, params={"query": props_query}, headers=headers, timeout=20)
            data = response.json()

            result = {
                'id': qid,
                'name': entity_label,
                'properties': {}
            }

            for binding in data["results"]["bindings"]:
                prop = binding.get("propertyLabel", {}).get("value", "")
                val = binding.get("valueLabel", {}).get("value", "")

                # if prop and val:
                #     if prop_norm not in result['properties']:
                #         result['properties'][prop_norm] = []
                #     if val not in result['properties'][prop_norm]:
                #         result['properties'][prop_norm].append(val)

            return result

        except Exception as e:
            return {'error': str(e)}


class DBpediaClient:
    SPARQL_ENDPOINT = "https://dbpedia.org/sparql"

    def get_entity(self, entity_name: str) -> Dict[str, Any]:
        try:
            formatted_name = entity_name.title().replace(' ', '_')

            query = f"""
            SELECT ?property ?value WHERE {{
              <http://dbpedia.org/resource/{formatted_name}> ?property ?value.
              FILTER(STRSTARTS(STR(?property), "http://dbpedia.org/ontology/"))
            }}
            """

            headers = {"Accept": "application/sparql-results+json", "User-Agent": "KnowledgeGraphMerger/1.0"}
            response = requests.get(self.SPARQL_ENDPOINT, params={"query": query}, headers=headers, timeout=10)

            if response.status_code != 200:
                return {'error': f'HTTP {response.status_code}'}

            data = response.json()
            result = {'name': formatted_name.replace('_', ' '), 'properties': {}}

            for binding in data["results"]["bindings"]:
                prop = binding["property"]["value"].split("/")[-1]
                val = binding["value"]["value"]
 
                if val.startswith("http://dbpedia.org/resource/"):
                    val = val.split("/")[-1].replace("_", " ")
                elif val.startswith("http"):
                    continue

                prop_norm = normalize_property_name(prop)
                if prop_norm not in result['properties']:
                    result['properties'][prop_norm] = []
                if val not in result['properties'][prop_norm]:
                    result['properties'][prop_norm].append(val)

            return result

        except Exception as e:
            return {'error': str(e)}


class UnifiedGraphBuilder:
    def __init__(self):
        self.skip_properties = {
            'bbc_things_id', 'canadiana_authorities_id', 'nlp_id',
            'british_museum_person_or_institution_id', 'gtaa_id',
            'great_aragonese_encyclopedia_id', 'national_portrait_gallery_person_id',
            'genealogics.org_person_id', 'ccab_id', 'id', 'source'
        }

        self.important_properties = {
            'birth_date': 'Дата рождения',
            'death_date': 'Дата смерти', 
            'birth_place': 'Место рождения',
            'death_place': 'Место смерти',
            'occupation': 'Профессия',
            'citizenship': 'Гражданство',
            'educated_at': 'Место учёбы',
            'employer': 'Место работы',
            'award': 'Награды',
            'spouse': 'Супруг(а)',
            'father': 'Отец',
            'mother': 'Мать',
            'child': 'Дети',
            'field': 'Область науки',
            'doctoral_advisor': 'Научный руководитель',
            'doctoral_students': 'Ученики'
        }

    def extract_meaningful_edges(self, sources_data: Dict[str, Dict]) -> List[Dict]:
        edges = []

        for source, data in sources_data.items():
            if not data or 'error' in data:
                continue

            properties = data.get('properties', {})

            for prop, values in properties.items():
                if prop in self.skip_properties:
                    continue

                if not isinstance(values, list):
                    values = [values]

                for val in values:
                    if val and not str(val).startswith('http'):
                        if self._is_valid_value(val):
                            edges.append({
                                'source': data.get('name', 'Unknown'),
                                'target': val,
                                'property': prop,
                                'property_label': self.important_properties.get(prop, prop.replace('_', ' ').title()),
                                'source_db': source,
                                'weight': 1
                            })

        return self._deduplicate_edges(edges)

    def _is_valid_value(self, value: str) -> bool:
        if re.match(r'^[A-Z0-9]+$', value) and len(value) < 15:
            return False
        if re.match(r'^Q[0-9]+$', value):
            return False
        if len(value) < 2:
            return False
        return True

    def _deduplicate_edges(self, edges: List[Dict]) -> List[Dict]:
        unique = {}

        for edge in edges:
            key = (edge['source'], edge['target'], edge['property'])

            if key not in unique:
                unique[key] = edge
                unique[key]['sources'] = [edge['source_db']]
                unique[key]['merged_from'] = 1
            else:
                if edge['source_db'] not in unique[key]['sources']:
                    unique[key]['sources'].append(edge['source_db'])
                    unique[key]['merged_from'] += 1
                unique[key]['weight'] = len(unique[key]['sources'])

        return list(unique.values())

    def build_knowledge_graph(self, entity_name: str, sources_data: Dict[str, Dict]) -> Dict[str, Any]:
        central_entity = sources_data.get('wikidata', {}).get('name') or \
                         sources_data.get('dbpedia', {}).get('name') or \
                         entity_name.title()

        edges = self.extract_meaningful_edges(sources_data)

        nodes: set = {central_entity}
        for edge in edges:
            nodes.add(edge['source'])
            nodes.add(edge['target'])

        edges_by_type = defaultdict(list)
        for edge in edges:
            edges_by_type[edge['property']].append(edge)

        graph = {
            'entity': central_entity,
            'statistics': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'sources_used': list(set(e['source_db'] for e in edges)),
                'property_types': len(edges_by_type)
            },
            'nodes': [{'id': n, 'label': n} for n in nodes],
            'edges': edges,
            'edges_by_type': dict(edges_by_type),
        }

        return graph


class KnowledgeGraphMerger:
    def __init__(self):
        self.wikidata = WikidataClient()
        self.dbpedia = DBpediaClient()
        self.graph_builder = UnifiedGraphBuilder()

    def get_entity(self, entity_name: str) -> Dict[str, Any]:
        result = {}

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                'wikidata': executor.submit(self.wikidata.get_entity, entity_name),
                'dbpedia': executor.submit(self.dbpedia.get_entity, entity_name)
            }

            for source, future in futures.items():
                try:
                    result[source] = future.result(timeout=15)
                except Exception as e:
                    result[source] = {'error': str(e)}

        return result

    def build_unified_graph(self, entity_name: str) -> Dict[str, Any]:
        sources_data = self.get_entity(entity_name)
        return self.graph_builder.build_knowledge_graph(entity_name, sources_data)
