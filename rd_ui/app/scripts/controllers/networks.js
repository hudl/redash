(function() {

  var NetworkCtrl = function($scope, $routeParams, $http, $location, $growl, Events, Table) {
    Events.record(currentUser, "view", "page", "table-networks");
    $scope.$parent.pageTitle = "Table Network";

    Table.get({'id': $routeParams.tableId}, function(data) {
        $scope.table = data;
    });
  };

  angular.module('redash.controllers')
    .controller('NetworkCtrl',  ['$scope', '$routeParams', '$http', '$location', 'growl', 'Events', 'Table', NetworkCtrl])
})();
