Start a new chat

# OpenAPI definition
```json
{
  "openapi": "3.0.0",
  "paths": {
    "/api/v1/chats": {
      "post": {
        "operationId": "ChatsController_startNewChat",
        "summary": "Start a new chat",
        "description": "Start a new conversation with one or more attendee. ⚠️ Interactive documentation does not work for Linkedin specific parameters (child parameters not correctly applied in snippet), the correct format is linkedin[inmail] = true, linkedin[api]...",
        "parameters": [],
        "requestBody": {
          "required": true,
          "content": {
            "multipart/form-data": {
              "schema": {
                "type": "object",
                "properties": {
                  "account_id": {
                    "title": "AccountIdParam",
                    "description": "An Unipile account id.",
                    "minLength": 1,
                    "type": "string"
                  },
                  "text": {
                    "description": "The message that will start the new conversation.\nWith LinkedIn recruiter, a range of HTML tags can be used directly in the body of the message to enhance the presentation. The supported tags are &lt;strong&gt; for bold text, &lt;em&gt; for italic text, &lt;a href=\"www.my-link.com\"&gt; for external links, &lt;ul&gt; for unordered lists, &lt;ol&gt; for ordered lists and &lt;li&gt; for list items. Tags can be nested into each other if necessary.",
                    "type": "string"
                  },
                  "attachments": {
                    "type": "array",
                    "items": {
                      "format": "binary",
                      "type": "string"
                    }
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
                  "attendees_ids": {
                    "description": "One or more attendee provider ID. (For instagram, please use the 'provider_messaging_id'.)",
                    "minItems": 1,
                    "type": "array",
                    "items": {
                      "type": "string"
                    }
                  },
                  "subject": {
                    "description": "An optional field to set the subject of the conversation.",
                    "type": "string"
                  },
                  "linkedin": {
                    "description": "Extra fields for Linkedin products",
                    "anyOf": [
                      {
                        "description": "Standard Linkedin fields",
                        "title": "Classic options",
                        "type": "object",
                        "properties": {
                          "api": {
                            "description": "The Linkedin API that should be used to start chatting (relative feature must be subscribed). Default is classic.",
                            "type": "string",
                            "enum": [
                              "classic"
                            ]
                          },
                          "topic": {
                            "description": "Mandatory to start a conversation with a company.",
                            "type": "string",
                            "enum": [
                              "service_request",
                              "request_demo",
                              "support",
                              "careers",
                              "other"
                            ]
                          },
                          "applicant_id": {
                            "description": "Mandatory to start a conversation with a job applicant. Use the <strong>List all job postings</strong> route first to retrieve the job posting, and then the <strong>List all applicants to a job posting</strong> route to get the applicant details.",
                            "type": "string"
                          },
                          "invitation_id": {
                            "description": "Mandatory to start a conversation with a user from whom you received an invitation that you have neither accepted nor declined yet.",
                            "type": "string"
                          },
                          "inmail": {
                            "description": "If set to true, start the new conversation with an inMail.",
                            "type": "boolean"
                          }
                        }
                      },
                      {
                        "description": "Recruiter Linkedin fields",
                        "title": "Recruiter options",
                        "type": "object",
                        "properties": {
                          "api": {
                            "description": "The Linkedin API that should be used to start chatting (relative feature must be subscribed).",
                            "type": "string",
                            "enum": [
                              "recruiter"
                            ]
                          },
                          "signature": {
                            "description": "The signature of the sender",
                            "type": "string"
                          },
                          "hiring_project_id": {
                            "description": "The ID of the project the chat should be started in",
                            "type": "string"
                          },
                          "job_posting_id": {
                            "description": "The ID of the related job posting in case of an initial contact with a candidate",
                            "type": "string"
                          },
                          "email_address": {
                            "description": "The email address of the recipient in case the chat should be started with email instead of inMail",
                            "type": "string"
                          },
                          "visibility": {
                            "description": "Define the level of visibility of the conversation within your organization. Default value will be PRIVATE.",
                            "type": "string",
                            "enum": [
                              "PUBLIC",
                              "PRIVATE",
                              "PROJECT"
                            ]
                          },
                          "follow_up": {
                            "description": "Allows to schedule a follow-up message. Available for Recruiter PRO account owners only.",
                            "title": "Follow-up config",
                            "type": "object",
                            "properties": {
                              "subject": {
                                "description": "The subject for the follow-up message.",
                                "type": "string"
                              },
                              "text": {
                                "description": "The textual content for the follow-up message.",
                                "type": "string"
                              },
                              "attachments": {
                                "type": "array",
                                "items": {
                                  "format": "binary",
                                  "type": "string"
                                }
                              },
                              "scheduled_time": {
                                "anyOf": [
                                  {
                                    "title": "Days based",
                                    "type": "object",
                                    "properties": {
                                      "days": {
                                        "description": "The number of days from here to send the follow-up message.",
                                        "minimum": 3,
                                        "maximum": 28,
                                        "type": "number"
                                      },
                                      "timezone": {
                                        "description": "The timezone from which the follow-up message is scheduled. Example: 'Europe/Paris', 'America/Phoenix'...",
                                        "type": "string"
                                      }
                                    },
                                    "required": [
                                      "days",
                                      "timezone"
                                    ]
                                  },
                                  {
                                    "title": "Weeks based",
                                    "type": "object",
                                    "properties": {
                                      "weeks": {
                                        "description": "The number of weeks from here to send the follow-up message.",
                                        "minimum": 1,
                                        "maximum": 4,
                                        "type": "number"
                                      },
                                      "timezone": {
                                        "description": "The timezone from which the follow-up message is scheduled. Example: 'Europe/Paris', 'America/Phoenix'...",
                                        "type": "string"
                                      }
                                    },
                                    "required": [
                                      "weeks",
                                      "timezone"
                                    ]
                                  }
                                ]
                              }
                            },
                            "required": [
                              "subject",
                              "text",
                              "scheduled_time"
                            ]
                          }
                        },
                        "required": [
                          "api"
                        ]
                      },
                      {
                        "description": "Sales Navigator Linkedin fields",
                        "title": "Sales Navigator options",
                        "type": "object",
                        "properties": {
                          "api": {
                            "description": "The Linkedin API that should be used to start chatting (relative features must be subscribed).",
                            "type": "string",
                            "enum": [
                              "sales_navigator"
                            ]
                          }
                        },
                        "required": [
                          "api"
                        ]
                      }
                    ]
                  }
                },
                "required": [
                  "account_id",
                  "attendees_ids"
                ]
              }
            }
          }
        },
        "responses": {
          "201": {
            "description": "Created. New chat created and message sent successfully.",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "object": {
                      "type": "string",
                      "enum": [
                        "ChatStarted"
                      ]
                    },
                    "chat_id": {
                      "description": "The Unipile ID of the newly started chat.",
                      "anyOf": [
                        {
                          "type": "string"
                        },
                        {
                          "nullable": true
                        }
                      ]
                    },
                    "message_id": {
                      "description": "The Unipile ID of the message the chat started with.",
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
                    "chat_id",
                    "message_id"
                  ]
                }
              }
            }
          },
          "400": {
            "description": "\n          ## Bad Request\n          ### Too many characters\n          The provided content exceeds the character limit.\nundefined",
            "content": {
              "application/json": {
                "schema": {
                  "title": "BadRequestResponse",
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
                        "errors/invalid_parameters",
                        "errors/malformed_request",
                        "errors/content_too_large",
                        "errors/invalid_url",
                        "errors/too_many_characters",
                        "errors/unescaped_characters",
                        "errors/missing_parameters"
                      ]
                    },
                    "status": {
                      "type": "number",
                      "enum": [
                        400
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
            "description": "\n        ## Not Found\n        ### Resource not found.\n        The requested resource were not found.\nundefined",
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
            "description": "\n          ## Unprocessable Entity\n          ### Recipient cannot be reached\n          The recipient appears not to be first degree connection.\nundefined",
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
          "501": {
            "description": "\n        ## Not Implemented\n        ### Missing feature\n        Requested feature is planned but has not been implemented yet.\nundefined",
            "content": {
              "application/json": {
                "schema": {
                  "title": "NotImplementedErrorResponse",
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
                        "errors/feature_not_implemented"
                      ]
                    },
                    "status": {
                      "type": "number",
                      "enum": [
                        501
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