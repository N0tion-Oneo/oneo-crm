/**
 * Oneo CRM JavaScript SDK
 * Auto-generated client library for the Oneo CRM API
 * 
 * Usage:
 *   import { OneoCrmClient } from './oneo-crm-client.js';
 *   
 *   const client = new OneoCrmClient({
 *     baseUrl: 'https://api.your-domain.com',
 *     jwtToken: 'your-jwt-token'
 *   });
 *   
 *   // List pipelines
 *   const pipelines = await client.pipelines.list();
 *   
 *   // Create a pipeline
 *   const pipeline = await client.pipelines.create({
 *     name: 'Sales Pipeline',
 *     pipelineType: 'crm'
 *   });
 *   
 *   // Create a record
 *   const record = await client.records.create(pipeline.id, {
 *     companyName: 'Acme Corp',
 *     dealValue: 50000
 *   });
 */

class OneoCrmAPIError extends Error {
  constructor(message, statusCode = null, responseData = null) {
    super(message);
    this.name = 'OneoCrmAPIError';
    this.statusCode = statusCode;
    this.responseData = responseData;
  }
}

class BaseResource {
  constructor(client) {
    this.client = client;
  }

  async _makeRequest(method, endpoint, data = null, params = null) {
    const url = new URL(`/api/{{ api_version }}/${endpoint}`, this.client.baseUrl);
    
    // Add query parameters
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== null && params[key] !== undefined) {
          url.searchParams.append(key, params[key]);
        }
      });
    }

    const headers = {
      'Content-Type': 'application/json',
      'User-Agent': 'oneo-crm-js-client/1.0.0',
    };

    if (this.client.jwtToken) {
      headers['Authorization'] = `Bearer ${this.client.jwtToken}`;
    } else if (this.client.apiKey) {
      headers['X-API-Key'] = this.client.apiKey;
    }

    const options = {
      method: method.toUpperCase(),
      headers,
    };

    if (data) {
      options.body = JSON.stringify(data);
    }

    try {
      const response = await fetch(url.toString(), options);
      
      // Handle rate limiting
      if (response.status === 429) {
        const errorData = await response.json().catch(() => ({}));
        throw new OneoCrmAPIError(
          'Rate limit exceeded. Please wait before making more requests.',
          429,
          errorData
        );
      }

      // Handle other errors
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.error || `HTTP ${response.status} error`;
        throw new OneoCrmAPIError(errorMessage, response.status, errorData);
      }

      // Return empty object for successful requests with no content
      if (response.status === 204) {
        return {};
      }

      return await response.json();
      
    } catch (error) {
      if (error instanceof OneoCrmAPIError) {
        throw error;
      }
      throw new OneoCrmAPIError(`Request failed: ${error.message}`);
    }
  }
}

class PipelinesResource extends BaseResource {
  /**
   * List pipelines with optional filtering
   */
  async list({ page = 1, pageSize = 50, search = null, pipelineType = null, isActive = null } = {}) {
    const params = { page, page_size: pageSize };
    
    if (search) params.search = search;
    if (pipelineType) params.pipeline_type = pipelineType;
    if (isActive !== null) params.is_active = isActive;
    
    return this._makeRequest('GET', 'pipelines/', null, params);
  }

  /**
   * Get a specific pipeline by ID
   */
  async get(pipelineId) {
    return this._makeRequest('GET', `pipelines/${pipelineId}/`);
  }

  /**
   * Create a new pipeline
   */
  async create(data) {
    return this._makeRequest('POST', 'pipelines/', data);
  }

  /**
   * Update an existing pipeline
   */
  async update(pipelineId, data) {
    return this._makeRequest('PUT', `pipelines/${pipelineId}/`, data);
  }

  /**
   * Delete a pipeline
   */
  async delete(pipelineId) {
    return this._makeRequest('DELETE', `pipelines/${pipelineId}/`);
  }

  /**
   * Get analytics data for a pipeline
   */
  async getAnalytics(pipelineId) {
    return this._makeRequest('GET', `pipelines/${pipelineId}/analytics/`);
  }

  /**
   * Export pipeline data
   */
  async exportData(pipelineId, format = 'csv') {
    const url = new URL(`/api/{{ api_version }}/pipelines/${pipelineId}/export/`, this.client.baseUrl);
    url.searchParams.append('format', format);

    const headers = {};
    if (this.client.jwtToken) {
      headers['Authorization'] = `Bearer ${this.client.jwtToken}`;
    }

    const response = await fetch(url.toString(), { headers });
    
    if (!response.ok) {
      throw new OneoCrmAPIError(`Export failed: ${response.status}`);
    }

    return response.blob();
  }
}

