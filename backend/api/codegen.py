"""
Client SDK generation utilities for Oneo CRM API
Generates client libraries in multiple languages from OpenAPI schema
"""
import json
import os
from typing import Dict, Any, List
from django.conf import settings
from django.template.loader import render_to_string
from drf_spectacular.openapi import AutoSchema
from api.docs import generate_graphql_docs


class SDKGenerator:
    """
    Generate client SDKs for different programming languages.
    """
    
    def __init__(self):
        self.base_url = getattr(settings, 'API_BASE_URL', 'https://api.example.com')
        self.api_version = 'v1'
    
    def generate_python_sdk(self, schema: Dict[str, Any]) -> str:
        """Generate Python SDK code."""
        return render_to_string('api/sdk/python_sdk.py', {
            'base_url': self.base_url,
            'api_version': self.api_version,
            'schema': schema,
            'endpoints': self._extract_endpoints(schema),
            'models': self._extract_models(schema)
        })
    
    def generate_javascript_sdk(self, schema: Dict[str, Any]) -> str:
        """Generate JavaScript/TypeScript SDK code."""
        return render_to_string('api/sdk/javascript_sdk.js', {
            'base_url': self.base_url,
            'api_version': self.api_version,
            'schema': schema,
            'endpoints': self._extract_endpoints(schema),
            'models': self._extract_models(schema)
        })
    
    def generate_curl_examples(self, schema: Dict[str, Any]) -> str:
        """Generate curl command examples."""
        examples = []
        endpoints = self._extract_endpoints(schema)
        
        for endpoint in endpoints:
            if endpoint['method'].upper() == 'GET':
                examples.append(f"""
# {endpoint['summary']}
curl -X {endpoint['method'].upper()} \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  "{self.base_url}/api/{self.api_version}{endpoint['path']}"
""")
            elif endpoint['method'].upper() in ['POST', 'PUT', 'PATCH']:
                examples.append(f"""
# {endpoint['summary']}
curl -X {endpoint['method'].upper()} \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{endpoint.get('example_payload', '{}')}' \\
  "{self.base_url}/api/{self.api_version}{endpoint['path']}"
""")
        
        return '\n'.join(examples)
    
    def generate_postman_collection(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Postman collection for API testing."""
        collection = {
            "info": {
                "name": "Oneo CRM API",
                "description": "Complete API collection for Oneo CRM",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "auth": {
                "type": "bearer",
                "bearer": [
                    {
                        "key": "token",
                        "value": "{{jwt_token}}",
                        "type": "string"
                    }
                ]
            },
            "variable": [
                {
                    "key": "base_url",
                    "value": self.base_url,
                    "type": "string"
                }
            ],
            "item": []
        }
        
        endpoints = self._extract_endpoints(schema)
        
        # Group endpoints by tag/category
        grouped_endpoints = {}
        for endpoint in endpoints:
            tag = endpoint.get('tag', 'General')
            if tag not in grouped_endpoints:
                grouped_endpoints[tag] = []
            grouped_endpoints[tag].append(endpoint)
        
        # Create folder for each tag
        for tag, tag_endpoints in grouped_endpoints.items():
            folder = {
                "name": tag,
                "item": []
            }
            
            for endpoint in tag_endpoints:
                request_item = {
                    "name": endpoint['summary'],
                    "request": {
                        "method": endpoint['method'].upper(),
                        "header": [
                            {
                                "key": "Content-Type",
                                "value": "application/json",
                                "type": "text"
                            }
                        ],
                        "url": {
                            "raw": f"{{{{base_url}}}}/api/{self.api_version}{endpoint['path']}",
                            "host": ["{{base_url}}"],
                            "path": ["api", self.api_version] + endpoint['path'].strip('/').split('/')
                        },
                        "description": endpoint.get('description', '')
                    }
                }
                
                # Add body for POST/PUT/PATCH requests
                if endpoint['method'].upper() in ['POST', 'PUT', 'PATCH']:
                    request_item['request']['body'] = {
                        "mode": "raw",
                        "raw": endpoint.get('example_payload', '{}'),
                        "options": {
                            "raw": {
                                "language": "json"
                            }
                        }
                    }
                
                folder['item'].append(request_item)
            
            collection['item'].append(folder)
        
        return collection
    
    def generate_openapi_client_config(self, language: str) -> Dict[str, Any]:
        """Generate configuration for OpenAPI Generator clients."""
        configs = {
            'python': {
                'generatorName': 'python',
                'packageName': 'oneo_crm_client',
                'projectName': 'oneo-crm-python-client',
                'packageVersion': '1.0.0',
                'packageUrl': 'https://github.com/your-org/oneo-crm-python-client',
                'additionalProperties': {
                    'generateSourceCodeOnly': True,
                    'library': 'urllib3'
                }
            },
            'javascript': {
                'generatorName': 'javascript',
                'packageName': 'oneo-crm-client',
                'projectName': 'oneo-crm-js-client',
                'projectVersion': '1.0.0',
                'additionalProperties': {
                    'usePromises': True,
                    'moduleName': 'OneoCrmClient'
                }
            },
            'typescript': {
                'generatorName': 'typescript-axios',
                'packageName': 'oneo-crm-client',
                'npmName': '@oneo/crm-client',
                'packageVersion': '1.0.0',
                'additionalProperties': {
                    'withInterfaces': True,
                    'useSingleRequestParameter': True
                }
            },
            'go': {
                'generatorName': 'go',
                'packageName': 'oneo_crm_client',
                'moduleName': 'github.com/your-org/oneo-crm-go-client',
                'packageVersion': '1.0.0',
                'additionalProperties': {
                    'packageUrl': 'github.com/your-org/oneo-crm-go-client'
                }
            },
            'java': {
                'generatorName': 'java',
                'artifactId': 'oneo-crm-client',
                'groupId': 'com.oneo.crm',
                'packageName': 'com.oneo.crm.client',
                'artifactVersion': '1.0.0',
                'additionalProperties': {
                    'library': 'okhttp-gson',
                    'invokerPackage': 'com.oneo.crm.client',
                    'modelPackage': 'com.oneo.crm.client.model',
                    'apiPackage': 'com.oneo.crm.client.api'
                }
            }
        }
        
        return configs.get(language, {})
    
    def _extract_endpoints(self, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract endpoint information from OpenAPI schema."""
        endpoints = []
        paths = schema.get('paths', {})
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method in ['get', 'post', 'put', 'patch', 'delete']:
                    endpoint = {
                        'path': path,
                        'method': method,
                        'summary': operation.get('summary', ''),
                        'description': operation.get('description', ''),
                        'tag': operation.get('tags', ['General'])[0],
                        'parameters': operation.get('parameters', []),
                        'responses': operation.get('responses', {}),
                    }
                    
                    # Extract example payload for request body
                    if 'requestBody' in operation:
                        request_body = operation['requestBody']
                        content = request_body.get('content', {})
                        json_content = content.get('application/json', {})
                        example = json_content.get('example', {})
                        endpoint['example_payload'] = json.dumps(example, indent=2)
                    
                    endpoints.append(endpoint)
        
        return endpoints
    
    def _extract_models(self, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract model/schema definitions from OpenAPI schema."""
        models = []
        components = schema.get('components', {})
        schemas = components.get('schemas', {})
        
        for model_name, model_schema in schemas.items():
            model = {
                'name': model_name,
                'type': model_schema.get('type', 'object'),
                'description': model_schema.get('description', ''),
                'properties': model_schema.get('properties', {}),
                'required': model_schema.get('required', [])
            }
            models.append(model)
        
        return models


class GraphQLSDKGenerator:
    """
    Generate GraphQL client SDKs and utilities.
    """
    
    def __init__(self):
        self.endpoint = '/graphql/'
        self.ws_endpoint = '/ws/graphql/'
    
    def generate_graphql_schema_file(self) -> str:
        """Generate GraphQL schema definition file."""
        # This would normally use introspection to get the schema
        # For now, return a placeholder
        return """
type Query {
  pipelines: [Pipeline!]!
  pipeline(id: ID!): Pipeline
  records(pipelineId: ID!, limit: Int, offset: Int): [Record!]!
  record(id: ID!): Record
  globalSearch(query: String!, pipelineIds: [ID!], limit: Int): [Record!]!
}

type Mutation {
  createPipeline(input: CreatePipelineInput!): CreatePipelinePayload!
  createRecord(pipelineId: ID!, input: CreateRecordInput!): CreateRecordPayload!
  updateRecord(id: ID!, input: UpdateRecordInput!): UpdateRecordPayload!
  deleteRecord(id: ID!): DeleteRecordPayload!
}

type Subscription {
  recordUpdates(pipelineId: String, recordId: String): Record!
  pipelineUpdates(pipelineId: String): Pipeline!
  activityFeed(pipelineId: String): String!
}

type Pipeline {
  id: ID!
  name: String!
  slug: String!
  description: String
  recordCount: Int!
  records(limit: Int, offset: Int): [Record!]!
  createdAt: DateTime!
  updatedAt: DateTime!
}

type Record {
  id: ID!
  title: String
  data: JSON!
  pipeline: Pipeline!
  createdAt: DateTime!
  updatedAt: DateTime!
}

input CreatePipelineInput {
  name: String!
  description: String
  pipelineType: String
  icon: String
  color: String
}

input CreateRecordInput {
  data: JSON!
  status: String
}

scalar DateTime
scalar JSON
"""
    
    def generate_apollo_client_config(self) -> str:
        """Generate Apollo Client configuration."""
        return """
import { ApolloClient, InMemoryCache, createHttpLink, split } from '@apollo/client';
import { setContext } from '@apollo/client/link/context';
import { GraphQLWsLink } from '@apollo/client/link/subscriptions';
import { createClient } from 'graphql-ws';
import { getMainDefinition } from '@apollo/client/utilities';

// HTTP link for queries and mutations
const httpLink = createHttpLink({
  uri: 'YOUR_API_BASE_URL/graphql/',
});

// WebSocket link for subscriptions
const wsLink = new GraphQLWsLink(createClient({
  url: 'wss://YOUR_API_BASE_URL/ws/graphql/',
  connectionParams: {
    authToken: localStorage.getItem('jwt_token'),
  },
}));

// Auth link to add JWT token to requests
const authLink = setContext((_, { headers }) => {
  const token = localStorage.getItem('jwt_token');
  
  return {
    headers: {
      ...headers,
      authorization: token ? `Bearer ${token}` : "",
    }
  }
});

// Split link - use WebSocket for subscriptions, HTTP for everything else
const splitLink = split(
  ({ query }) => {
    const definition = getMainDefinition(query);
    return (
      definition.kind === 'OperationDefinition' &&
      definition.operation === 'subscription'
    );
  },
  wsLink,
  authLink.concat(httpLink),
);

// Create Apollo Client
export const apolloClient = new ApolloClient({
  link: splitLink,
  cache: new InMemoryCache(),
  defaultOptions: {
    watchQuery: {
      errorPolicy: 'ignore',
    },
    query: {
      errorPolicy: 'all',
    },
    mutate: {
      errorPolicy: 'all',
    },
  },
});
"""


def generate_all_sdks(output_dir: str = '/tmp/oneo_crm_sdks') -> Dict[str, str]:
    """
    Generate all SDK files and return their paths.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    generator = SDKGenerator()
    graphql_generator = GraphQLSDKGenerator()
    
    # Mock schema for now - in production, get from drf-spectacular
    mock_schema = {
        'openapi': '3.0.0',
        'info': {'title': 'Oneo CRM API', 'version': '1.0.0'},
        'paths': {},
        'components': {'schemas': {}}
    }
    
    generated_files = {}
    
    # Generate Python SDK
    python_sdk = generator.generate_python_sdk(mock_schema)
    python_path = os.path.join(output_dir, 'oneo_crm_client.py')
    with open(python_path, 'w') as f:
        f.write(python_sdk)
    generated_files['python'] = python_path
    
    # Generate JavaScript SDK
    js_sdk = generator.generate_javascript_sdk(mock_schema)
    js_path = os.path.join(output_dir, 'oneo-crm-client.js')
    with open(js_path, 'w') as f:
        f.write(js_sdk)
    generated_files['javascript'] = js_path
    
    # Generate curl examples
    curl_examples = generator.generate_curl_examples(mock_schema)
    curl_path = os.path.join(output_dir, 'curl_examples.sh')
    with open(curl_path, 'w') as f:
        f.write(curl_examples)
    generated_files['curl'] = curl_path
    
    # Generate Postman collection
    postman_collection = generator.generate_postman_collection(mock_schema)
    postman_path = os.path.join(output_dir, 'oneo_crm_api.postman_collection.json')
    with open(postman_path, 'w') as f:
        json.dump(postman_collection, f, indent=2)
    generated_files['postman'] = postman_path
    
    # Generate GraphQL schema
    graphql_schema = graphql_generator.generate_graphql_schema_file()
    schema_path = os.path.join(output_dir, 'schema.graphql')
    with open(schema_path, 'w') as f:
        f.write(graphql_schema)
    generated_files['graphql_schema'] = schema_path
    
    # Generate Apollo Client config
    apollo_config = graphql_generator.generate_apollo_client_config()
    apollo_path = os.path.join(output_dir, 'apollo-client-config.js')
    with open(apollo_path, 'w') as f:
        f.write(apollo_config)
    generated_files['apollo_config'] = apollo_path
    
    return generated_files