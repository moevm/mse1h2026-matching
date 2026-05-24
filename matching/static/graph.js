// Функция показа уведомлений
function showToast(message, duration = 2000) {
    let toast = document.querySelector('.cy-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.className = 'cy-toast';
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.style.display = 'block';
    setTimeout(() => {
        toast.style.display = 'none';
    }, duration);
}

function initNetwork() {
    const container = document.getElementById('network');
    
    if (!container) return;
    
    if (graphData.nodes.length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 50px; color: #999;">Нет данных для отображения</div>';
        return;
    }
    
    // Подготовка элементов для Cytoscape
    const elements = [];
    
    // Добавляем узлы
    graphData.nodes.forEach(node => {
        const isCentral = (node.id === centralNodeId);
        elements.push({
            data: {
                id: node.id,
                label: node.label.length > 25 ? node.label.substring(0, 22) + '...' : node.label,
                fullLabel: node.label
            },
            style: isCentral ? {
                'background-color': '#ff5722',
                'border-color': '#ff9800',
                'border-width': 3,
                'width': 50,
                'height': 50
            } : {}
        });
    });
    
    // Добавляем связи
    graphData.edges.forEach((edge, index) => {
        elements.push({
            data: {
                id: `edge_${index}`,
                source: edge.source,
                target: edge.target,
                label: (edge.property_label || edge.property || 'связано').substring(0, 20)
            }
        });
    });
    
    // Стили для графа
    const styles = [
        {
            selector: 'node',
            style: {
                'label': 'data(label)',
                'background-color': '#764ba2',
                'border-color': '#667eea',
                'border-width': 2,
                'width': 40,
                'height': 40,
                'font-size': '11px',
                'color': '#333',
                'text-valign': 'bottom',
                'text-halign': 'center',
                'text-margin-y': 8
            }
        },
        {
            selector: 'node:selected',
            style: {
                'background-color': '#ff5722',
                'border-color': '#ff9800',
                'border-width': 3,
                'width': 45,
                'height': 45
            }
        },
        {
            selector: 'edge',
            style: {
                'width': 2,
                'line-color': '#ccc',
                'target-arrow-color': '#999',
                'target-arrow-shape': 'triangle',
                'curve-style': 'bezier',
                'label': 'data(label)',
                'font-size': '9px',
                'text-rotation': 'autorotate',
                'color': '#666',
                'arrow-scale': 1
            }
        },
        {
            selector: 'edge:selected',
            style: {
                'line-color': '#ff5722',
                'target-arrow-color': '#ff5722',
                'width': 3
            }
        }
    ];
    
    // Инициализация Cytoscape
    cy = cytoscape({
        container: container,
        elements: elements,
        style: styles,
        layout: {
            name: 'cose',
            idealEdgeLength: 100,
            nodeRepulsion: 400000,
            gravity: 0.3,
            numIter: 500,
            fit: true,
            padding: 30,
            animate: false
        },
        wheelSensitivity: 0.5,
        minZoom: 0.1,
        maxZoom: 3
    });
    
    // Обработчик клика по узлу
    cy.on('tap', 'node', (evt) => {
        const node = evt.target;
        const fullLabel = node.data('fullLabel') || node.data('label');
        const connectedEdges = node.connectedEdges();
        const connectedNodes = node.neighborhood();
        
        showToast(`🔍 ${fullLabel}\n📊 Связан с ${connectedNodes.length - 1} узлами`, 3000);
        
        // Подсветка
        node.addClass('selected');
        connectedEdges.addClass('selected');
        
        setTimeout(() => {
            node.removeClass('selected');
            connectedEdges.removeClass('selected');
        }, 2000);
    });
    
    // Обработчик клика по связи
    cy.on('tap', 'edge', (evt) => {
        const edge = evt.target;
        edge.addClass('selected');
        showToast(`🔗 ${edge.data('label')}`, 1500);
        setTimeout(() => {
            edge.removeClass('selected');
        }, 2000);
    });
    
    // Центрируем граф
    setTimeout(() => {
        cy.fit();
        cy.center();
        showToast(`✅ Граф загружен: ${graphData.nodes.length} узлов, ${graphData.edges.length} связей`, 3000);
    }, 100);
}

// Применение раскладки
function applyLayout(layoutName) {
    if (!cy) return;
    
    currentLayout = layoutName;
    let layoutOptions = { name: layoutName, fit: true, padding: 30, animate: true };
    
    switch(layoutName) {
        case 'cose':
            layoutOptions = {
                name: 'cose',
                idealEdgeLength: 100,
                nodeRepulsion: 400000,
                gravity: 0.3,
                numIter: 500,
                fit: true,
                padding: 30,
                animate: true
            };
            break;
        case 'circle':
            layoutOptions = { name: 'circle', fit: true, padding: 30, animate: true };
            break;
        case 'concentric':
            layoutOptions = { 
                name: 'concentric', 
                fit: true, 
                padding: 30, 
                animate: true,
                concentric: function(node) {
                    return node.degree();
                }
            };
            break;
        case 'grid':
            layoutOptions = { name: 'grid', fit: true, padding: 30, animate: true };
            break;
        case 'breadthfirst':
            layoutOptions = { name: 'breadthfirst', fit: true, padding: 30, animate: true, directed: false };
            break;
    }
    
    cy.layout(layoutOptions).run();
    showToast(`🎨 Раскладка: ${layoutName}`, 1500);
}

// Подсветка связи при клике из списка
function highlightEdge(source, target) {
    if (!cy) return;
    
    switchTab('visualization');
    
    setTimeout(() => {
        const edge = cy.edges().filter(e => 
            e.data('source') === source && e.data('target') === target
        );
        if (edge.length > 0) {
            edge.select();
            
            // Подсветим также узлы
            const sourceNode = cy.nodes().filter(n => n.data('id') === source);
            const targetNode = cy.nodes().filter(n => n.data('id') === target);
            sourceNode.addClass('selected');
            targetNode.addClass('selected');
            
            // Центрируем на связи
            cy.fit(edge, { padding: 50 });
            
            setTimeout(() => {
                edge.unselect();
                sourceNode.removeClass('selected');
                targetNode.removeClass('selected');
            }, 3000);
            
            showToast(`🔗 ${source} → ${target}`, 2000);
        }
    }, 200);
}

// Переключение вкладок
function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    document.getElementById(tabId).classList.add('active');
    event.target.classList.add('active');
    
    if (tabId === 'neo4j') {
        generateCypherQueries();
    }
    
    if (tabId === 'visualization' && cy) {
        setTimeout(() => {
            cy.fit();
            cy.center();
        }, 100);
    }
}