class RecordsResource extends BaseResource {
  /**
   * List records in a pipeline
   */
  async list(pipelineId, { page = 1, pageSize = 50, search = null, status = null } = {}) {
    const params = { page, page_size: pageSize };
    
    if (search) params.search = search;
    if (status) params.status = status;
    
    return this._makeRequest('GET', `pipelines/${pipelineId}/records/`, null, params);
  }

  /**
   * Get a specific record
   */
  async get(pipelineId, recordId) {
    return this._makeRequest('GET', `pipelines/${pipelineId}/records/${recordId}/`);
  }

  /**
   * Create a new record
   */
  async create(pipelineId, data, status = 'active') {
    const payload = {
      data,
      status
    };
    return this._makeRequest('POST', `pipelines/${pipelineId}/records/`, payload);
  }

  /**
   * Update an existing record
   */
  async update(pipelineId, recordId, data) {
    return this._makeRequest('PUT', `pipelines/${pipelineId}/records/${recordId}/`, { data });
  }

  /**
   * Delete a record
   */
  async delete(pipelineId, recordId) {
    return this._makeRequest('DELETE', `pipelines/${pipelineId}/records/${recordId}/`);
  }

  /**
   * Create multiple records at once
   */
  async bulkCreate(pipelineId, records) {
    return this._makeRequest('POST', `pipelines/${pipelineId}/records/bulk/`, { records });
  }

  /**
   * Update multiple records at once
   */
  async bulkUpdate(pipelineId, updates) {
    return this._makeRequest('PUT', `pipelines/${pipelineId}/records/bulk/`, { updates });
  }
}

class RelationshipsResource extends BaseResource {
  /**
   * List relationships for a record
   */
  async list(recordId) {
    return this._makeRequest('GET', `records/${recordId}/relationships/`);
  }

  /**
   * Create a relationship between records
   */
  async create(fromRecordId, toRecordId, relationshipType, metadata = {}) {
    const data = {
      from_record_id: fromRecordId,
      to_record_id: toRecordId,
      relationship_type: relationshipType,
      metadata
    };
    return this._makeRequest('POST', 'relationships/', data);
  }

  /**
   * Delete a relationship
   */
  async delete(relationshipId) {
    return this._makeRequest('DELETE', `relationships/${relationshipId}/`);
  }
}

class SearchResource extends BaseResource {
  /**
   * Perform global search across records
   */
  async search(query, { pipelineIds = null, limit = 50 } = {}) {
    const params = {
      q: query,
      limit
    };
    
    if (pipelineIds && pipelineIds.length > 0) {
      params.pipeline_ids = pipelineIds.join(',');
    }
    
    return this._makeRequest('GET', 'search/', null, params);
  }
}

class GraphQLResource extends BaseResource {
  /**
   * Execute a GraphQL query
   */
  async query(query, variables = {}) {
    const url = new URL('/graphql/', this.client.baseUrl);
    
    const headers = {
      'Content-Type': 'application/json'
    };
    
    if (this.client.jwtToken) {
      headers['Authorization'] = `Bearer ${this.client.jwtToken}`;
    }

    const data = {
      query,
      variables
    };

    try {
      const response = await fetch(url.toString(), {
        method: 'POST',
        headers,
        body: JSON.stringify(data)
      });

      if (!response.ok) {
        throw new OneoCrmAPIError(`GraphQL request failed: ${response.status}`);
      }

      const result = await response.json();

      if (result.errors && result.errors.length > 0) {
        const errorMessages = result.errors.map(error => error.message);
        throw new OneoCrmAPIError(`GraphQL errors: ${errorMessages.join('; ')}`);
      }

      return result;
    } catch (error) {
      if (error instanceof OneoCrmAPIError) {
        throw error;
      }
      throw new OneoCrmAPIError(`GraphQL request failed: ${error.message}`);
    }
  }
}

class WebSocketResource {
  constructor(client) {
    this.client = client;
    this.ws = null;
    this.subscriptions = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  /**
   * Connect to WebSocket for real-time updates
   */
  connect() {
    return new Promise((resolve, reject) => {
      const wsUrl = this.client.baseUrl.replace('http', 'ws') + `/ws/sse/?token=${this.client.jwtToken}`;
      
      this.ws = new WebSocket(wsUrl);
      
      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        resolve();
      };
      
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this._handleMessage(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };
      
      this.ws.onclose = () => {
        this._handleDisconnect();
      };
      
      this.ws.onerror = (error) => {
        reject(error);
      };
    });
  }

  /**
   * Subscribe to real-time updates
   */
  subscribe(subscription, filters = {}, callback = null) {
    const subscriptionId = `${subscription}_${Date.now()}`;
    
    if (callback) {
      this.subscriptions.set(subscriptionId, callback);
    }
    
    const message = {
      type: 'subscribe',
      subscription,
      id: subscriptionId,
      filters
    };
    
    this._send(message);
    return subscriptionId;
  }

