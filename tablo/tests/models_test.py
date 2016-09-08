from collections import OrderedDict

from django.test import TestCase
from tablo.models import FeatureService, FeatureServiceLayer, FeatureServiceLayerRelations
from unittest.mock import patch, PropertyMock


TABLE_NAME = 'db_table'


class PerformQueryTestCase(TestCase):

    def setUp(self):
        feature_service = FeatureService.objects.create(description='FeatureServiceTestOne')
        self.feature_service_layer = FeatureServiceLayer.objects.create(
            service=feature_service,
            layer_order=0,
            table=TABLE_NAME,
            name='FeatureServiceLayerTestOne',
            object_id_field='db_id'
        )

        self.relationship = FeatureServiceLayerRelations.objects.create(
            layer=self.feature_service_layer,
            related_index=0,
            related_title='measurements',
            source_column='base_table_field',
            target_column='base_table_field_ref'
        )

        feature_service2 = FeatureService.objects.create(description='FeatureServiceTestTwo')
        self.feature_service_layer2 = FeatureServiceLayer.objects.create(
            service=feature_service2,
            layer_order=0,
            table=TABLE_NAME,
            name='FeatureServiceLayerTestTwo',
            object_id_field='db_id'
        )

        self.relationship2 = FeatureServiceLayerRelations.objects.create(
            layer=self.feature_service_layer2,
            related_index=0,
            related_title='measurements',
            source_column='casgem_station_id',
            target_column='casgem_station_id'
        )

    def test_no_where_clause(self):
        self.validate_perform_query_sql(
            {},
            ('SELECT "source".*, ST_AsText(ST_Transform("source"."dbasin_geom", 3857)) '
             'FROM "{table}" AS "source"  WHERE 1=1 ORDER BY "source".* LIMIT 0 OFFSET 0').format(
                table=TABLE_NAME
            )
        )

    def test_additional_where_clause(self):
        # Mock out the fields for the table
        with patch('tablo.models.FeatureServiceLayer.fields', new_callable=PropertyMock) as fields:
            fields.return_value = ([{
                'name': 'TEST',
                'alias': 'TEST',
                'type': 'esriFieldTypeInteger',
                'nullable': True,
                'editable': True
            }])
            self.validate_perform_query_sql(
                {'additional_where_clause': 'TEST=1'},
                ('SELECT "source".*, ST_AsText(ST_Transform("source"."dbasin_geom", 3857)) '
                 'FROM "{table}" AS "source"  WHERE "source"."TEST"=1 '
                 'ORDER BY "source".* LIMIT 0 OFFSET 0').format(
                    table=TABLE_NAME
                )
            )

    def test_related_query(self):
        with patch('tablo.models.FeatureServiceLayer.fields', new_callable=PropertyMock) as fields:
            with patch('tablo.models.FeatureServiceLayer.related_fields', new_callable=PropertyMock) as related_fields:
                fields.return_value = ([{
                    'name': 'base_table_field',
                    'alias': 'base_table_field',
                    'type': 'esriFieldTypeInteger',
                    'nullable': True,
                    'editable': True
                }])

                related_fields.return_value = {
                    'measurements.base_table_field_ref': {
                        'name': 'base_table_field_ref',
                        'type': 'esriFieldTypeInteger'
                    },
                    'measurements.well_depth': {
                        'name': 'well_depth',
                        'type': 'esriFieldTypeInteger'
                    },
                }

                self.validate_perform_query_sql(
                    {'additional_where_clause': '("measurements.well_depth" > 50)'},
                    ('SELECT "source".*, ST_AsText(ST_Transform("source"."dbasin_geom", 3857)) '
                     'FROM "{table}" AS "source" LEFT OUTER JOIN "{table}_0" AS "measurements" '
                     'ON "source"."base_table_field" = "measurements"."base_table_field_ref" '
                     'WHERE ("measurements"."well_depth" > 50) '
                     'ORDER BY "source"."base_table_field" LIMIT 0 OFFSET 0').format(
                        table=TABLE_NAME
                    )
                )

    def test_related_count(self):
        with patch('tablo.models.FeatureServiceLayer.fields', new_callable=PropertyMock) as fields:
            with patch('tablo.models.FeatureServiceLayer.related_fields', new_callable=PropertyMock) as related_fields:
                fields.return_value = ([
                    {
                        'name': 'db_id'
                    },
                    {
                        'name': 'base_table_field',
                        'alias': 'base_table_field',
                        'type': 'esriFieldTypeInteger',
                        'nullable': True,
                        'editable': True
                    }
                ])

                related_fields.return_value = {
                    'measurements.base_table_field_ref': {
                        'name': 'base_table_field_ref',
                        'type': 'esriFieldTypeInteger'
                    },
                    'measurements.well_depth': {
                        'name': 'well_depth',
                        'type': 'esriFieldTypeInteger'
                    },
                }

                self.validate_perform_query_sql(
                    {
                        'additional_where_clause': '("measurements.well_depth" > 50)',
                        'ids_only': True,
                        'return_geometry': False
                    },
                    ('SELECT DISTINCT "source"."{object_id_field}" '
                     'FROM "{table}" AS "source" LEFT OUTER JOIN "{table}_0" AS "measurements" '
                     'ON "source"."base_table_field" = "measurements"."base_table_field_ref" '
                     'WHERE ("measurements"."well_depth" > 50) '
                     'ORDER BY "source"."{object_id_field}" LIMIT 0 OFFSET 0').format(
                        table=TABLE_NAME,
                        object_id_field=self.feature_service_layer.object_id_field
                    )
                )

    def test_duplicate_field(self):
        with patch('tablo.models.FeatureServiceLayer.fields', new_callable=PropertyMock) as fields:
            with patch('tablo.models.FeatureServiceLayer.related_fields', new_callable=PropertyMock) as related_fields:
                fields.return_value = ([
                    {
                        'name': 'db_id'
                    },
                    {
                        'name': 'casgem_station_id',
                        'alias': 'casgem_station_id',
                        'type': 'esriFieldTypeInteger',
                        'nullable': True,
                        'editable': True
                    }
                ])

                related_fields.return_value = OrderedDict({
                    'measurements.casgem_station_id': {
                        'name': 'casgem_station_id',
                        'type': 'esriFieldTypeInteger'
                    },
                    'measurements.something_else': {
                        'name': 'something_else',
                        'type': 'esriFieldTypeInteger'
                    },
                })

                self.validate_perform_query_sql(
                    {
                        'return_fields': ['*', 'measurements.*'],
                    },
                    ('SELECT "source"."db_id" AS "db_id", "source"."casgem_station_id" AS "casgem_station_id", '
                     '"measurements"."casgem_station_id" AS "measurements.casgem_station_id", '
                     '"measurements"."something_else" AS "measurements.something_else", '
                     'ST_AsText(ST_Transform("source"."dbasin_geom", 3857)) '
                     'FROM "{table}" AS "source" LEFT OUTER JOIN "{table}_0" AS "measurements" '
                     'ON "source"."casgem_station_id" = "measurements"."casgem_station_id" '
                     'WHERE 1=1 '
                     'ORDER BY "source"."casgem_station_id" LIMIT 0 OFFSET 0').format(
                        table=TABLE_NAME,
                        object_id_field=self.feature_service_layer2.object_id_field
                    ),
                    layer=self.feature_service_layer2
                )

    def validate_perform_query_sql(self, perform_query_args, expected_sql, expected_sql_args=None, layer=None):
        """
        This method test the FeatureServiceLayer.perform_query given.

        :param perform_query_args: The arguments that will be passed into the perform_query method. This should
          be a dict, that will be passed in as the methods kwargs.
        :param expected_sql: The SQL that is expected to be executed when the perform_query method is called.
        :param expected_sql_args: The expected arguments to be passed into the SQL as parameters.
        """
        layer = layer or self.feature_service_layer
        expected_sql_args = [] if expected_sql_args is None else expected_sql_args
        with patch('tablo.models.connection') as mockconnection:
            layer.perform_query(**perform_query_args)
            mockconnection.cursor().__enter__().execute.assert_called_with(expected_sql, expected_sql_args)