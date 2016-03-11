(function () {
  'use strict';

  var directives = angular.module('redash.directives');

  directives.directive('networkGraph', function(){
    function link(scope, el) {

        var el = el[0],
            width = el.clientWidth,
            height = el.clientHeight,
            votefoci = [
                {x: width / 2, y: height / 10},
                {x: width / 10, y: 2 * height / 3 },
                {x: width, y: 2 * height / 3}
            ];

        var nodes = [];
        var links = [];
        var groups = [ scope.table.name ];

        scope.table.joins.forEach(function(join) {
          var groupId = groups.indexOf(join.related_table);

          if (groupId !== -1) {
            groups.push(join.related_table)
            groupId = nodes.length - 1;
          }

          var newNode = {
            party: groupId,
            label: join.related_table + '.' + join.related_column,
            cardinality: join.cardinality[-1]
          }

          var destNodeId = nodes.indexOf(newNode);

          if (destNodeId !== -1) {
            nodes.push(newNodes);
            destNodeId = nodes.length - 1;
          }

          newNode = {
            party: 0,
            label: $scope.table.name + '.' + join.column,
            cardinality: join.cardinality[0]
          }

          var sourceNodeId = nodes.indexOf(newNode);

          if (sourceNodeId !== -1) {
            nodes.push(newNodes);
            sourceNodeId = nodes.length - 1;
          }

          links.push({source: sourceNodeId, target: destNodeId});
        });

        var fill = [];
        for (var i = 0; i < groups.length; i++) {
            fill.push('#'+Math.random().toString(16).substr(2,6));
        }

        var force = d3.layout.force()
            .nodes(nodes)
            .links(lnks)
            .start();

        var svg = d3.select(el).append("svg")
            .attr("width", width)
            .attr("height", height);

        var node = svg.selectAll(".node")
            .data(nodes)
            .enter().append("circle")
            .attr("class", "node")
            .attr("cx", function(d) { return d.x; })
            .attr("cy", function(d) { return d.y; })
            .attr("r", function(d) { return d.size; })
            .style("fill", function(d, i) { return fill(d.party); })
            .style("stroke", function(d, i) { return d3.rgb(fill(d.party)).darker(2); })
            .call(force.drag);

        svg.style("opacity", 1e-6)
           .transition()
           .duration(1000)
           .style("opacity", 1);
    }
    return {
        link: link,
        restrict: 'E',
        scope: { data: '='},
        templateUrl: '/views/schemas/network.html'
    }
 });
})();