  /**
   * Unsubscribe from updates
   */
  unsubscribe(subscriptionId) {
    this.subscriptions.delete(subscriptionId);
    
    const message = {
      type: 'unsubscribe',
      id: subscriptionId
    };
    
    this._send(message);
  }

  /**
   * Disconnect WebSocket
   */
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.subscriptions.clear();
  }

  _send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  _handleMessage(data) {
    const { subscription_id, type, data: messageData } = data;
    
    if (subscription_id && this.subscriptions.has(subscription_id)) {
      const callback = this.subscriptions.get(subscription_id);
      callback(messageData, type);
    }
  }

  _handleDisconnect() {
    // Attempt to reconnect
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        this.connect().catch(console.error);
      }, Math.pow(2, this.reconnectAttempts) * 1000);
    }
  }
}

/**
 * Main client class for Oneo CRM API
 */
export class OneoCrmClient {
  constructor({ baseUrl = '{{ base_url }}', jwtToken = null, apiKey = null, timeout = 30000 } = {}) {
    if (!jwtToken && !apiKey) {
      throw new Error('Either jwtToken or apiKey must be provided');
    }

    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.jwtToken = jwtToken;
    this.apiKey = apiKey;
    this.timeout = timeout;

    // Initialize resource endpoints
    this.pipelines = new PipelinesResource(this);
    this.records = new RecordsResource(this);
    this.relationships = new RelationshipsResource(this);
    this.search = new SearchResource(this);
    this.graphql = new GraphQLResource(this);
    this.websocket = new WebSocketResource(this);
  }

  /**
   * Update the JWT token
   */
  setJwtToken(token) {
    this.jwtToken = token;
  }

  /**
   * Update the API key
   */
  setApiKey(apiKey) {
    this.apiKey = apiKey;
  }

  /**
   * Check API health status
   */
  async healthCheck() {
    const url = new URL('/api/health/', this.baseUrl);
    const response = await fetch(url.toString());
    return response.json();
  }
}

/**
 * Convenience function to create client from environment variables
 */
export function createClientFromEnv() {
  const baseUrl = process.env.ONEO_CRM_BASE_URL || '{{ base_url }}';
  const jwtToken = process.env.ONEO_CRM_JWT_TOKEN;
  const apiKey = process.env.ONEO_CRM_API_KEY;

  return new OneoCrmClient({
    baseUrl,
    jwtToken,
    apiKey
  });
}

// Export error class for external use
export { OneoCrmAPIError };

// Example usage (for Node.js environments)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { OneoCrmClient, OneoCrmAPIError, createClientFromEnv };
}

// Example usage
/*
(async () => {
  try {
    // Initialize client
    const client = new OneoCrmClient({
      baseUrl: 'https://api.your-domain.com',
      jwtToken: 'your-jwt-token-here'
    });

    // Health check
    const health = await client.healthCheck();
    console.log(`API Status: ${health.status}`);

    // List pipelines
    const pipelines = await client.pipelines.list({ pageSize: 10 });
    console.log(`Found ${pipelines.count} pipelines`);

    // Create a new pipeline
    const newPipeline = await client.pipelines.create({
      name: 'Test Pipeline',
      description: 'A test pipeline created with JavaScript SDK',
      pipelineType: 'custom'
    });
    console.log(`Created pipeline: ${newPipeline.id}`);

    // Create a record in the pipeline
    const newRecord = await client.records.create(newPipeline.id, {
      name: 'Test Record',
      description: 'A test record',
      value: 1000
    });
    console.log(`Created record: ${newRecord.id}`);

    // Search for records
    const searchResults = await client.search.search('Test', { limit: 5 });
    console.log(`Search found ${searchResults.results.length} results`);

    // GraphQL query example
    const graphqlResult = await client.graphql.query(`
      query GetPipelines {
        pipelines {
          id
          name
          recordCount
        }
      }
    `);
    console.log(`GraphQL returned ${graphqlResult.data.pipelines.length} pipelines`);

    // WebSocket example
    await client.websocket.connect();
    
    const subscriptionId = client.websocket.subscribe('record_updates', 
      { pipeline_id: newPipeline.id },
      (data, type) => {
        console.log(`Received ${type} update:`, data);
      }
    );

  } catch (error) {
    if (error instanceof OneoCrmAPIError) {
      console.error(`API Error: ${error.message}`);
      if (error.responseData) {
        console.error(`Response:`, error.responseData);
      }
    } else {
      console.error(`Unexpected error:`, error);
    }
  }
})();
*/