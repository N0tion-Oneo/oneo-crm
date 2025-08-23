Send a message in a chat

# OpenAPI definition
```json
{
  "openapi": "3.0.0",
  "paths": {
    "/api/v1/chats/{chat_id}/messages": {
      "post": {
        "operationId": "ChatsController_sendMessageInChat",
        "x-readme": {
          "code-samples": [
            {
              "language": "node",
              "code": "import { UnipileClient } from \"unipile-node-sdk\"\n\n// SDK setup\nconst BASE_URL = \"your base url\"\nconst ACCESS_TOKEN = \"your access token\"\n// Inputs\nconst chat_id = \"chat id\"\nconst text = \"text\"\n\ntry {\n\tconst client = new UnipileClient(BASE_URL, ACCESS_TOKEN)\n\n\tconst response = await client.messaging.sendMessage({\n\t\tchat_id,\n\t\ttext,\n\t})\n} catch (error) {\n\tconsole.log(error)\n}\n",
              "name": "unipile-node-sdk",
              "install": "npm install unipile-node-sdk"
            }
          ]
        },
        "summary": "Send a message in a chat",
        "description": "Send a message to the given chat with the possibility to link some attachments.",
        "parameters": [
          {
            "name": "chat_id",
            "required": true,
            "in": "path",
            "description": "The id of the chat where to send the message.",
            "schema": {
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "multipart/form-data": {
              "schema": {
                "type": "object",
                "properties": {
                  "text": {
                    "type": "string"
                  },
                  "account_id": {
                    "description": "An account_id can be specified to prevent the user from sending messages in chats not belonging to the account.",
                    "type": "string"
                  },
                  "thread_id": {
                    "description": "Optional and for Slack’s messaging only. The id of the thread to send the message in.",
                    "type": "string"
                  },
                  "quote_id": {
                    "description": "The id of a message to quote. The id of the message to quote / reply to.",
                    "type": "string"
                  },
                  "voice_message": {
                    "format": "binary",
                    "description": "For Linkedin messaging only.",
                    "type": "string"
                  },
                  "video_message": {
                    "format": "binary",
                    "description": "For Linkedin messaging only.",
                    "type": "string"
                  },
                  "attachments": {
                    "type": "array",
                    "items": {
                      "format": "binary",
                      "type": "string"
                    }
                  }
                }
              }
            }
          }
        },
        "responses": {
          "201": {
            "description": "Created. Message sent successfully.",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "object": {
                      "type": "string",
                      "enum": [
                        "MessageSent"
                      ]
                    },
                    "message_id": {
                      "description": "The Unipile ID of the newly sent message.",
                      "anyOf": [
                        {
                          "type": "string"
                        },
                        {
                          "nullable": true
                        }
                      ]
                    }
                  },
                  "required": [
                    "object",
                    "message_id"
                  ]
                }
              }
            }
          },
          "401": {
            "description": "\n          ## Unauthorized\n          ### Disconnected account\n          The account appears to be disconnected from the provider service.\nundefined",
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
            "description": "\n          ## Forbidden\n          ### Feature not subscribed\n          The requested feature has either not been subscribed or not been authenticated properly.\nundefined",
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
          "404": {
            "description": "\n        ## Not Found\n        ### Resource not found.\n        The requested resource were not found.\nAccount, chat or thread not found",
            "content": {
              "application/json": {
                "schema": {
                  "title": "NotFoundResponse",
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
                        "errors/resource_not_found",
                        "errors/invalid_resource_identifier"
                      ]
                    },
                    "status": {
                      "type": "number",
                      "enum": [
                        404
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
          "415": {
            "description": "\n          ## Unsupported Media Type\n          ### Unsupported media\n          The media has been rejected by the provider.\nundefined",
            "content": {
              "application/json": {
                "schema": {
                  "title": "UnsupportedMediaResponseSchema",
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
                        "errors/unsupported_media_type"
                      ]
                    },
                    "status": {
                      "type": "number",
                      "enum": [
                        415
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
          "422": {
            "description": "\n          ## Unprocessable Entity\n          ### Message couldn't pass validation\n          Provider cannot execute request because of an invalid message.\nundefined",
            "content": {
              "application/json": {
                "schema": {
                  "title": "UnprocessableEntityResponseSchema",
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
                        "errors/invalid_account",
                        "errors/invalid_recipient",
                        "errors/no_connection_with_recipient",
                        "errors/blocked_recipient",
                        "errors/user_unreachable",
                        "errors/unprocessable_entity",
                        "errors/action_already_performed",
                        "errors/invalid_message",
                        "errors/invalid_post",
                        "errors/not_allowed_inmail",
                        "errors/insufficient_credits",
                        "errors/cannot_resend_yet",
                        "errors/cannot_resend_within_24hrs",
                        "errors/limit_exceeded",
                        "errors/already_invited_recently",
                        "errors/cannot_invite_attendee",
                        "errors/parent_mail_not_found",
                        "errors/invalid_reply_subject",
                        "errors/invalid_headers",
                        "errors/send_as_denied",
                        "errors/invalid_folder",
                        "errors/invalid_thread",
                        "errors/limit_too_high",
                        "errors/unauthorized",
                        "errors/sender_rejected",
                        "errors/recipient_rejected",
                        "errors/ip_rejected_by_server",
                        "errors/provider_unreachable",
                        "errors/account_configuration_error",
                        "errors/cant_send_message",
                        "errors/realtime_client_not_initialized"
                      ]
                    },
                    "status": {
                      "type": "number",
                      "enum": [
                        422
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
          "429": {
            "description": "\n        ## Too Many Requests\n        ### Too many requests\n        The provider cannot accept any more requests at the moment. Please try again later.\nundefined",
            "content": {
              "application/json": {
                "schema": {
                  "title": "TooManyRequestsResponse",
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
                        "errors/too_many_requests"
                      ]
                    },
                    "status": {
                      "type": "number",
                      "enum": [
                        429
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
            "description": "\n          ## Service Unavailable\n          ### Network down\n          Network is down on server side. Please wait a moment and retry.\nundefined",
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