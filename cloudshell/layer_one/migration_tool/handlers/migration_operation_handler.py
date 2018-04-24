from cloudshell.layer_one.migration_tool.entities.resource import Resource
from cloudshell.layer_one.migration_tool.helpers.connection_associator import ConnectionAssociator
from cloudshell.layer_one.migration_tool.helpers.connection_helper import ConnectionHelper
from cloudshell.layer_one.migration_tool.helpers.logical_route_helper import LogicalRouteHelper
from cloudshell.layer_one.migration_tool.helpers.resource_operation_helper import ResourceOperationHelper
from cloudshell.layer_one.migration_tool.validators.migration_operation_validator import MigrationOperationValidator


class MigrationOperationHandler(object):
    def __init__(self, api, logger):
        """
        :type api: cloudshell.api.cloudshell_api.CloudShellAPISession
        :type logger: cloudshell.layer_one.migration_tool.helpers.logger.Logger
        """
        self._api = api
        self._logger = logger
        self._resource_helper = ResourceOperationHelper(api, logger)
        self._connection_helper = ConnectionHelper(api, logger)
        self._operation_validator = MigrationOperationValidator(self._api, logger)
        self._logical_route_helper = LogicalRouteHelper(api, logger)
        self._connections = {}

    def prepare_operation(self, operation):
        """
        :type operation: cloudshell.layer_one.migration_tool.entities.migration_operation.MigrationOperation
        """
        self._operation_validator.validate(operation)

        self._resource_helper.define_resource_attributes(operation.old_resource)
        if operation.new_resource.exist:
            self._resource_helper.define_resource_attributes(operation.new_resource)
        else:
            operation.new_resource.address = operation.old_resource.address
            operation.new_resource.attributes = operation.old_resource.attributes

        # operation.connections = self._resource_helper.get_physical_connections(operation.old_resource)
        # operation.logical_routes = self._logical_route_helper.get_logical_routes(operation.connections)

    def define_connections(self, operation):
        """
        :type operation: cloudshell.layer_one.migration_tool.entities.migration_operation.MigrationOperation
        """
        self._connections[operation.old_resource.name] = self._resource_helper.get_physical_connections(
            operation.old_resource)

    def perform_operation(self, operation):
        """
        :type operation: cloudshell.layer_one.migration_tool.entities.migration_operation.MigrationOperation
        """
        new_resource = operation.new_resource
        old_resource = operation.old_resource

        # Create new resource or synchronize
        if not new_resource.exist:
            self._resource_helper.create_resource(new_resource)
            self._resource_helper.autoload_resource(new_resource)
        else:
            self._resource_helper.sync_from_device(new_resource)

        # Associate and update connections
        connection_associator = ConnectionAssociator(self._resource_helper.get_resource_ports(new_resource),
                                                     self._logger)

        self._logger.debug('Updating connections for resource {}'.format(new_resource))
        for connection in self._connections.get(old_resource.name).values():
            associated_connection = connection_associator.associated_connection(connection)
            self._connection_helper.update_connection(associated_connection)
            # update local connection DB
            connected_to_resource_connections = self._connections.get(connection.connected_to.split('/')[0])
            if connected_to_resource_connections:
                connected_to_connection = connected_to_resource_connections.get(connection.connected_to)
                connected_to_connection.connected_to = associated_connection.port.name
