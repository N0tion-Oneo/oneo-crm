Create a job posting

# OpenAPI definition
```json
{
  "openapi": "3.0.0",
  "paths": {
    "/api/v1/linkedin/jobs": {
      "post": {
        "operationId": "LinkedinController_createJobPosting",
        "summary": "Create a job posting",
        "description": "Create a new job offer draft.",
        "parameters": [],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "account_id": {
                    "title": "AccountIdParam",
                    "description": "An Unipile account id.",
                    "minLength": 1,
                    "type": "string"
                  },
                  "job_title": {
                    "anyOf": [
                      {
                        "title": "ID based job title",
                        "type": "object",
                        "properties": {
                          "id": {
                            "description": "The ID of the parameter. Use type JOB_TITLE on the List search parameters route to find out the right ID.",
                            "type": "string",
                            "pattern": "^\\d+$"
                          }
                        },
                        "required": [
                          "id"
                        ]
                      },
                      {
                        "title": "Plain text based job title",
                        "type": "object",
                        "properties": {
                          "text": {
                            "type": "string"
                          }
                        },
                        "required": [
                          "text"
                        ]
                      }
                    ]
                  },
                  "company": {
                    "anyOf": [
                      {
                        "title": "ID based company",
                        "type": "object",
                        "properties": {
                          "id": {
                            "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.",
                            "type": "string",
                            "pattern": "^\\d+$"
                          }
                        },
                        "required": [
                          "id"
                        ]
                      },
                      {
                        "title": "Plain text based company",
                        "type": "object",
                        "properties": {
                          "text": {
                            "type": "string"
                          }
                        },
                        "required": [
                          "text"
                        ]
                      }
                    ]
                  },
                  "workplace": {
                    "type": "string",
                    "enum": [
                      "ON_SITE",
                      "HYBRID",
                      "REMOTE"
                    ]
                  },
                  "location": {
                    "description": "The ID of the parameter. Use type LOCATION on the List search parameters route to find out the right ID.",
                    "type": "string",
                    "pattern": "^\\d+$"
                  },
                  "employment_status": {
                    "type": "string",
                    "enum": [
                      "FULL_TIME",
                      "PART_TIME",
                      "CONTRACT",
                      "TEMPORARY",
                      "OTHER",
                      "VOLUNTEER",
                      "INTERNSHIP"
                    ]
                  },
                  "description": {
                    "description": "You can use HTML tags to structure your description.",
                    "type": "string"
                  },
                  "auto_rejection_template": {
                    "description": "You can define a rejection message template to be automatically sent to applicants that don't pass screening questions.",
                    "type": "string"
                  },
                  "screening_questions": {
                    "type": "array",
                    "items": {
                      "anyOf": [
                        {
                          "type": "object",
                          "properties": {
                            "question": {
                              "type": "string"
                            },
                            "position": {
                              "description": "The position of the question in the list. Overrides the index of the question in the array.",
                              "type": "number"
                            },
                            "must_match": {
                              "description": "Whether an answer that doesn't perfectly match the expected is disqualifying or not.",
                              "type": "boolean"
                            },
                            "answer_type": {
                              "type": "string",
                              "enum": [
                                "numeric"
                              ]
                            },
                            "min_expectation": {
                              "type": "number"
                            },
                            "max_expectation": {
                              "type": "number"
                            }
                          },
                          "required": [
                            "question",
                            "answer_type"
                          ]
                        },
                        {
                          "type": "object",
                          "properties": {
                            "question": {
                              "type": "string"
                            },
                            "position": {
                              "description": "The position of the question in the list. Overrides the index of the question in the array.",
                              "type": "number"
                            },
                            "must_match": {
                              "description": "Whether an answer that doesn't perfectly match the expected is disqualifying or not.",
                              "type": "boolean"
                            },
                            "answer_type": {
                              "type": "string",
                              "enum": [
                                "multiple_choices"
                              ]
                            },
                            "choices": {
                              "type": "array",
                              "items": {
                                "type": "string"
                              }
                            },
                            "expected_choices": {
                              "type": "array",
                              "items": {
                                "type": "string"
                              }
                            }
                          },
                          "required": [
                            "question",
                            "answer_type",
                            "choices",
                            "expected_choices"
                          ]
                        }
                      ]
                    }
                  },
                  "recruiter": {
                    "type": "object",
                    "properties": {
                      "project": {
                        "anyOf": [
                          {
                            "title": "The ID of an existing project",
                            "type": "object",
                            "properties": {
                              "id": {
                                "type": "string"
                              }
                            },
                            "required": [
                              "id"
                            ]
                          },
                          {
                            "title": "The name of a new project",
                            "type": "object",
                            "properties": {
                              "name": {
                                "type": "string"
                              }
                            },
                            "required": [
                              "name"
                            ]
                          }
                        ]
                      },
                      "functions": {
                        "description": "The ID of the parameter. Use type JOB_FUNCTION on the List search parameters route to find out the right ID.\nLinkedin native field : Job function.",
                        "minItems": 1,
                        "maxItems": 3,
                        "type": "array",
                        "items": {
                          "type": "string",
                          "pattern": "^[a-z]+$"
                        }
                      },
                      "industries": {
                        "description": "The ID of the parameter. Use type INDUSTRY on the List search parameters route to find out the right ID.\nLinkedin native field : Company industry.",
                        "minItems": 1,
                        "maxItems": 3,
                        "type": "array",
                        "items": {
                          "type": "string",
                          "pattern": "^\\d+$"
                        }
                      },
                      "seniority": {
                        "type": "string",
                        "enum": [
                          "INTERNSHIP",
                          "ENTRY_LEVEL",
                          "ASSOCIATE",
                          "MID_SENIOR_LEVEL",
                          "DIRECTOR",
                          "EXECUTIVE",
                          "NOT_APPLICABLE"
                        ]
                      },
                      "apply_method": {
                        "anyOf": [
                          {
                            "title": "Apply within Linkedin",
                            "type": "object",
                            "properties": {
                              "type": {
                                "type": "string",
                                "enum": [
                                  "linkedin"
                                ]
                              },
                              "notification_email": {
                                "type": "string"
                              },
                              "resume_required": {
                                "type": "boolean"
                              }
                            },
                            "required": [
                              "type",
                              "notification_email",
                              "resume_required"
                            ]
                          },
                          {
                            "title": "Apply through an external website",
                            "type": "object",
                            "properties": {
                              "type": {
                                "type": "string",
                                "enum": [
                                  "external"
                                ]
                              },
                              "url": {
                                "type": "string"
                              }
                            },
                            "required": [
                              "type",
                              "url"
                            ]
                          }
                        ]
                      }
                    },
                    "required": [
                      "project",
                      "functions",
                      "industries",
                      "seniority",
                      "apply_method"
                    ]
                  }
                },
                "required": [
                  "account_id",
                  "job_title",
                  "company",
                  "workplace",
                  "location",
                  "description"
                ]
              }
            }
          }
        },
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
                        "LinkedinJobPostingDraftCreated"
                      ]
                    },
                    "job_id": {
                      "type": "string"
                    },
                    "publish_options": {
                      "type": "object",
                      "properties": {
                        "free": {
                          "type": "object",
                          "properties": {
                            "eligible": {
                              "description": "Whether the user is authorized to publish this job offer for free.",
                              "type": "boolean"
                            },
                            "ineligible_reason": {
                              "anyOf": [
                                {
                                  "type": "string"
                                },
                                {
                                  "nullable": true
                                }
                              ]
                            },
                            "estimated_monthly_applicants": {
                              "type": "number"
                            }
                          },
                          "required": [
                            "eligible",
                            "ineligible_reason",
                            "estimated_monthly_applicants"
                          ]
                        },
                        "promoted": {
                          "type": "object",
                          "properties": {
                            "estimated_monthly_applicants": {
                              "type": "number"
                            },
                            "currency": {
                              "type": "string"
                            },
                            "daily_budget": {
                              "type": "object",
                              "properties": {
                                "min": {
                                  "type": "number"
                                },
                                "max": {
                                  "type": "number"
                                },
                                "recommended": {
                                  "type": "number"
                                }
                              },
                              "required": [
                                "min",
                                "max",
                                "recommended"
                              ]
                            },
                            "monthly_budget": {
                              "type": "object",
                              "properties": {
                                "min": {
                                  "type": "number"
                                },
                                "max": {
                                  "type": "number"
                                },
                                "recommended": {
                                  "type": "number"
                                }
                              },
                              "required": [
                                "min",
                                "max",
                                "recommended"
                              ]
                            }
                          },
                          "required": [
                            "estimated_monthly_applicants",
                            "currency",
                            "daily_budget",
                            "monthly_budget"
                          ]
                        }
                      },
                      "required": [
                        "free",
                        "promoted"
                      ]
                    }
                  },
                  "required": [
                    "object",
                    "job_id",
                    "publish_options"
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
          "404": {
            "description": "\n        ## Not Found\n        ### Resource not found.\n        The requested resource were not found.\nAccount not found",
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
          "422": {
            "description": "\n          ## Unprocessable Entity\n          ### Invalid account\n          Provided account is not designed for this feature.\nundefined",
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
          "LinkedIn Specific"
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
      "name": "LinkedIn Specific",
      "description": "Linkedin specific use cases"
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