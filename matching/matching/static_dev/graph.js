fetch("data.json")
.then(res => res.json())
.then(graph => {

    const cy = cytoscape({
        container: document.getElementById('cy'),

        elements: graph,

        style: [
            {
                selector: 'node',
                style: {
                    'label': 'data(label)',
                    'background-color': '#3498db',
                    'text-valign': 'top',
                    'text-halign': 'center',
                    'color': 'black',
                    'font-size': '12px'
                }
            },

            {
                selector: 'edge',
                style: {
                    'curve-style': 'bezier',
                    'target-arrow-shape': 'triangle',
                    'label': 'data(label)',
                    'line-color': '#999',
                    'target-arrow-color': '#999'
                }
            }
        ],

        layout: {
            name: 'cose'
        }
    });

    cy.on('tap', 'node', function(evt){
        const node = evt.target;

        document.getElementById("info").innerHTML =
            "<b>" + node.data("label") + "</b><br>" +
            "Source: " + node.data("source");
    });

});