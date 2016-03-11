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
        
class DataSourceTableSchemaAPI(BaseResource):
    def get(self, table_id):
        data_source_table = get_object_or_404(models.DataSourceTable.get_by_id, table_id)
        return data_source_table.to_dict(all=True)
            
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
    
class DataSourceColumnSchemaAPI(BaseResource):
    def get(self, column_id):
        data_source_column = get_object_or_404(models.DataSourceColumn.get_by_id, column_id)
        return data_source_column.to_dict(all=True)
            
    def post(self, column_id):
        req = request.get_json(True)
        if req:
            data_source_column = get_object_or_404(models.DataSourceColumn.get_by_id, column_id)
        
            if req.has_key('joins'):
                data_source_column.joins = req['joins']
            if req.has_key('description'):
                data_source_column.description = req['description']
            if req.has_key('tags'):
                data_source_column.tags = req['tags']
               
            data_source_column.save()
            
            return data_source_column.to_dict(all=True)
        else:
            abort(400)
               
api.add_org_resource(DataSourceSchemaAPI, '/api/data_sources/<data_source_id>/schema')
api.add_org_resource(DataSourceTableSchemaAPI, '/api/tables/<table_id>/schema')
api.add_org_resource(DataSourceColumnSchemaAPI, '/api/columns/<column_id>/schema')

class DataSourceColumnJoinListAPI(BaseResource):
    def get(self,table_id):
        model = get_object_or_404(models.DataSourceColumnJoin.get_by_table,table_id)
        join_col = [m.to_dict() for m in model['join_col'] if model['join_col']]
        join_rel = [m.to_dict(is_related=True) for m in model['join_rel'] if model['join_rel'] ]
        schema = join_col + join_rel
        return schema

    def post(self,table_id):
        table_model = get_object_or_404(models.DataSourceTable.get_by_id,table_id)
        req = request.get_json(True)
        if isinstance(req,list):
            joins = []
            for req_jn in req:
                if req_jn.has_key('column') and req_jn.has_key('related_column') \
                    and req_jn.has_key('related_table') and req_jn.has_key('cardinality'):
                    column_model = get_object_or_404(models.DataSourceColumn.get_by_id,req_jn['column'])
                    if column_model.table.id != table_model.id:
                        abort(400)
                    related_column_model = get_object_or_404(models.DataSourceColumn.get_by_id,req_jn['related_column'])
                    jn, created = models.DataSourceColumnJoin.get_or_create(related_table = related_column_model.table
                          ,related_column = related_column_model
                          ,cardinality = req_jn['cardinality']
                          ,table = column_model.table
                          ,column = column_model)
                    joins.append(jn.to_dict(all=True))
                else:
                    abort(400)
            return joins
        else:
            abort(400)


class DataSourceColumnJoinAPI(BaseResource):
    def get(self,column_id):
        column_model = get_object_or_404(models.DataSourceColumn.get_by_id, column_id)
        model = models.DataSourceColumnJoin.get_by_column(column_model.id)
        join_col = [m.to_dict() for m in model['join_col'] if model['join_col']]
        join_rel = [m.to_dict(is_related=True) for m in model['join_rel'] if model['join_rel'] ]
        schema = join_col + join_rel
        return schema

    def post(self, column_id):
        column_model = get_object_or_404(models.DataSourceColumn.get_by_id, column_id)
        req = request.get_json(True)
        if req.has_key('related_column') and req.has_key('related_table') and req.has_key('cardinality'):
            jn, created = models.DataSourceColumnJoin.get_or_create(related_table = req['related_table']
                  ,related_column = req['related_column']
                  ,cardinality = req['cardinality']
                  ,table = column_model.table.id
                  ,column = column_model.id)
            return jn.to_dict(all=True)
        else:
            abort(400)

api.add_org_resource(DataSourceColumnJoinListAPI,'/api/data_sources/joins/table/<table_id>')
api.add_org_resource(DataSourceColumnJoinAPI,'/api/data_sources/joins/column/<column_id>')