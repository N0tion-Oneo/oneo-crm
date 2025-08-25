# Unipile Email API Markdown:
## List all emails

# OpenAPI definition
```json
{
  "openapi": "3.0.0",
  "paths": {
    "/api/v1/emails": {
      "get": {
        "operationId": "MailsController_listMails",
        "x-readme": {
          "code-samples": [
            {
              "language": "node",
              "code": "import { UnipileClient } from \"unipile-node-sdk\"\n\n// SDK setup\nconst BASE_URL = \"your base url\"\nconst ACCESS_TOKEN = \"your access token\"\n\ntry {\n\tconst client = new UnipileClient(BASE_URL, ACCESS_TOKEN)\n\n\tconst response = await client.email.getAll()\n} catch (error) {\n\tconsole.log(error)\n}\n",
              "name": "unipile-node-sdk",
              "install": "npm install unipile-node-sdk"
            }
          ]
        },
        "summary": "List all emails",
        "description": "Returns a list of emails.",
        "parameters": [
          {
            "name": "message_id",
            "required": false,
            "in": "query",
            "description": "A filter to target items by message_id.",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "thread_id",
            "required": false,
            "in": "query",
            "description": "A filter to target items by thread identifier.",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "meta_only",
            "required": false,
            "in": "query",
            "description": "Speed up the response by only returning the email metadata, excluding the body and attachments metadata.",
            "schema": {
              "type": "boolean"
            }
          },
          {
            "name": "include_headers",
            "required": false,
            "in": "query",
            "description": "Include the email headers in the response. `meta_only` must be false.",
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
            "name": "any_email",
            "required": false,
            "in": "query",
            "description": "A filter to target items sent to or received from a comma-separated list of email addresses.",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "to",
            "required": false,
            "in": "query",
            "description": "A filter to target items related to a certain recipient, either in the to, cc or bcc field.",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "from",
            "required": false,
            "in": "query",
            "description": "A filter to target items related to a certain sender.",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "folder",
            "required": false,
            "in": "query",
            "description": "A filter to target items related to a certain folder provider_id.",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "account_id",
            "required": true,
            "in": "query",
            "description": "A filter to target items related to a certain account.",
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
                  "description": "@todo List of Emails.",
                  "type": "object",
                  "properties": {
                    "object": {
                      "type": "string",
                      "enum": [
                        "EmailList"
                      ]
                    },
                    "items": {
                      "type": "array",
                      "items": {
                        "anyOf": [
                          {
                            "title": "Mail reference",
                            "type": "object",
                            "properties": {
                              "object": {
                                "type": "string",
                                "enum": [
                                  "Email"
                                ]
                              },
                              "id": {
                                "title": "UniqueId",
                                "description": "A unique identifier.",
                                "minLength": 1,
                                "type": "string"
                              },
                              "deprecated_id": {
                                "title": "UniqueId",
                                "description": "A unique identifier.",
                                "minLength": 1,
                                "type": "string"
                              },
                              "kind": {
                                "type": "string",
                                "enum": [
                                  "0_ref"
                                ]
                              },
                              "account_id": {
                                "title": "UniqueId",
                                "description": "A unique identifier.",
                                "minLength": 1,
                                "type": "string"
                              },
                              "type": {
                                "anyOf": [
                                  {
                                    "type": "string",
                                    "enum": [
                                      "MAIL"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "GOOGLE"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "ICLOUD"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "OUTLOOK"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "EXCHANGE"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "GOOGLE_OAUTH"
                                    ]
                                  }
                                ]
                              },
                              "date": {
                                "description": "An ISO 8601 UTC datetime (YYYY-MM-DDTHH:MM:SS.sssZ). ⚠️ All links expire upon daily restart, regardless of their stated expiration date. A new link must be generated each time a user clicks on your app to connect.",
                                "example": "2025-12-31T23:59:59.999Z",
                                "pattern": "^[1-2]\\d{3}-[0-1]\\d-[0-3]\\dT\\d{2}:\\d{2}:\\d{2}.\\d{3}Z$"
                              },
                              "role": {
                                "anyOf": [
                                  {
                                    "type": "string",
                                    "enum": [
                                      "inbox"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "sent"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "archive"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "drafts"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "trash"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "spam"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "all"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "important"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "starred"
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
                              "folders": {
                                "type": "array",
                                "items": {
                                  "type": "string"
                                }
                              },
                              "folderIds": {
                                "type": "array",
                                "items": {
                                  "type": "string"
                                }
                              },
                              "read_date": {
                                "anyOf": [
                                  {
                                    "description": "An ISO 8601 UTC datetime (YYYY-MM-DDTHH:MM:SS.sssZ). ⚠️ All links expire upon daily restart, regardless of their stated expiration date. A new link must be generated each time a user clicks on your app to connect.",
                                    "example": "2025-12-31T23:59:59.999Z",
                                    "pattern": "^[1-2]\\d{3}-[0-1]\\d-[0-3]\\dT\\d{2}:\\d{2}:\\d{2}.\\d{3}Z$"
                                  },
                                  {
                                    "nullable": true
                                  }
                                ]
                              },
                              "message_id": {
                                "type": "string"
                              },
                              "provider_id": {
                                "type": "string"
                              }
                            },
                            "required": [
                              "object",
                              "id",
                              "deprecated_id",
                              "kind",
                              "account_id",
                              "type",
                              "date",
                              "role",
                              "folders",
                              "folderIds",
                              "message_id",
                              "provider_id"
                            ]
                          },
                          {
                            "title": "Mail metas",
                            "type": "object",
                            "properties": {
                              "object": {
                                "type": "string",
                                "enum": [
                                  "Email"
                                ]
                              },
                              "id": {
                                "title": "UniqueId",
                                "description": "A unique identifier.",
                                "minLength": 1,
                                "type": "string"
                              },
                              "deprecated_id": {
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
                              "type": {
                                "anyOf": [
                                  {
                                    "type": "string",
                                    "enum": [
                                      "MAIL"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "GOOGLE"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "ICLOUD"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "OUTLOOK"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "EXCHANGE"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "GOOGLE_OAUTH"
                                    ]
                                  }
                                ]
                              },
                              "date": {
                                "description": "An ISO 8601 UTC datetime (YYYY-MM-DDTHH:MM:SS.sssZ). ⚠️ All links expire upon daily restart, regardless of their stated expiration date. A new link must be generated each time a user clicks on your app to connect.",
                                "example": "2025-12-31T23:59:59.999Z",
                                "pattern": "^[1-2]\\d{3}-[0-1]\\d-[0-3]\\dT\\d{2}:\\d{2}:\\d{2}.\\d{3}Z$"
                              },
                              "role": {
                                "anyOf": [
                                  {
                                    "type": "string",
                                    "enum": [
                                      "inbox"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "sent"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "archive"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "drafts"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "trash"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "spam"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "all"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "important"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "starred"
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
                              "folders": {
                                "type": "array",
                                "items": {
                                  "type": "string"
                                }
                              },
                              "folderIds": {
                                "type": "array",
                                "items": {
                                  "type": "string"
                                }
                              },
                              "read_date": {
                                "anyOf": [
                                  {
                                    "description": "An ISO 8601 UTC datetime (YYYY-MM-DDTHH:MM:SS.sssZ). ⚠️ All links expire upon daily restart, regardless of their stated expiration date. A new link must be generated each time a user clicks on your app to connect.",
                                    "example": "2025-12-31T23:59:59.999Z",
                                    "pattern": "^[1-2]\\d{3}-[0-1]\\d-[0-3]\\dT\\d{2}:\\d{2}:\\d{2}.\\d{3}Z$"
                                  },
                                  {
                                    "nullable": true
                                  }
                                ]
                              },
                              "message_id": {
                                "type": "string"
                              },
                              "provider_id": {
                                "type": "string"
                              },
                              "kind": {
                                "type": "string",
                                "enum": [
                                  "1_meta"
                                ]
                              },
                              "body_plain": {
                                "type": "string",
                                "enum": [
                                  ""
                                ]
                              },
                              "body": {
                                "type": "string",
                                "enum": [
                                  ""
                                ]
                              },
                              "from_attendee": {
                                "type": "object",
                                "properties": {
                                  "display_name": {
                                    "type": "string"
                                  },
                                  "profile_picture": {
                                    "type": "string"
                                  },
                                  "identifier": {
                                    "type": "string"
                                  },
                                  "identifier_type": {
                                    "type": "string",
                                    "enum": [
                                      "CHAT_ATTENDEE_ID",
                                      "PHONE_NUMBER",
                                      "EMAIL_ADDRESS",
                                      "MESSENGER_ID",
                                      "MESSENGER_THREAD_ID",
                                      "TIKTOK_ID",
                                      "TIKTOK_THREAD_ID",
                                      "TWITTER_ID",
                                      "TWITTER_THREAD_ID",
                                      "INSTAGRAM_ID",
                                      "INSTAGRAM_THREAD_ID",
                                      "LINKEDIN_ID",
                                      "LINKEDIN_THREAD_ID",
                                      "GROUP_THREAD"
                                    ]
                                  }
                                },
                                "required": [
                                  "identifier",
                                  "identifier_type"
                                ]
                              },
                              "to_attendees": {
                                "type": "array",
                                "items": {
                                  "type": "object",
                                  "properties": {
                                    "display_name": {
                                      "type": "string"
                                    },
                                    "profile_picture": {
                                      "type": "string"
                                    },
                                    "identifier": {
                                      "type": "string"
                                    },
                                    "identifier_type": {
                                      "type": "string",
                                      "enum": [
                                        "CHAT_ATTENDEE_ID",
                                        "PHONE_NUMBER",
                                        "EMAIL_ADDRESS",
                                        "MESSENGER_ID",
                                        "MESSENGER_THREAD_ID",
                                        "TIKTOK_ID",
                                        "TIKTOK_THREAD_ID",
                                        "TWITTER_ID",
                                        "TWITTER_THREAD_ID",
                                        "INSTAGRAM_ID",
                                        "INSTAGRAM_THREAD_ID",
                                        "LINKEDIN_ID",
                                        "LINKEDIN_THREAD_ID",
                                        "GROUP_THREAD"
                                      ]
                                    }
                                  },
                                  "required": [
                                    "identifier",
                                    "identifier_type"
                                  ]
                                }
                              },
                              "cc_attendees": {
                                "type": "array",
                                "items": {
                                  "type": "object",
                                  "properties": {
                                    "display_name": {
                                      "type": "string"
                                    },
                                    "profile_picture": {
                                      "type": "string"
                                    },
                                    "identifier": {
                                      "type": "string"
                                    },
                                    "identifier_type": {
                                      "type": "string",
                                      "enum": [
                                        "CHAT_ATTENDEE_ID",
                                        "PHONE_NUMBER",
                                        "EMAIL_ADDRESS",
                                        "MESSENGER_ID",
                                        "MESSENGER_THREAD_ID",
                                        "TIKTOK_ID",
                                        "TIKTOK_THREAD_ID",
                                        "TWITTER_ID",
                                        "TWITTER_THREAD_ID",
                                        "INSTAGRAM_ID",
                                        "INSTAGRAM_THREAD_ID",
                                        "LINKEDIN_ID",
                                        "LINKEDIN_THREAD_ID",
                                        "GROUP_THREAD"
                                      ]
                                    }
                                  },
                                  "required": [
                                    "identifier",
                                    "identifier_type"
                                  ]
                                }
                              },
                              "bcc_attendees": {
                                "type": "array",
                                "items": {
                                  "type": "object",
                                  "properties": {
                                    "display_name": {
                                      "type": "string"
                                    },
                                    "profile_picture": {
                                      "type": "string"
                                    },
                                    "identifier": {
                                      "type": "string"
                                    },
                                    "identifier_type": {
                                      "type": "string",
                                      "enum": [
                                        "CHAT_ATTENDEE_ID",
                                        "PHONE_NUMBER",
                                        "EMAIL_ADDRESS",
                                        "MESSENGER_ID",
                                        "MESSENGER_THREAD_ID",
                                        "TIKTOK_ID",
                                        "TIKTOK_THREAD_ID",
                                        "TWITTER_ID",
                                        "TWITTER_THREAD_ID",
                                        "INSTAGRAM_ID",
                                        "INSTAGRAM_THREAD_ID",
                                        "LINKEDIN_ID",
                                        "LINKEDIN_THREAD_ID",
                                        "GROUP_THREAD"
                                      ]
                                    }
                                  },
                                  "required": [
                                    "identifier",
                                    "identifier_type"
                                  ]
                                }
                              },
                              "reply_to_attendees": {
                                "type": "array",
                                "items": {
                                  "type": "object",
                                  "properties": {
                                    "display_name": {
                                      "type": "string"
                                    },
                                    "profile_picture": {
                                      "type": "string"
                                    },
                                    "identifier": {
                                      "type": "string"
                                    },
                                    "identifier_type": {
                                      "type": "string",
                                      "enum": [
                                        "CHAT_ATTENDEE_ID",
                                        "PHONE_NUMBER",
                                        "EMAIL_ADDRESS",
                                        "MESSENGER_ID",
                                        "MESSENGER_THREAD_ID",
                                        "TIKTOK_ID",
                                        "TIKTOK_THREAD_ID",
                                        "TWITTER_ID",
                                        "TWITTER_THREAD_ID",
                                        "INSTAGRAM_ID",
                                        "INSTAGRAM_THREAD_ID",
                                        "LINKEDIN_ID",
                                        "LINKEDIN_THREAD_ID",
                                        "GROUP_THREAD"
                                      ]
                                    }
                                  },
                                  "required": [
                                    "identifier",
                                    "identifier_type"
                                  ]
                                }
                              },
                              "subject": {
                                "type": "string"
                              },
                              "has_attachments": {
                                "type": "boolean"
                              },
                              "origin": {
                                "anyOf": [
                                  {
                                    "type": "string",
                                    "enum": [
                                      "unipile"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "external"
                                    ]
                                  }
                                ]
                              },
                              "in_reply_to": {
                                "type": "object",
                                "properties": {
                                  "message_id": {
                                    "type": "string"
                                  },
                                  "id": {
                                    "title": "UniqueId",
                                    "description": "A unique identifier.",
                                    "minLength": 1,
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "message_id",
                                  "id"
                                ]
                              },
                              "tracking_id": {
                                "type": "string"
                              },
                              "thread_id": {
                                "type": "string"
                              },
                              "attachments": {
                                "type": "array",
                                "items": {
                                  "type": "object",
                                  "properties": {
                                    "id": {
                                      "type": "string"
                                    },
                                    "name": {
                                      "type": "string"
                                    },
                                    "size": {
                                      "type": "number"
                                    },
                                    "extension": {
                                      "type": "string"
                                    },
                                    "mime": {
                                      "type": "string"
                                    },
                                    "cid": {
                                      "type": "string"
                                    }
                                  },
                                  "required": [
                                    "id",
                                    "name",
                                    "size",
                                    "extension",
                                    "mime"
                                  ]
                                }
                              },
                              "parent_mail": {
                                "type": "object",
                                "properties": {
                                  "id": {
                                    "title": "UniqueId",
                                    "description": "A unique identifier.",
                                    "minLength": 1,
                                    "type": "string"
                                  },
                                  "deprecated_id": {
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
                                  "type": {
                                    "anyOf": [
                                      {
                                        "type": "string",
                                        "enum": [
                                          "MAIL"
                                        ]
                                      },
                                      {
                                        "type": "string",
                                        "enum": [
                                          "GOOGLE"
                                        ]
                                      },
                                      {
                                        "type": "string",
                                        "enum": [
                                          "ICLOUD"
                                        ]
                                      },
                                      {
                                        "type": "string",
                                        "enum": [
                                          "OUTLOOK"
                                        ]
                                      },
                                      {
                                        "type": "string",
                                        "enum": [
                                          "EXCHANGE"
                                        ]
                                      },
                                      {
                                        "type": "string",
                                        "enum": [
                                          "GOOGLE_OAUTH"
                                        ]
                                      }
                                    ]
                                  },
                                  "date": {
                                    "description": "An ISO 8601 UTC datetime (YYYY-MM-DDTHH:MM:SS.sssZ). ⚠️ All links expire upon daily restart, regardless of their stated expiration date. A new link must be generated each time a user clicks on your app to connect.",
                                    "example": "2025-12-31T23:59:59.999Z",
                                    "pattern": "^[1-2]\\d{3}-[0-1]\\d-[0-3]\\dT\\d{2}:\\d{2}:\\d{2}.\\d{3}Z$"
                                  },
                                  "role": {
                                    "anyOf": [
                                      {
                                        "type": "string",
                                        "enum": [
                                          "inbox"
                                        ]
                                      },
                                      {
                                        "type": "string",
                                        "enum": [
                                          "sent"
                                        ]
                                      },
                                      {
                                        "type": "string",
                                        "enum": [
                                          "archive"
                                        ]
                                      },
                                      {
                                        "type": "string",
                                        "enum": [
                                          "drafts"
                                        ]
                                      },
                                      {
                                        "type": "string",
                                        "enum": [
                                          "trash"
                                        ]
                                      },
                                      {
                                        "type": "string",
                                        "enum": [
                                          "spam"
                                        ]
                                      },
                                      {
                                        "type": "string",
                                        "enum": [
                                          "all"
                                        ]
                                      },
                                      {
                                        "type": "string",
                                        "enum": [
                                          "important"
                                        ]
                                      },
                                      {
                                        "type": "string",
                                        "enum": [
                                          "starred"
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
                                  "folders": {
                                    "type": "array",
                                    "items": {
                                      "type": "string"
                                    }
                                  },
                                  "folderIds": {
                                    "type": "array",
                                    "items": {
                                      "type": "string"
                                    }
                                  },
                                  "read_date": {
                                    "anyOf": [
                                      {
                                        "description": "An ISO 8601 UTC datetime (YYYY-MM-DDTHH:MM:SS.sssZ). ⚠️ All links expire upon daily restart, regardless of their stated expiration date. A new link must be generated each time a user clicks on your app to connect.",
                                        "example": "2025-12-31T23:59:59.999Z",
                                        "pattern": "^[1-2]\\d{3}-[0-1]\\d-[0-3]\\dT\\d{2}:\\d{2}:\\d{2}.\\d{3}Z$"
                                      },
                                      {
                                        "nullable": true
                                      }
                                    ]
                                  },
                                  "message_id": {
                                    "type": "string"
                                  },
                                  "provider_id": {
                                    "type": "string"
                                  },
                                  "kind": {
                                    "type": "string",
                                    "enum": [
                                      "1_meta"
                                    ]
                                  },
                                  "body_plain": {
                                    "type": "string",
                                    "enum": [
                                      ""
                                    ]
                                  },
                                  "body": {
                                    "type": "string",
                                    "enum": [
                                      ""
                                    ]
                                  },
                                  "from_attendee": {
                                    "type": "object",
                                    "properties": {
                                      "display_name": {
                                        "type": "string"
                                      },
                                      "profile_picture": {
                                        "type": "string"
                                      },
                                      "identifier": {
                                        "type": "string"
                                      },
                                      "identifier_type": {
                                        "type": "string",
                                        "enum": [
                                          "CHAT_ATTENDEE_ID",
                                          "PHONE_NUMBER",
                                          "EMAIL_ADDRESS",
                                          "MESSENGER_ID",
                                          "MESSENGER_THREAD_ID",
                                          "TIKTOK_ID",
                                          "TIKTOK_THREAD_ID",
                                          "TWITTER_ID",
                                          "TWITTER_THREAD_ID",
                                          "INSTAGRAM_ID",
                                          "INSTAGRAM_THREAD_ID",
                                          "LINKEDIN_ID",
                                          "LINKEDIN_THREAD_ID",
                                          "GROUP_THREAD"
                                        ]
                                      }
                                    },
                                    "required": [
                                      "identifier",
                                      "identifier_type"
                                    ]
                                  },
                                  "to_attendees": {
                                    "type": "array",
                                    "items": {
                                      "type": "object",
                                      "properties": {
                                        "display_name": {
                                          "type": "string"
                                        },
                                        "profile_picture": {
                                          "type": "string"
                                        },
                                        "identifier": {
                                          "type": "string"
                                        },
                                        "identifier_type": {
                                          "type": "string",
                                          "enum": [
                                            "CHAT_ATTENDEE_ID",
                                            "PHONE_NUMBER",
                                            "EMAIL_ADDRESS",
                                            "MESSENGER_ID",
                                            "MESSENGER_THREAD_ID",
                                            "TIKTOK_ID",
                                            "TIKTOK_THREAD_ID",
                                            "TWITTER_ID",
                                            "TWITTER_THREAD_ID",
                                            "INSTAGRAM_ID",
                                            "INSTAGRAM_THREAD_ID",
                                            "LINKEDIN_ID",
                                            "LINKEDIN_THREAD_ID",
                                            "GROUP_THREAD"
                                          ]
                                        }
                                      },
                                      "required": [
                                        "identifier",
                                        "identifier_type"
                                      ]
                                    }
                                  },
                                  "cc_attendees": {
                                    "type": "array",
                                    "items": {
                                      "type": "object",
                                      "properties": {
                                        "display_name": {
                                          "type": "string"
                                        },
                                        "profile_picture": {
                                          "type": "string"
                                        },
                                        "identifier": {
                                          "type": "string"
                                        },
                                        "identifier_type": {
                                          "type": "string",
                                          "enum": [
                                            "CHAT_ATTENDEE_ID",
                                            "PHONE_NUMBER",
                                            "EMAIL_ADDRESS",
                                            "MESSENGER_ID",
                                            "MESSENGER_THREAD_ID",
                                            "TIKTOK_ID",
                                            "TIKTOK_THREAD_ID",
                                            "TWITTER_ID",
                                            "TWITTER_THREAD_ID",
                                            "INSTAGRAM_ID",
                                            "INSTAGRAM_THREAD_ID",
                                            "LINKEDIN_ID",
                                            "LINKEDIN_THREAD_ID",
                                            "GROUP_THREAD"
                                          ]
                                        }
                                      },
                                      "required": [
                                        "identifier",
                                        "identifier_type"
                                      ]
                                    }
                                  },
                                  "bcc_attendees": {
                                    "type": "array",
                                    "items": {
                                      "type": "object",
                                      "properties": {
                                        "display_name": {
                                          "type": "string"
                                        },
                                        "profile_picture": {
                                          "type": "string"
                                        },
                                        "identifier": {
                                          "type": "string"
                                        },
                                        "identifier_type": {
                                          "type": "string",
                                          "enum": [
                                            "CHAT_ATTENDEE_ID",
                                            "PHONE_NUMBER",
                                            "EMAIL_ADDRESS",
                                            "MESSENGER_ID",
                                            "MESSENGER_THREAD_ID",
                                            "TIKTOK_ID",
                                            "TIKTOK_THREAD_ID",
                                            "TWITTER_ID",
                                            "TWITTER_THREAD_ID",
                                            "INSTAGRAM_ID",
                                            "INSTAGRAM_THREAD_ID",
                                            "LINKEDIN_ID",
                                            "LINKEDIN_THREAD_ID",
                                            "GROUP_THREAD"
                                          ]
                                        }
                                      },
                                      "required": [
                                        "identifier",
                                        "identifier_type"
                                      ]
                                    }
                                  },
                                  "reply_to_attendees": {
                                    "type": "array",
                                    "items": {
                                      "type": "object",
                                      "properties": {
                                        "display_name": {
                                          "type": "string"
                                        },
                                        "profile_picture": {
                                          "type": "string"
                                        },
                                        "identifier": {
                                          "type": "string"
                                        },
                                        "identifier_type": {
                                          "type": "string",
                                          "enum": [
                                            "CHAT_ATTENDEE_ID",
                                            "PHONE_NUMBER",
                                            "EMAIL_ADDRESS",
                                            "MESSENGER_ID",
                                            "MESSENGER_THREAD_ID",
                                            "TIKTOK_ID",
                                            "TIKTOK_THREAD_ID",
                                            "TWITTER_ID",
                                            "TWITTER_THREAD_ID",
                                            "INSTAGRAM_ID",
                                            "INSTAGRAM_THREAD_ID",
                                            "LINKEDIN_ID",
                                            "LINKEDIN_THREAD_ID",
                                            "GROUP_THREAD"
                                          ]
                                        }
                                      },
                                      "required": [
                                        "identifier",
                                        "identifier_type"
                                      ]
                                    }
                                  },
                                  "subject": {
                                    "type": "string"
                                  },
                                  "has_attachments": {
                                    "type": "boolean"
                                  },
                                  "origin": {
                                    "anyOf": [
                                      {
                                        "type": "string",
                                        "enum": [
                                          "unipile"
                                        ]
                                      },
                                      {
                                        "type": "string",
                                        "enum": [
                                          "external"
                                        ]
                                      }
                                    ]
                                  },
                                  "in_reply_to": {
                                    "type": "object",
                                    "properties": {
                                      "message_id": {
                                        "type": "string"
                                      },
                                      "id": {
                                        "title": "UniqueId",
                                        "description": "A unique identifier.",
                                        "minLength": 1,
                                        "type": "string"
                                      }
                                    },
                                    "required": [
                                      "message_id",
                                      "id"
                                    ]
                                  },
                                  "tracking_id": {
                                    "type": "string"
                                  },
                                  "thread_id": {
                                    "type": "string"
                                  },
                                  "attachments": {
                                    "type": "array",
                                    "items": {
                                      "type": "object",
                                      "properties": {
                                        "id": {
                                          "type": "string"
                                        },
                                        "name": {
                                          "type": "string"
                                        },
                                        "size": {
                                          "type": "number"
                                        },
                                        "extension": {
                                          "type": "string"
                                        },
                                        "mime": {
                                          "type": "string"
                                        },
                                        "cid": {
                                          "type": "string"
                                        }
                                      },
                                      "required": [
                                        "id",
                                        "name",
                                        "size",
                                        "extension",
                                        "mime"
                                      ]
                                    }
                                  }
                                },
                                "required": [
                                  "id",
                                  "deprecated_id",
                                  "account_id",
                                  "type",
                                  "date",
                                  "role",
                                  "folders",
                                  "folderIds",
                                  "message_id",
                                  "provider_id",
                                  "kind",
                                  "body_plain",
                                  "body",
                                  "from_attendee",
                                  "subject",
                                  "has_attachments",
                                  "origin",
                                  "attachments"
                                ]
                              }
                            },
                            "required": [
                              "object",
                              "id",
                              "deprecated_id",
                              "account_id",
                              "type",
                              "date",
                              "role",
                              "folders",
                              "folderIds",
                              "message_id",
                              "provider_id",
                              "kind",
                              "body_plain",
                              "body",
                              "from_attendee",
                              "subject",
                              "has_attachments",
                              "origin",
                              "attachments"
                            ]
                          },
                          {
                            "title": "Full mail",
                            "type": "object",
                            "properties": {
                              "object": {
                                "type": "string",
                                "enum": [
                                  "Email"
                                ]
                              },
                              "id": {
                                "title": "UniqueId",
                                "description": "A unique identifier.",
                                "minLength": 1,
                                "type": "string"
                              },
                              "deprecated_id": {
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
                              "type": {
                                "anyOf": [
                                  {
                                    "type": "string",
                                    "enum": [
                                      "MAIL"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "GOOGLE"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "ICLOUD"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "OUTLOOK"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "EXCHANGE"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "GOOGLE_OAUTH"
                                    ]
                                  }
                                ]
                              },
                              "date": {
                                "description": "An ISO 8601 UTC datetime (YYYY-MM-DDTHH:MM:SS.sssZ). ⚠️ All links expire upon daily restart, regardless of their stated expiration date. A new link must be generated each time a user clicks on your app to connect.",
                                "example": "2025-12-31T23:59:59.999Z",
                                "pattern": "^[1-2]\\d{3}-[0-1]\\d-[0-3]\\dT\\d{2}:\\d{2}:\\d{2}.\\d{3}Z$"
                              },
                              "role": {
                                "anyOf": [
                                  {
                                    "type": "string",
                                    "enum": [
                                      "inbox"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "sent"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "archive"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "drafts"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "trash"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "spam"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "all"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "important"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "starred"
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
                              "folders": {
                                "type": "array",
                                "items": {
                                  "type": "string"
                                }
                              },
                              "folderIds": {
                                "type": "array",
                                "items": {
                                  "type": "string"
                                }
                              },
                              "read_date": {
                                "anyOf": [
                                  {
                                    "description": "An ISO 8601 UTC datetime (YYYY-MM-DDTHH:MM:SS.sssZ). ⚠️ All links expire upon daily restart, regardless of their stated expiration date. A new link must be generated each time a user clicks on your app to connect.",
                                    "example": "2025-12-31T23:59:59.999Z",
                                    "pattern": "^[1-2]\\d{3}-[0-1]\\d-[0-3]\\dT\\d{2}:\\d{2}:\\d{2}.\\d{3}Z$"
                                  },
                                  {
                                    "nullable": true
                                  }
                                ]
                              },
                              "message_id": {
                                "type": "string"
                              },
                              "provider_id": {
                                "type": "string"
                              },
                              "from_attendee": {
                                "type": "object",
                                "properties": {
                                  "display_name": {
                                    "type": "string"
                                  },
                                  "profile_picture": {
                                    "type": "string"
                                  },
                                  "identifier": {
                                    "type": "string"
                                  },
                                  "identifier_type": {
                                    "type": "string",
                                    "enum": [
                                      "CHAT_ATTENDEE_ID",
                                      "PHONE_NUMBER",
                                      "EMAIL_ADDRESS",
                                      "MESSENGER_ID",
                                      "MESSENGER_THREAD_ID",
                                      "TIKTOK_ID",
                                      "TIKTOK_THREAD_ID",
                                      "TWITTER_ID",
                                      "TWITTER_THREAD_ID",
                                      "INSTAGRAM_ID",
                                      "INSTAGRAM_THREAD_ID",
                                      "LINKEDIN_ID",
                                      "LINKEDIN_THREAD_ID",
                                      "GROUP_THREAD"
                                    ]
                                  }
                                },
                                "required": [
                                  "identifier",
                                  "identifier_type"
                                ]
                              },
                              "to_attendees": {
                                "type": "array",
                                "items": {
                                  "type": "object",
                                  "properties": {
                                    "display_name": {
                                      "type": "string"
                                    },
                                    "profile_picture": {
                                      "type": "string"
                                    },
                                    "identifier": {
                                      "type": "string"
                                    },
                                    "identifier_type": {
                                      "type": "string",
                                      "enum": [
                                        "CHAT_ATTENDEE_ID",
                                        "PHONE_NUMBER",
                                        "EMAIL_ADDRESS",
                                        "MESSENGER_ID",
                                        "MESSENGER_THREAD_ID",
                                        "TIKTOK_ID",
                                        "TIKTOK_THREAD_ID",
                                        "TWITTER_ID",
                                        "TWITTER_THREAD_ID",
                                        "INSTAGRAM_ID",
                                        "INSTAGRAM_THREAD_ID",
                                        "LINKEDIN_ID",
                                        "LINKEDIN_THREAD_ID",
                                        "GROUP_THREAD"
                                      ]
                                    }
                                  },
                                  "required": [
                                    "identifier",
                                    "identifier_type"
                                  ]
                                }
                              },
                              "cc_attendees": {
                                "type": "array",
                                "items": {
                                  "type": "object",
                                  "properties": {
                                    "display_name": {
                                      "type": "string"
                                    },
                                    "profile_picture": {
                                      "type": "string"
                                    },
                                    "identifier": {
                                      "type": "string"
                                    },
                                    "identifier_type": {
                                      "type": "string",
                                      "enum": [
                                        "CHAT_ATTENDEE_ID",
                                        "PHONE_NUMBER",
                                        "EMAIL_ADDRESS",
                                        "MESSENGER_ID",
                                        "MESSENGER_THREAD_ID",
                                        "TIKTOK_ID",
                                        "TIKTOK_THREAD_ID",
                                        "TWITTER_ID",
                                        "TWITTER_THREAD_ID",
                                        "INSTAGRAM_ID",
                                        "INSTAGRAM_THREAD_ID",
                                        "LINKEDIN_ID",
                                        "LINKEDIN_THREAD_ID",
                                        "GROUP_THREAD"
                                      ]
                                    }
                                  },
                                  "required": [
                                    "identifier",
                                    "identifier_type"
                                  ]
                                }
                              },
                              "bcc_attendees": {
                                "type": "array",
                                "items": {
                                  "type": "object",
                                  "properties": {
                                    "display_name": {
                                      "type": "string"
                                    },
                                    "profile_picture": {
                                      "type": "string"
                                    },
                                    "identifier": {
                                      "type": "string"
                                    },
                                    "identifier_type": {
                                      "type": "string",
                                      "enum": [
                                        "CHAT_ATTENDEE_ID",
                                        "PHONE_NUMBER",
                                        "EMAIL_ADDRESS",
                                        "MESSENGER_ID",
                                        "MESSENGER_THREAD_ID",
                                        "TIKTOK_ID",
                                        "TIKTOK_THREAD_ID",
                                        "TWITTER_ID",
                                        "TWITTER_THREAD_ID",
                                        "INSTAGRAM_ID",
                                        "INSTAGRAM_THREAD_ID",
                                        "LINKEDIN_ID",
                                        "LINKEDIN_THREAD_ID",
                                        "GROUP_THREAD"
                                      ]
                                    }
                                  },
                                  "required": [
                                    "identifier",
                                    "identifier_type"
                                  ]
                                }
                              },
                              "reply_to_attendees": {
                                "type": "array",
                                "items": {
                                  "type": "object",
                                  "properties": {
                                    "display_name": {
                                      "type": "string"
                                    },
                                    "profile_picture": {
                                      "type": "string"
                                    },
                                    "identifier": {
                                      "type": "string"
                                    },
                                    "identifier_type": {
                                      "type": "string",
                                      "enum": [
                                        "CHAT_ATTENDEE_ID",
                                        "PHONE_NUMBER",
                                        "EMAIL_ADDRESS",
                                        "MESSENGER_ID",
                                        "MESSENGER_THREAD_ID",
                                        "TIKTOK_ID",
                                        "TIKTOK_THREAD_ID",
                                        "TWITTER_ID",
                                        "TWITTER_THREAD_ID",
                                        "INSTAGRAM_ID",
                                        "INSTAGRAM_THREAD_ID",
                                        "LINKEDIN_ID",
                                        "LINKEDIN_THREAD_ID",
                                        "GROUP_THREAD"
                                      ]
                                    }
                                  },
                                  "required": [
                                    "identifier",
                                    "identifier_type"
                                  ]
                                }
                              },
                              "subject": {
                                "type": "string"
                              },
                              "has_attachments": {
                                "type": "boolean"
                              },
                              "origin": {
                                "anyOf": [
                                  {
                                    "type": "string",
                                    "enum": [
                                      "unipile"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "external"
                                    ]
                                  }
                                ]
                              },
                              "in_reply_to": {
                                "type": "object",
                                "properties": {
                                  "message_id": {
                                    "type": "string"
                                  },
                                  "id": {
                                    "title": "UniqueId",
                                    "description": "A unique identifier.",
                                    "minLength": 1,
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "message_id",
                                  "id"
                                ]
                              },
                              "tracking_id": {
                                "type": "string"
                              },
                              "thread_id": {
                                "type": "string"
                              },
                              "attachments": {
                                "type": "array",
                                "items": {
                                  "type": "object",
                                  "properties": {
                                    "id": {
                                      "type": "string"
                                    },
                                    "name": {
                                      "type": "string"
                                    },
                                    "size": {
                                      "type": "number"
                                    },
                                    "extension": {
                                      "type": "string"
                                    },
                                    "mime": {
                                      "type": "string"
                                    },
                                    "cid": {
                                      "type": "string"
                                    }
                                  },
                                  "required": [
                                    "id",
                                    "name",
                                    "size",
                                    "extension",
                                    "mime"
                                  ]
                                }
                              },
                              "kind": {
                                "type": "string",
                                "enum": [
                                  "2_full"
                                ]
                              },
                              "body_plain": {
                                "type": "string"
                              },
                              "body": {
                                "type": "string"
                              },
                              "headers": {
                                "type": "array",
                                "items": {
                                  "type": "object",
                                  "properties": {
                                    "name": {
                                      "type": "string"
                                    },
                                    "value": {
                                      "type": "string"
                                    }
                                  },
                                  "required": [
                                    "name",
                                    "value"
                                  ]
                                }
                              }
                            },
                            "required": [
                              "object",
                              "id",
                              "deprecated_id",
                              "account_id",
                              "type",
                              "date",
                              "role",
                              "folders",
                              "folderIds",
                              "message_id",
                              "provider_id",
                              "from_attendee",
                              "subject",
                              "has_attachments",
                              "origin",
                              "attachments",
                              "kind",
                              "body_plain",
                              "body"
                            ]
                          }
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
          "Emails"
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
      "name": "Emails",
      "description": "Emails management"
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