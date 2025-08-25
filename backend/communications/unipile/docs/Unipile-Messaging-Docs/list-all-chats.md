List all chats

# OpenAPI definition
```json
{
  "openapi": "3.0.0",
  "paths": {
    "/api/v1/chats": {
      "get": {
        "operationId": "ChatsController_listAllChats",
        "x-readme": {
          "code-samples": [
            {
              "language": "node",
              "code": "import { UnipileClient } from \"unipile-node-sdk\"\n\nconst BASE_URL = \"your base url\"\nconst ACCESS_TOKEN = \"your access token\"\n\ntry {\n\tconst client = new UnipileClient(BASE_URL, ACCESS_TOKEN)\n\n\tconst response = await client.messaging.getAllChats()\n} catch (error) {\n\tconsole.log(error)\n}\n",
              "name": "unipile-node-sdk",
              "install": "npm install unipile-node-sdk"
            }
          ]
        },
        "summary": "List all chats",
        "description": "Returns a list of chats. Some optional parameters are available to filter the results.",
        "parameters": [
          {
            "name": "unread",
            "required": false,
            "in": "query",
            "description": "Whether you want to get either unread chats only, or read chats only.",
            "schema": {
              "type": "boolean"
            }
          },
          {
            "name": "cursor",
            "required": false,
            "in": "query",
            "schema": {
              "title": "CursorParam",
              "description": "A cursor for pagination purposes. To get the next page of entries, you need to make a new request and fulfill this field with the cursor received in the preceding request. This process should be repeated until all entries have been retrieved.",
              "minLength": 1,
              "type": "string"
            }
          },
          {
            "name": "before",
            "required": false,
            "in": "query",
            "schema": {
              "description": "A filter to target items created before the datetime (exclusive). Must be an ISO 8601 UTC datetime (YYYY-MM-DDTHH:MM:SS.sssZ).",
              "example": "2025-12-31T23:59:59.999Z",
              "pattern": "^[1-2]\\d{3}-[0-1]\\d-[0-3]\\dT\\d{2}:\\d{2}:\\d{2}.\\d{3}Z$",
              "type": "string"
            }
          },
          {
            "name": "after",
            "required": false,
            "in": "query",
            "schema": {
              "description": "A filter to target items created after the datetime (exclusive). Must be an ISO 8601 UTC datetime (YYYY-MM-DDTHH:MM:SS.sssZ).",
              "example": "2025-12-31T23:59:59.999Z",
              "pattern": "^[1-2]\\d{3}-[0-1]\\d-[0-3]\\dT\\d{2}:\\d{2}:\\d{2}.\\d{3}Z$",
              "type": "string"
            }
          },
          {
            "name": "limit",
            "required": false,
            "in": "query",
            "schema": {
              "minimum": 1,
              "maximum": 250,
              "description": "A limit for the number of items returned in the response. The value can be set between 1 and 250.",
              "example": 100,
              "type": "integer"
            }
          },
          {
            "name": "account_type",
            "required": false,
            "in": "query",
            "description": "A filter to target items related to a certain provider.",
            "schema": {
              "enum": [
                "WHATSAPP",
                "LINKEDIN",
                "SLACK",
                "TWITTER",
                "MESSENGER",
                "INSTAGRAM",
                "TELEGRAM"
              ],
              "type": "string"
            }
          },
          {
            "name": "account_id",
            "required": false,
            "in": "query",
            "description": "A filter to target items related to a certain account. Can be a comma-separated list of ids.",
            "schema": {
              "title": "AccountIdOrIdsParam",
              "description": "An Unipile account id or a list of Unipile account ids separated by commas.",
              "minLength": 1,
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "OK. Request succeeded.",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "object": {
                      "type": "string",
                      "enum": [
                        "ChatList"
                      ]
                    },
                    "items": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "object": {
                            "type": "string",
                            "enum": [
                              "Chat"
                            ]
                          },
                          "id": {
                            "title": "UniqueId",
                            "description": "A unique identifier.",
                            "minLength": 1,
                            "type": "string"
                          },
                          "account_id": {
                            "title": "UniqueId",
                            "description": "A unique identifier.",
                            "minLength": 1,
                            "type": "string"
                          },
                          "account_type": {
                            "anyOf": [
                              {
                                "type": "string",
                                "enum": [
                                  "WHATSAPP"
                                ]
                              },
                              {
                                "type": "string",
                                "enum": [
                                  "LINKEDIN"
                                ]
                              },
                              {
                                "type": "string",
                                "enum": [
                                  "SLACK"
                                ]
                              },
                              {
                                "type": "string",
                                "enum": [
                                  "TWITTER"
                                ]
                              },
                              {
                                "type": "string",
                                "enum": [
                                  "MESSENGER"
                                ]
                              },
                              {
                                "type": "string",
                                "enum": [
                                  "INSTAGRAM"
                                ]
                              },
                              {
                                "type": "string",
                                "enum": [
                                  "TELEGRAM"
                                ]
                              }
                            ]
                          },
                          "provider_id": {
                            "type": "string"
                          },
                          "attendee_provider_id": {
                            "type": "string"
                          },
                          "name": {
                            "anyOf": [
                              {
                                "type": "string"
                              },
                              {
                                "nullable": true
                              }
                            ]
                          },
                          "type": {
                            "anyOf": [
                              {
                                "type": "number",
                                "enum": [
                                  0
                                ]
                              },
                              {
                                "type": "number",
                                "enum": [
                                  1
                                ]
                              },
                              {
                                "type": "number",
                                "enum": [
                                  2
                                ]
                              }
                            ]
                          },
                          "timestamp": {
                            "anyOf": [
                              {
                                "type": "string"
                              },
                              {
                                "nullable": true
                              }
                            ]
                          },
                          "unread_count": {
                            "type": "number"
                          },
                          "archived": {
                            "anyOf": [
                              {
                                "type": "number",
                                "enum": [
                                  0
                                ]
                              },
                              {
                                "type": "number",
                                "enum": [
                                  1
                                ]
                              }
                            ]
                          },
                          "muted_until": {
                            "anyOf": [
                              {
                                "type": "number",
                                "enum": [
                                  -1
                                ]
                              },
                              {
                                "type": "string"
                              },
                              {
                                "nullable": true
                              }
                            ]
                          },
                          "read_only": {
                            "anyOf": [
                              {
                                "type": "number",
                                "enum": [
                                  0
                                ]
                              },
                              {
                                "type": "number",
                                "enum": [
                                  1
                                ]
                              },
                              {
                                "type": "number",
                                "enum": [
                                  2
                                ]
                              }
                            ]
                          },
                          "disabledFeatures": {
                            "type": "array",
                            "items": {
                              "anyOf": [
                                {
                                  "type": "string",
                                  "enum": [
                                    "reactions"
                                  ]
                                },
                                {
                                  "type": "string",
                                  "enum": [
                                    "reply"
                                  ]
                                }
                              ]
                            }
                          },
                          "subject": {
                            "type": "string"
                          },
                          "organization_id": {
                            "description": "Linkedin specific ID for organization mailboxes.",
                            "type": "string"
                          },
                          "mailbox_id": {
                            "description": "Linkedin specific ID for organization mailboxes.",
                            "type": "string"
                          },
                          "content_type": {
                            "anyOf": [
                              {
                                "type": "string",
                                "enum": [
                                  "inmail"
                                ]
                              },
                              {
                                "type": "string",
                                "enum": [
                                  "sponsored"
                                ]
                              },
                              {
                                "type": "string",
                                "enum": [
                                  "linkedin_offer"
                                ]
                              }
                            ]
                          },
                          "folder": {
                            "type": "array",
                            "items": {
                              "anyOf": [
                                {
                                  "type": "string",
                                  "enum": [
                                    "INBOX"
                                  ]
                                },
                                {
                                  "type": "string",
                                  "enum": [
                                    "INBOX_LINKEDIN_CLASSIC"
                                  ]
                                },
                                {
                                  "type": "string",
                                  "enum": [
                                    "INBOX_LINKEDIN_RECRUITER"
                                  ]
                                },
                                {
                                  "type": "string",
                                  "enum": [
                                    "INBOX_LINKEDIN_SALES_NAVIGATOR"
                                  ]
                                },
                                {
                                  "type": "string",
                                  "enum": [
                                    "INBOX_LINKEDIN_ORGANIZATION"
                                  ]
                                }
                              ]
                            }
                          }
                        },
                        "required": [
                          "object",
                          "id",
                          "account_id",
                          "account_type",
                          "provider_id",
                          "name",
                          "type",
                          "timestamp",
                          "unread_count",
                          "archived",
                          "muted_until",
                          "read_only"
                        ]
                      }
                    },
                    "cursor": {
                      "anyOf": [
                        {},
                        {
                          "nullable": true
                        }
                      ]
                    }
                  },
                  "required": [
                    "object",
                    "items",
                    "cursor"
                  ]
                }
              }
            }
          },
          "401": {
            "description": "## Unauthorized\n\n### Missing credentials - Type: \"errors/missing_credentials\"\nSome credentials are necessary to perform the request.\n\n### Multiple sessions - Type: \"errors/multiple_sessions\"\nLinkedIn limits the use of multiple sessions on certain Recruiter accounts. This error restricts access to this route only, but causing a popup to appear in the user's browser, prompting them to choose a session, which can disconnect the current account. To avoid this error, use the cookie connection method.\n\n### Wrong account - Type: \"errors/wrong_account\"\nThe provided credentials do not match the correct account.\n\n### Invalid credentials - Type: \"errors/invalid_credentials\"\nThe provided credentials are invalid.\n\n### Invalid IMAP configuration - Type: \"errors/invalid_imap_configuration\"\nThe provided IMAP configuration is invalid.\n\n### Invalid SMTP configuration - Type: \"errors/invalid_smtp_configuration\"\nThe provided SMTP configuration is invalid.\n\n### Invalid checkpoint solution - Type: \"errors/invalid_checkpoint_solution\"\nThe checkpoint resolution did not pass successfully. Please retry.\n\n### Checkpoint error - Type: \"errors/checkpoint_error\"\nThe checkpoint does not appear to be resolvable. Please try again and contact support if the problem persists.\n\n### Expired credentials - Type: \"errors/expired_credentials\"\nInvalid credentials. Please check your username and password and try again.\n\n### Expired link - Type: \"errors/expired_link\"\nThis link has expired. Please return to the application and generate a new one.\n\n### Insufficient privileges - Type: \"errors/insufficient_privileges\"\nThis resource seems to be out of your scopes.\n\n### Disconnected account - Type: \"errors/disconnected_account\"\nThe account appears to be disconnected from the provider service.\n\n### Disconnected feature - Type: \"errors/disconnected_feature\"\nThe service you're trying to reach appears to be disconnected.\n\n### Captcha not supported - Type: \"errors/captcha_not_supported\"\nWe encounter captcha checkpoint, we currently working to manage it",
            "content": {
              "application/json": {
                "schema": {
                  "title": "UnauthorizedResponse",
                  "type": "object",
                  "properties": {
                    "title": {
                      "type": "string"
                    },
                    "detail": {
                      "type": "string"
                    },
                    "instance": {
                      "type": "string"
                    },
                    "type": {
                      "type": "string",
                      "enum": [
                        "errors/missing_credentials",
                        "errors/multiple_sessions",
                        "errors/invalid_checkpoint_solution",
                        "errors/checkpoint_error",
                        "errors/invalid_credentials",
                        "errors/expired_credentials",
                        "errors/insufficient_privileges",
                        "errors/disconnected_account",
                        "errors/disconnected_feature",
                        "errors/invalid_credentials_but_valid_account_imap",
                        "errors/expired_link",
                        "errors/wrong_account",
                        "errors/captcha_not_supported"
                      ]
                    },
                    "status": {
                      "type": "number",
                      "enum": [
                        401
                      ]
                    },
                    "connectionParams": {
                      "type": "object",
                      "properties": {
                        "imap_host": {
                          "type": "string"
                        },
                        "imap_encryption": {
                          "type": "string"
                        },
                        "imap_port": {
                          "type": "number"
                        },
                        "imap_user": {
                          "type": "string"
                        },
                        "smtp_host": {
                          "type": "string"
                        },
                        "smtp_port": {
                          "type": "number"
                        },
                        "smtp_user": {
                          "type": "string"
                        }
                      },
                      "required": [
                        "imap_host",
                        "imap_port",
                        "imap_user",
                        "smtp_host",
                        "smtp_port",
                        "smtp_user"
                      ]
                    }
                  },
                  "required": [
                    "title",
                    "type",
                    "status"
                  ]
                }
              }
            }
          },
          "403": {
            "description": "## Forbidden\n\n### Insufficient permissions - Type: \"errors/insufficient_permissions\"\nValid authentication but insufficient permissions to perform the request.\n\n### Account restricted - Type: \"errors/account_restricted\"\nAccess to this account has been restricted by the provider.\n\n### Account mismatch - Type: \"errors/account_mismatch\"\nThis action cannot be done with your account.\n\n### Unknown authentication context - Type: \"errors/unknown_authentication_context\"\nAn additional step seems necessary to complete login. Please connect to provider with your browser to find out more, then retry authentication.\n\n### Session mismatch - Type: \"errors/session_mismatch\"\nToken User id does not match client session id.\n\n### Feature not subscribed - Type: \"errors/feature_not_subscribed\"\nThe requested feature has either not been subscribed or not been authenticated properly.\n\n### Subscription required - Type: \"errors/subscription_required\"\nThe action you're trying to achieve requires a subscription to provider's services.\n\n### Resource access restricted - Type: \"errors/resource_access_restricted\"\nYou don't have access to this resource.\n\n### Action required - Type: \"errors/action_required\"\nAn additional step seems necessary. Complete authentication on the provider's native application and try again.",
            "content": {
              "application/json": {
                "schema": {
                  "title": "ForbiddenResponse",
                  "type": "object",
                  "properties": {
                    "title": {
                      "type": "string"
                    },
                    "detail": {
                      "type": "string"
                    },
                    "instance": {
                      "type": "string"
                    },
                    "type": {
                      "type": "string",
                      "enum": [
                        "errors/account_restricted",
                        "errors/account_mismatch",
                        "errors/insufficient_permissions",
                        "errors/session_mismatch",
                        "errors/feature_not_subscribed",
                        "errors/subscription_required",
                        "errors/unknown_authentication_context",
                        "errors/action_required",
                        "errors/resource_access_restricted"
                      ]
                    },
                    "status": {
                      "type": "number",
                      "enum": [
                        403
                      ]
                    }
                  },
                  "required": [
                    "title",
                    "type",
                    "status"
                  ]
                }
              }
            }
          },
          "500": {
            "description": "## Internal Server Error\n\n### Unexpected error - Type: \"errors/unexpected_error\"\nSomething went wrong. {{moreDetails}}\n\n### Provider error - Type: \"errors/provider_error\"\nThe provider is experiencing operational problems. Please try again later.\n\n### Authentication intent error - Type: \"errors/authentication_intent_error\"\nThe current authentication intent was killed after failure. Please start the process again from the beginning.",
            "content": {
              "application/json": {
                "schema": {
                  "title": "InternalServerErrorResponse",
                  "type": "object",
                  "properties": {
                    "title": {
                      "type": "string"
                    },
                    "detail": {
                      "type": "string"
                    },
                    "instance": {
                      "type": "string"
                    },
                    "type": {
                      "type": "string",
                      "enum": [
                        "errors/unexpected_error",
                        "errors/provider_error",
                        "errors/authentication_intent_error"
                      ]
                    },
                    "status": {
                      "type": "number",
                      "enum": [
                        500
                      ]
                    }
                  },
                  "required": [
                    "title",
                    "type",
                    "status"
                  ]
                }
              }
            }
          },
          "503": {
            "description": "## Service Unavailable\n\n### No client session - Type: \"errors/no_client_session\"\nNo client session is currently running.\n\n### No channel - Type: \"errors/no_channel\"\nNo channel to client session.\n\n### Handler missing - Type: \"errors/no_handler\"\nHandler missing for that request.\n\n### Network down - Type: \"errors/network_down\"\nNetwork is down on server side. Please wait a moment and retry.\n\n### Service unavailable - Type: \"errors/service_unavailable\"\nPlease try again later.",
            "content": {
              "application/json": {
                "schema": {
                  "title": "ServiceUnavailableResponse",
                  "type": "object",
                  "properties": {
                    "title": {
                      "type": "string"
                    },
                    "detail": {
                      "type": "string"
                    },
                    "instance": {
                      "type": "string"
                    },
                    "type": {
                      "type": "string",
                      "enum": [
                        "errors/no_client_session",
                        "errors/no_channel",
                        "errors/no_handler",
                        "errors/network_down",
                        "errors/service_unavailable"
                      ]
                    },
                    "status": {
                      "type": "number",
                      "enum": [
                        503
                      ]
                    }
                  },
                  "required": [
                    "title",
                    "type",
                    "status"
                  ]
                }
              }
            }
          },
          "504": {
            "description": "## Gateway Timeout\n\n### Request timed out - Type: \"errors/request_timeout\"\nRequest Timeout. Please try again, and if the issue persists, contact support.",
            "content": {
              "application/json": {
                "schema": {
                  "title": "GatewayTimeoutResponse",
                  "type": "object",
                  "properties": {
                    "title": {
                      "type": "string"
                    },
                    "detail": {
                      "type": "string"
                    },
                    "instance": {
                      "type": "string"
                    },
                    "type": {
                      "type": "string",
                      "enum": [
                        "errors/request_timeout"
                      ]
                    },
                    "status": {
                      "type": "number",
                      "enum": [
                        504
                      ]
                    }
                  },
                  "required": [
                    "title",
                    "type",
                    "status"
                  ]
                }
              }
            }
          }
        },
        "tags": [
          "Messaging"
        ],
        "security": [
          {
            "Access-Token": []
          }
        ]
      }
    }
  },
  "info": {
    "title": "Unipile API Reference",
    "description": "Unipile Communication is an **HTTP API**. It has predictable resource-oriented `URLs`, accepts **form-encoded** or **JSON-encoded** request bodies, returns **JSON-encoded responses**, and uses standard HTTP response codes, authentication, and verbs.",
    "version": "1.0",
    "contact": {}
  },
  "tags": [
    {
      "name": "Messaging",
      "description": "Messaging management"
    }
  ],
  "servers": [
    {
      "url": "https://{subdomain}.unipile.com:{port}",
      "description": "live server",
      "variables": {
        "subdomain": {
          "default": "api1"
        },
        "port": {
          "default": "13111"
        }
      }
    },
    {
      "url": "http://127.0.0.1:3114"
    }
  ],
  "components": {
    "securitySchemes": {
      "Access-Token": {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-KEY"
      }
    }
  },
  "x-readme": {
    "explorer-enabled": true,
    "proxy-enabled": true
  },
  "_id": "654cacb148798d000bf66ba2"
}
```