// Генерация Cypher запросов
function generateCypherQueries() {
    const nodesSet = new Set();
    graphData.edges.forEach(edge => {
        nodesSet.add(edge.source);
        nodesSet.add(edge.target);
    });
    
    const cypherNodes = [];
    nodesSet.forEach(node => {
        const safeName = node.replace(/['"\\]/g, '\\$&');
        cypherNodes.push(`MERGE (n:Entity {name: '${safeName}'}) SET n.name = '${safeName}'`);
    });
    
    const cypherRels = [];
    graphData.edges.forEach(edge => {
        const safeSource = edge.source.replace(/['"\\]/g, '\\$&');
        const safeTarget = edge.target.replace(/['"\\]/g, '\\$&');
        const relType = (edge.property_label || edge.property || 'RELATED').toUpperCase().replace(/[^A-Z0-9_]/g, '_');
        const props = [];
        
        if (edge.property) props.push(`property: '${edge.property}'`);
        if (edge.property_label) props.push(`label: '${edge.property_label}'`);
        if (edge.sources) props.push(`sources: ['${edge.sources.join("', '")}']`);
        if (edge.merged_from) props.push(`merged_from: ${edge.merged_from}`);
        
        const propsStr = props.length > 0 ? ` {${props.join(', ')}}` : '';
        
        cypherRels.push(
            `MATCH (a:Entity {name: '${safeSource}'}), (b:Entity {name: '${safeTarget}'}) ` +
            `MERGE (a)-[r:${relType}]->(b) SET r += ${propsStr || '{}'}`
        );
    });
    
    const nodesPre = document.getElementById('cypher-nodes');
    const relsPre = document.getElementById('cypher-rels');
    if (nodesPre) nodesPre.textContent = cypherNodes.join(';\n');
    if (relsPre) relsPre.textContent = cypherRels.join(';\n');
}

function exportAsJSON() {
    const dataStr = JSON.stringify(graphData, null, 2);
    const blob = new Blob([dataStr], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `{{ entity_name }}_graph.json`;
    a.click();
    URL.revokeObjectURL(url);
    showAlert('✅ JSON файл сохранен');
}

function exportForNeo4j() {
    generateCypherQueries();
    const cypherNodes = document.getElementById('cypher-nodes')?.textContent || '';
    const cypherRels = document.getElementById('cypher-rels')?.textContent || '';
    const fullCypher = `// Nodes\n${cypherNodes};\n\n// Relationships\n${cypherRels};`;
    
    const blob = new Blob([fullCypher], {type: 'text/plain'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `{{ entity_name }}_neo4j.cypher`;
    a.click();
    URL.revokeObjectURL(url);
    showAlert('✅ Neo4j файл сохранен');
}

function copyCypher() {
    generateCypherQueries();
    const cypherNodes = document.getElementById('cypher-nodes')?.textContent || '';
    const cypherRels = document.getElementById('cypher-rels')?.textContent || '';
    const fullCypher = `// Neo4j Cypher queries for {{ entity_name }}\n\n// Create nodes\n${cypherNodes};\n\n// Create relationships\n${cypherRels};`;
    
    navigator.clipboard.writeText(fullCypher).then(() => {
        showAlert('✅ Cypher запросы скопированы');
    });
}

function copyAllCypher() {
    copyCypher();
}

function downloadNeo4jFile() {
    exportForNeo4j();
}

function showAlert(message) {
    const alert = document.getElementById('alert');
    alert.textContent = message;
    alert.classList.add('show');
    setTimeout(() => {
        alert.classList.remove('show');
    }, 3000);
}

// Инициализация
window.addEventListener('load', () => {
    initNetwork();
});