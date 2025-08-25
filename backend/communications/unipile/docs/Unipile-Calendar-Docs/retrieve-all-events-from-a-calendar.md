Retrieve all events from a calendar

# OpenAPI definition
```json
{
  "openapi": "3.0.0",
  "paths": {
    "/api/v1/calendars/{calendar_id}/events": {
      "get": {
        "operationId": "CalendarsController_listCalendarEventsByCalendar",
        "summary": "Retrieve all events from a calendar",
        "description": "Returns a list of calendar events related to the given calendar.",
        "parameters": [
          {
            "name": "expand_recurring",
            "required": false,
            "in": "query",
            "description": "Filter events by type (single or occurence).",
            "schema": {
              "type": "boolean"
            }
          },
          {
            "name": "event_type",
            "required": false,
            "in": "query",
            "description": "Filter events by event type. This parameter accepts a comma-delimited list of event type.",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "attendees",
            "required": false,
            "in": "query",
            "description": "Filter events with attendees contained in this list. This parameter accepts a comma-delimited list of email addresses.",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "updated_after",
            "required": false,
            "in": "query",
            "description": "Filter events updated after this date.",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "updated_before",
            "required": false,
            "in": "query",
            "description": "Filter events updated before this date.",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "busy",
            "required": false,
            "in": "query",
            "description": "Filter for events with the status `busy`",
            "schema": {
              "type": "boolean"
            }
          },
          {
            "name": "end",
            "required": false,
            "in": "query",
            "description": "Filter events ending before this date.",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "start",
            "required": false,
            "in": "query",
            "description": "Filter events starting after this date.",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "location",
            "required": false,
            "in": "query",
            "description": "Filter for events matching the specified location.",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "ical_uid",
            "required": false,
            "in": "query",
            "description": "Filter for events matching the specified iCal UID.",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "description",
            "required": false,
            "in": "query",
            "description": "Filter for events matching the specified description.",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "title",
            "required": false,
            "in": "query",
            "description": "Filter for events matching the specified title.",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "is_cancelled",
            "required": false,
            "in": "query",
            "description": "Indicates if you want to retrieve the cancelled events.",
            "schema": {
              "type": "boolean"
            }
          },
          {
            "name": "cursor",
            "required": false,
            "in": "query",
            "description": "A cursor used for pagination. If supported by the provider, use `next_cursor` given by the previous page of the list, else use `offset`.",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "offset",
            "required": false,
            "in": "query",
            "description": "An offset used for pagination, if supported by the provider, else use `cursor`.",
            "schema": {
              "type": "number"
            }
          },
          {
            "name": "limit",
            "required": false,
            "in": "query",
            "description": "The limit of items to be returned.",
            "schema": {
              "type": "number"
            }
          },
          {
            "name": "account_id",
            "required": true,
            "in": "query",
            "description": "The id of the account to use.",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "calendar_id",
            "required": true,
            "in": "path",
            "description": "The id of the calendar related to events",
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "OK",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "data": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "object": {
                            "type": "string",
                            "enum": [
                              "CalendarEvent"
                            ]
                          },
                          "id": {
                            "description": "The ID of the calendar event.",
                            "type": "string"
                          },
                          "master_event_id": {
                            "description": "If event instance, the ID of the master event.",
                            "type": "string"
                          },
                          "calendar_id": {
                            "description": "The ID of the calendar the event belongs to.",
                            "type": "string"
                          },
                          "created_at": {
                            "description": "The date the event was created. Uses ISO 8601 UTC datetime (YYYY-MM-DDTHH:MM:SS.sssZ).",
                            "type": "string"
                          },
                          "updated_at": {
                            "description": "The date the event was last updated. Uses ISO 8601 UTC datetime (YYYY-MM-DDTHH:MM:SS.sssZ).",
                            "type": "string"
                          },
                          "title": {
                            "description": "The title of the event.",
                            "type": "string"
                          },
                          "body": {
                            "description": "The body of the event.",
                            "type": "string"
                          },
                          "location": {
                            "description": "The location of the event.",
                            "type": "string"
                          },
                          "is_cancelled": {
                            "description": "Is the event cancelled.",
                            "type": "boolean"
                          },
                          "is_all_day": {
                            "description": "Is the event all day.",
                            "type": "boolean"
                          },
                          "is_attendees_list_hidden": {
                            "description": "Is the attendees list hidden for attendees.",
                            "type": "boolean"
                          },
                          "attendees": {
                            "description": "The attendees of the event.",
                            "type": "array",
                            "items": {
                              "description": "An attendee of a calendar event.",
                              "type": "object",
                              "properties": {
                                "email": {
                                  "description": "Email address of the attendee.",
                                  "type": "string"
                                },
                                "display_name": {
                                  "description": "Display name of the attendee.",
                                  "type": "string"
                                },
                                "comment": {
                                  "description": "The response comment of the attendee.",
                                  "type": "string"
                                },
                                "is_organizer": {
                                  "description": "Is the attendee the organizer of the event.",
                                  "type": "boolean"
                                },
                                "is_optional": {
                                  "description": "Is the attendee optional (based on type).",
                                  "type": "boolean"
                                },
                                "is_resource": {
                                  "description": "Is the attendee a resource (based on type).",
                                  "type": "boolean"
                                },
                                "type": {
                                  "description": "Type of the attendee.",
                                  "anyOf": [
                                    {
                                      "type": "string",
                                      "enum": [
                                        "required"
                                      ]
                                    },
                                    {
                                      "type": "string",
                                      "enum": [
                                        "optional"
                                      ]
                                    },
                                    {
                                      "type": "string",
                                      "enum": [
                                        "resource"
                                      ]
                                    }
                                  ]
                                },
                                "response_status": {
                                  "description": "The response status of the attendee. `yes` if the invitation is accepted. `no` if the invitation is declined. `maybe` if the attendee is not sure. `noreply` if the invitation is pending.",
                                  "anyOf": [
                                    {
                                      "type": "string",
                                      "enum": [
                                        "yes"
                                      ]
                                    },
                                    {
                                      "type": "string",
                                      "enum": [
                                        "no"
                                      ]
                                    },
                                    {
                                      "type": "string",
                                      "enum": [
                                        "maybe"
                                      ]
                                    },
                                    {
                                      "type": "string",
                                      "enum": [
                                        "noreply"
                                      ]
                                    }
                                  ]
                                }
                              },
                              "required": [
                                "email",
                                "is_organizer",
                                "is_optional",
                                "is_resource",
                                "type",
                                "response_status"
                              ]
                            }
                          },
                          "start": {
                            "description": "The start date and time of the event.",
                            "anyOf": [
                              {
                                "type": "object",
                                "properties": {
                                  "date_time": {
                                    "description": "The date and time. Uses ISO 8601 UTC datetime (YYYY-MM-DDTHH:MM:SS.sssZ).",
                                    "type": "string"
                                  },
                                  "time_zone": {
                                    "description": "The time zone of the date time.",
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "date_time",
                                  "time_zone"
                                ]
                              },
                              {
                                "type": "object",
                                "properties": {
                                  "date": {
                                    "description": "The date. Uses ISO 8601 date format (YYYY-MM-DD).",
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "date"
                                ]
                              }
                            ]
                          },
                          "end": {
                            "description": "The end date and time of the event.",
                            "anyOf": [
                              {
                                "type": "object",
                                "properties": {
                                  "date_time": {
                                    "description": "The date and time. Uses ISO 8601 UTC datetime (YYYY-MM-DDTHH:MM:SS.sssZ).",
                                    "type": "string"
                                  },
                                  "time_zone": {
                                    "description": "The time zone of the date time.",
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "date_time",
                                  "time_zone"
                                ]
                              },
                              {
                                "type": "object",
                                "properties": {
                                  "date": {
                                    "description": "The date. Uses ISO 8601 date format (YYYY-MM-DD).",
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "date"
                                ]
                              }
                            ]
                          },
                          "recurrence": {
                            "description": "List of RRULE, EXRULE, RDATE and EXDATE lines for a recurring event, as specified in RFC5545.",
                            "type": "array",
                            "items": {
                              "type": "string"
                            }
                          },
                          "organizer": {
                            "type": "object",
                            "properties": {
                              "email": {
                                "description": "Email address of the organizer.",
                                "type": "string"
                              },
                              "display_name": {
                                "description": "Display name of the organizer.",
                                "type": "string"
                              }
                            },
                            "required": [
                              "email"
                            ]
                          },
                          "conference": {
                            "type": "object",
                            "properties": {
                              "provider": {
                                "description": "The conference provider.",
                                "anyOf": [
                                  {
                                    "type": "string",
                                    "enum": [
                                      "google_meet"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "zoom"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "skype"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "teams"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "unknown"
                                    ]
                                  }
                                ]
                              },
                              "url": {
                                "description": "The conference URL. If not provided, it will automatically create a new conference (only skype and google_meet available)",
                                "type": "string"
                              }
                            },
                            "required": [
                              "provider"
                            ]
                          },
                          "visibility": {
                            "description": "The visibility of the event.",
                            "anyOf": [
                              {
                                "type": "string",
                                "enum": [
                                  "public"
                                ]
                              },
                              {
                                "type": "string",
                                "enum": [
                                  "private"
                                ]
                              }
                            ]
                          },
                          "transparency": {
                            "description": "The transparency of the event. `opaque` does block time on the calendar and is equivalent to setting Show me as to Busy in the Calendar UI. `transparent` does not block time on the calendar and is equivalent to setting Show me as to Available in the Calendar UI.",
                            "anyOf": [
                              {
                                "type": "string",
                                "enum": [
                                  "opaque"
                                ]
                              },
                              {
                                "type": "string",
                                "enum": [
                                  "transparent"
                                ]
                              }
                            ]
                          },
                          "event_type": {
                            "description": "The type of the event (`birthday`, `fromGmail`, `outOfOffice`...)",
                            "default": "default",
                            "type": "string"
                          }
                        },
                        "required": [
                          "object",
                          "id",
                          "calendar_id",
                          "created_at",
                          "updated_at",
                          "title",
                          "is_cancelled",
                          "is_all_day",
                          "is_attendees_list_hidden",
                          "start",
                          "end",
                          "organizer",
                          "visibility",
                          "transparency",
                          "event_type"
                        ]
                      }
                    },
                    "next_cursor": {
                      "description": "Cursor to get the next page of results if supported. Else use `offset`.",
                      "type": "string"
                    }
                  },
                  "required": [
                    "data"
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
          "Calendars"
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
      "name": "Calendars",
      "description": "Calendars management"
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