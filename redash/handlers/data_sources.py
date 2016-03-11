from flask import make_response, request
from flask_restful import abort
from funcy import project

from redash import models
from redash.wsgi import api
from redash.utils.configuration import ConfigurationContainer, ValidationError
from redash.permissions import require_admin
from redash.query_runner import query_runners, get_configuration_schema_for_type
from redash.handlers.base import BaseResource, get_object_or_404


class DataSourceTypeListAPI(BaseResource):
    @require_admin
    def get(self):
        return [q.to_dict() for q in query_runners.values()]

api.add_org_resource(DataSourceTypeListAPI, '/api/data_sources/types', endpoint='data_source_types')


class DataSourceAPI(BaseResource):
    @require_admin
    def get(self, data_source_id):
        data_source = models.DataSource.get_by_id_and_org(data_source_id, self.current_org)
        return data_source.to_dict(all=True)

    @require_admin
    def post(self, data_source_id):
        data_source = models.DataSource.get_by_id_and_org(data_source_id, self.current_org)
        req = request.get_json(True)

        schema = get_configuration_schema_for_type(req['type'])
        if schema is None:
            abort(400)

        try:
            data_source.options.set_schema(schema)
            data_source.options.update(req['options'])
        except ValidationError:
            abort(400)

        data_source.type = req['type']
        data_source.name = req['name']
        data_source.save()

        return data_source.to_dict(all=True)

    @require_admin
    def delete(self, data_source_id):
        data_source = models.DataSource.get_by_id_and_org(data_source_id, self.current_org)
        data_source.delete_instance(recursive=True)

        return make_response('', 204)


class DataSourceListAPI(BaseResource):
    def get(self):
        if self.current_user.has_permission('admin'):
            data_sources = models.DataSource.all(self.current_org)
        else:
            data_sources = models.DataSource.all(self.current_org, groups=self.current_user.groups)

        response = {}
        for ds in data_sources:
            if ds.id in response:
                continue

            d = ds.to_dict()
            d['view_only'] = all(project(ds.groups, self.current_user.groups).values())
            response[ds.id] = d

        return response.values()

    @require_admin
    def post(self):
        req = request.get_json(True)
        required_fields = ('options', 'name', 'type')
        for f in required_fields:
            if f not in req:
                abort(400)

        schema = get_configuration_schema_for_type(req['type'])
        if schema is None:
            abort(400)

        config = ConfigurationContainer(req['options'], schema)
        if not config.is_valid():
            abort(400)

        datasource = models.DataSource.create_with_group(org=self.current_org,
                                                         name=req['name'],
                                                         type=req['type'],
                                                         options=config)

        return datasource.to_dict(all=True)

api.add_org_resource(DataSourceAPI, '/api/data_sources/<data_source_id>', endpoint='data_source')
api.add_org_resource(DataSourceListAPI, '/api/data_sources', endpoint='data_sources')


class DataSourceSchemaAPI(BaseResource):
    def get(self, data_source_id):
        data_source = get_object_or_404(models.DataSource.get_by_id_and_org, data_source_id, self.current_org)
        all = request.args.get('all', False)
        schema = data_source.get_schema(all=all)

        return schema
        
class DataSourceTableAPI(BaseResource):
    def get(self, table_id):
        data_source_table = get_object_or_404(models.DataSourceTable.get_by_id, table_id)
        return data_source_table.to_dict(all=True, with_joins=True)
            
    def post(self, table_id):
        req = request.get_json(True)
        if req:
            data_source_table = get_object_or_404(models.DataSourceTable.get_by_id, table_id)
        
            if req.has_key('description'):
                data_source_table.description = req['description']
            if req.has_key('tags'):
                data_source_table.tags = req['tags']
               
            data_source_table.save()
            
            return data_source_table.to_dict(all=True)
        else:
            abort(400)
    
class DataSourceColumnAPI(BaseResource):
    def get(self, column_id):
        data_source_column = get_object_or_404(models.DataSourceColumn.get_by_id, column_id)
        return data_source_column.to_dict(all=True)
            
    def post(self, column_id):
        # We only allow manual updates of description, as rest is updated from database
        req = request.get_json(True)
        required_fields = ('description',)

        for f in required_fields:
            if f not in req:
                abort(400)

        data_source_column = get_object_or_404(models.DataSourceColumn.get_by_id, column_id)
        
        data_source_column.description = req['description']
           
        data_source_column.save()
            
        return data_source_column.to_dict(all=True)


class DataSourceJoinAPI(BaseResource):
    def post(self, column_id):
        req = request.get_json(True)
        required_fields = ('table', 'column', 'related_table',
                           'related_column', 'cardinality')

        for f in required_fields:
            if f not in req:
                abort(400)
        
        join = models.DataSourceJoin.create(
            table=req['table'],
            column=req['column'],
            related_table=req['related_table'],
            related_column=req['related_column'],
            cardinality=req['cardinality']
        )

        return join.to_dict(all=True)

               
api.add_org_resource(DataSourceSchemaAPI, '/api/data_sources/<data_source_id>/schema')
api.add_org_resource(DataSourceTableAPI, '/api/tables/<table_id>/schema')
api.add_org_resource(DataSourceColumnAPI, '/api/columns/<column_id>/schema')
api.add_org_resource(DataSourceJoinAPI,'/api/joins/<join_id>')
