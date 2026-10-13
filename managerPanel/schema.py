import ast
import inspect
import textwrap

from drf_spectacular.openapi import AutoSchema
from drf_spectacular.types import OpenApiTypes

from rest_framework import serializers


class BackendSchema(AutoSchema):
    """Document legacy views without running their database querysets."""

    def _legacy_serializer(self, request=False):
        method = getattr(self.view, self.method.lower(), None)
        # Function-based DRF views keep their original function in the handler closure.
        if method and method.__closure__:
            method = next((c.cell_contents for c in method.__closure__
                           if inspect.isfunction(c.cell_contents)), method)
        fields = {}
        name = self.view.__class__.__name__
        if request and name in ('LoginView', 'GenerateTraccarTokenView', 'TraccarSessionView'):
            fields = {'password': serializers.CharField(write_only=True, style={'input_type': 'password'})}
            if name == 'LoginView':
                fields['phone'] = serializers.CharField()
            return type(f'{name}Request', (serializers.Serializer,), fields)()
        if not request and name == 'CheckTraccarTokenView':
            return {
                200: {'type': 'object', 'required': ['message', 'valid', 'requires_regeneration'],
                      'properties': {'message': {'type': 'string'}, 'valid': {'type': 'boolean'},
                                     'requires_regeneration': {'type': 'boolean'}}},
                401: {'type': 'object', 'properties': {'detail': {'type': 'string'}}},
                502: {'type': 'object', 'properties': {'message': {'type': 'string'}}},
                503: {'type': 'object', 'properties': {'message': {'type': 'string'}}},
            }
        if not request and name == 'GenerateTraccarTokenView':
            return {200: {'type': 'object', 'properties': {
                'message': {'type': 'string'}, 'token': {'type': 'string'},
                'traccar_id': {'type': 'integer'}}},
                400: {'type': 'object', 'additionalProperties': True},
                401: {'type': 'object', 'additionalProperties': True}}
        if request and method:
            tree = ast.parse(textwrap.dedent(inspect.getsource(method)))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                target = node.func.value
                if (node.func.attr == 'get' and isinstance(target, ast.Attribute)
                        and target.attr == 'data' and node.args
                        and isinstance(node.args[0], ast.Constant)
                        and isinstance(node.args[0].value, str)):
                    name = node.args[0].value
                    fields[name] = serializers.JSONField(required=False)
        if not fields:
            # ponytail: opaque legacy payloads; add explicit serializers as contracts stabilize.
            return OpenApiTypes.OBJECT if request else {200: OpenApiTypes.OBJECT}
        return type(f'{self.view.__class__.__name__}{self.method.title()}Request',
                    (serializers.Serializer,), fields)()

    def get_operation_id(self):
        return self.method.lower() + '_' + self.path.strip('/').replace('/', '_').replace('{', '').replace('}', '')



    def get_request_serializer(self):
        if getattr(self.view, 'serializer_class', None):
            return super().get_request_serializer()
        return self._legacy_serializer(request=True)

    def get_response_serializers(self):
        if getattr(self.view, 'serializer_class', None):
            return super().get_response_serializers()
        return self._legacy_serializer()
