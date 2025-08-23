Retrieve a post

# OpenAPI definition
```json
{
  "openapi": "3.0.0",
  "paths": {
    "/api/v1/posts/{post_id}": {
      "get": {
        "operationId": "PostsController_getPost",
        "x-readme": {
          "code-samples": [
            {
              "language": "node",
              "code": "import { UnipileClient } from \"unipile-node-sdk\"\n\n// SDK setup\nconst BASE_URL = \"your base url\"\nconst ACCESS_TOKEN = \"your access token\"\n// Inputs\nconst account_id = \"account id\"\nconst post_id = \"post id\"\n\ntry {\n\tconst client = new UnipileClient(BASE_URL, ACCESS_TOKEN)\n\n\tconst response = await client.users.getPost({\n\t\taccount_id,\n\t\tpost_id,\n\t})\n} catch (error) {\n\tconsole.log(error)\n}\n",
              "name": "unipile-node-sdk",
              "install": "npm install unipile-node-sdk"
            }
          ]
        },
        "summary": "Retrieve a post",
        "description": "Retrieve the details of a post.",
        "parameters": [
          {
            "name": "post_id",
            "required": true,
            "in": "path",
            "description": "The id of the post. <br>        `Instagram`: You can use the **provider_id** or the **shortcode** found in the post URL. (***www.instagram.com/reel/SHORTCODE***)",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "account_id",
            "required": true,
            "in": "query",
            "description": "The id of the account to perform the request from.",
            "schema": {
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
                  "allOf": [
                    {
                      "anyOf": [
                        {
                          "type": "object",
                          "properties": {
                            "provider": {
                              "type": "string",
                              "enum": [
                                "LINKEDIN"
                              ]
                            },
                            "id": {
                              "title": "UniqueId",
                              "description": "A unique identifier.",
                              "minLength": 1,
                              "type": "string"
                            },
                            "social_id": {
                              "description": "A unique identifier to be used to add a comment or a reaction to the post.",
                              "type": "string"
                            },
                            "share_url": {
                              "type": "string"
                            },
                            "title": {
                              "type": "string"
                            },
                            "text": {
                              "type": "string"
                            },
                            "date": {
                              "type": "string"
                            },
                            "parsed_datetime": {
                              "type": "string"
                            },
                            "reaction_counter": {
                              "type": "number"
                            },
                            "comment_counter": {
                              "type": "number"
                            },
                            "repost_counter": {
                              "type": "number"
                            },
                            "impressions_counter": {
                              "type": "number"
                            },
                            "author": {
                              "type": "object",
                              "properties": {
                                "public_identifier": {
                                  "anyOf": [
                                    {
                                      "type": "string"
                                    },
                                    {
                                      "nullable": true
                                    }
                                  ]
                                },
                                "id": {
                                  "anyOf": [
                                    {
                                      "type": "string"
                                    },
                                    {
                                      "nullable": true
                                    }
                                  ]
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
                                "is_company": {
                                  "type": "boolean"
                                },
                                "headline": {
                                  "type": "string"
                                }
                              },
                              "required": [
                                "public_identifier",
                                "id",
                                "name",
                                "is_company"
                              ]
                            },
                            "written_by": {
                              "type": "object",
                              "properties": {
                                "id": {
                                  "type": "string"
                                },
                                "public_identifier": {
                                  "type": "string"
                                },
                                "name": {
                                  "type": "string"
                                }
                              },
                              "required": [
                                "id",
                                "public_identifier",
                                "name"
                              ]
                            },
                            "permissions": {
                              "type": "object",
                              "properties": {
                                "can_react": {
                                  "type": "boolean"
                                },
                                "can_share": {
                                  "type": "boolean"
                                },
                                "can_post_comments": {
                                  "type": "boolean"
                                }
                              },
                              "required": [
                                "can_react",
                                "can_share",
                                "can_post_comments"
                              ]
                            },
                            "is_repost": {
                              "type": "boolean"
                            },
                            "repost_id": {
                              "description": "The republication ID.",
                              "type": "string"
                            },
                            "reposted_by": {
                              "type": "object",
                              "properties": {
                                "public_identifier": {
                                  "anyOf": [
                                    {
                                      "type": "string"
                                    },
                                    {
                                      "nullable": true
                                    }
                                  ]
                                },
                                "id": {
                                  "anyOf": [
                                    {
                                      "type": "string"
                                    },
                                    {
                                      "nullable": true
                                    }
                                  ]
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
                                "is_company": {
                                  "type": "boolean"
                                },
                                "headline": {
                                  "type": "string"
                                }
                              },
                              "required": [
                                "public_identifier",
                                "id",
                                "name",
                                "is_company"
                              ]
                            },
                            "repost_content": {
                              "description": "The post shared in the current publication.",
                              "type": "object",
                              "properties": {
                                "id": {
                                  "title": "UniqueId",
                                  "description": "A unique identifier.",
                                  "minLength": 1,
                                  "type": "string"
                                },
                                "date": {
                                  "type": "string"
                                },
                                "parsed_datetime": {
                                  "type": "string"
                                },
                                "author": {
                                  "type": "object",
                                  "properties": {
                                    "public_identifier": {
                                      "anyOf": [
                                        {
                                          "type": "string"
                                        },
                                        {
                                          "nullable": true
                                        }
                                      ]
                                    },
                                    "id": {
                                      "anyOf": [
                                        {
                                          "type": "string"
                                        },
                                        {
                                          "nullable": true
                                        }
                                      ]
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
                                    "is_company": {
                                      "type": "boolean"
                                    },
                                    "headline": {
                                      "type": "string"
                                    }
                                  },
                                  "required": [
                                    "public_identifier",
                                    "id",
                                    "name",
                                    "is_company"
                                  ]
                                },
                                "text": {
                                  "type": "string"
                                }
                              },
                              "required": [
                                "id",
                                "date",
                                "parsed_datetime",
                                "author",
                                "text"
                              ]
                            },
                            "attachments": {
                              "type": "array",
                              "items": {
                                "anyOf": [
                                  {
                                    "type": "object",
                                    "properties": {
                                      "id": {
                                        "type": "string"
                                      },
                                      "file_size": {
                                        "type": "number"
                                      },
                                      "unavailable": {
                                        "type": "boolean"
                                      },
                                      "mimetype": {
                                        "type": "string"
                                      },
                                      "url": {
                                        "type": "string"
                                      },
                                      "url_expires_at": {
                                        "type": "number"
                                      },
                                      "type": {
                                        "type": "string",
                                        "enum": [
                                          "img"
                                        ]
                                      },
                                      "size": {
                                        "type": "object",
                                        "properties": {
                                          "width": {
                                            "type": "number"
                                          },
                                          "height": {
                                            "type": "number"
                                          }
                                        },
                                        "required": [
                                          "width",
                                          "height"
                                        ]
                                      },
                                      "sticker": {
                                        "type": "boolean"
                                      }
                                    },
                                    "required": [
                                      "id",
                                      "unavailable",
                                      "type",
                                      "size",
                                      "sticker"
                                    ]
                                  },
                                  {
                                    "type": "object",
                                    "properties": {
                                      "id": {
                                        "type": "string"
                                      },
                                      "file_size": {
                                        "type": "number"
                                      },
                                      "unavailable": {
                                        "type": "boolean"
                                      },
                                      "mimetype": {
                                        "type": "string"
                                      },
                                      "url": {
                                        "type": "string"
                                      },
                                      "url_expires_at": {
                                        "type": "number"
                                      },
                                      "type": {
                                        "type": "string",
                                        "enum": [
                                          "video"
                                        ]
                                      },
                                      "size": {
                                        "type": "object",
                                        "properties": {
                                          "width": {
                                            "type": "number"
                                          },
                                          "height": {
                                            "type": "number"
                                          }
                                        },
                                        "required": [
                                          "width",
                                          "height"
                                        ]
                                      },
                                      "gif": {
                                        "type": "boolean"
                                      }
                                    },
                                    "required": [
                                      "id",
                                      "unavailable",
                                      "type",
                                      "size",
                                      "gif"
                                    ]
                                  },
                                  {
                                    "type": "object",
                                    "properties": {
                                      "id": {
                                        "type": "string"
                                      },
                                      "file_size": {
                                        "type": "number"
                                      },
                                      "unavailable": {
                                        "type": "boolean"
                                      },
                                      "mimetype": {
                                        "type": "string"
                                      },
                                      "url": {
                                        "type": "string"
                                      },
                                      "url_expires_at": {
                                        "type": "number"
                                      },
                                      "type": {
                                        "type": "string",
                                        "enum": [
                                          "audio"
                                        ]
                                      },
                                      "duration": {
                                        "type": "number"
                                      },
                                      "voice_note": {
                                        "type": "boolean"
                                      }
                                    },
                                    "required": [
                                      "id",
                                      "unavailable",
                                      "type",
                                      "voice_note"
                                    ]
                                  },
                                  {
                                    "type": "object",
                                    "properties": {
                                      "id": {
                                        "type": "string"
                                      },
                                      "file_size": {
                                        "type": "number"
                                      },
                                      "unavailable": {
                                        "type": "boolean"
                                      },
                                      "mimetype": {
                                        "type": "string"
                                      },
                                      "url": {
                                        "type": "string"
                                      },
                                      "url_expires_at": {
                                        "type": "number"
                                      },
                                      "type": {
                                        "type": "string",
                                        "enum": [
                                          "file"
                                        ]
                                      },
                                      "file_name": {
                                        "type": "string"
                                      }
                                    },
                                    "required": [
                                      "id",
                                      "unavailable",
                                      "type",
                                      "file_name"
                                    ]
                                  },
                                  {
                                    "type": "object",
                                    "properties": {
                                      "id": {
                                        "type": "string"
                                      },
                                      "file_size": {
                                        "type": "number"
                                      },
                                      "unavailable": {
                                        "type": "boolean"
                                      },
                                      "mimetype": {
                                        "type": "string"
                                      },
                                      "url": {
                                        "type": "string"
                                      },
                                      "url_expires_at": {
                                        "type": "number"
                                      },
                                      "type": {
                                        "type": "string",
                                        "enum": [
                                          "linkedin_post"
                                        ]
                                      }
                                    },
                                    "required": [
                                      "id",
                                      "unavailable",
                                      "type"
                                    ]
                                  },
                                  {
                                    "type": "object",
                                    "properties": {
                                      "id": {
                                        "type": "string"
                                      },
                                      "file_size": {
                                        "type": "number"
                                      },
                                      "unavailable": {
                                        "type": "boolean"
                                      },
                                      "mimetype": {
                                        "type": "string"
                                      },
                                      "url": {
                                        "type": "string"
                                      },
                                      "url_expires_at": {
                                        "type": "number"
                                      },
                                      "type": {
                                        "type": "string",
                                        "enum": [
                                          "video_meeting"
                                        ]
                                      },
                                      "starts_at": {
                                        "anyOf": [
                                          {
                                            "type": "number"
                                          },
                                          {
                                            "nullable": true
                                          }
                                        ]
                                      },
                                      "expires_at": {
                                        "anyOf": [
                                          {
                                            "type": "number"
                                          },
                                          {
                                            "nullable": true
                                          }
                                        ]
                                      },
                                      "time_range": {
                                        "anyOf": [
                                          {
                                            "type": "number"
                                          },
                                          {
                                            "nullable": true
                                          }
                                        ]
                                      }
                                    },
                                    "required": [
                                      "id",
                                      "unavailable",
                                      "type",
                                      "starts_at",
                                      "expires_at",
                                      "time_range"
                                    ]
                                  }
                                ]
                              }
                            },
                            "poll": {
                              "type": "object",
                              "properties": {
                                "id": {
                                  "title": "UniqueId",
                                  "description": "A unique identifier.",
                                  "minLength": 1,
                                  "type": "string"
                                },
                                "total_votes_count": {
                                  "type": "number"
                                },
                                "question": {
                                  "type": "string"
                                },
                                "is_open": {
                                  "type": "boolean"
                                },
                                "options": {
                                  "type": "array",
                                  "items": {
                                    "type": "object",
                                    "properties": {
                                      "id": {
                                        "title": "UniqueId",
                                        "description": "A unique identifier.",
                                        "minLength": 1,
                                        "type": "string"
                                      },
                                      "text": {
                                        "type": "string"
                                      },
                                      "win": {
                                        "type": "boolean"
                                      },
                                      "votes_count": {
                                        "type": "number"
                                      }
                                    },
                                    "required": [
                                      "id",
                                      "text",
                                      "win",
                                      "votes_count"
                                    ]
                                  }
                                }
                              },
                              "required": [
                                "id",
                                "total_votes_count",
                                "question",
                                "is_open",
                                "options"
                              ]
                            },
                            "group": {
                              "type": "object",
                              "properties": {
                                "id": {
                                  "type": "string"
                                },
                                "name": {
                                  "type": "string"
                                },
                                "private": {
                                  "type": "boolean"
                                }
                              },
                              "required": [
                                "id",
                                "name",
                                "private"
                              ]
                            },
                            "analytics": {
                              "type": "object",
                              "properties": {
                                "impressions": {
                                  "type": "number"
                                },
                                "engagements": {
                                  "type": "number"
                                },
                                "engagement_rate": {
                                  "type": "number"
                                },
                                "clicks": {
                                  "type": "number"
                                },
                                "clickthrough_rate": {
                                  "type": "number"
                                },
                                "page_viewers_from_this_post": {
                                  "type": "number"
                                },
                                "followers_gained_from_this_post": {
                                  "type": "number"
                                },
                                "members_reached": {
                                  "type": "number"
                                }
                              },
                              "required": [
                                "impressions",
                                "engagements",
                                "engagement_rate",
                                "clicks",
                                "clickthrough_rate"
                              ]
                            }
                          },
                          "required": [
                            "provider",
                            "id",
                            "social_id",
                            "share_url",
                            "text",
                            "date",
                            "parsed_datetime",
                            "reaction_counter",
                            "comment_counter",
                            "repost_counter",
                            "impressions_counter",
                            "author",
                            "permissions",
                            "is_repost",
                            "attachments"
                          ]
                        },
                        {
                          "type": "object",
                          "properties": {
                            "provider": {
                              "type": "string",
                              "enum": [
                                "INSTAGRAM"
                              ]
                            },
                            "provider_id": {
                              "type": "string"
                            },
                            "has_audio": {
                              "type": "boolean"
                            },
                            "has_liked": {
                              "type": "boolean"
                            },
                            "like_count": {
                              "type": "number"
                            },
                            "comment_count": {
                              "type": "number"
                            },
                            "like_and_view_counts_disabled": {
                              "type": "boolean"
                            },
                            "comments_disabled": {
                              "anyOf": [
                                {
                                  "type": "boolean"
                                },
                                {
                                  "nullable": true
                                }
                              ]
                            },
                            "accessibility_caption": {
                              "anyOf": [
                                {
                                  "type": "string"
                                },
                                {
                                  "nullable": true
                                }
                              ]
                            },
                            "caption": {
                              "type": "object",
                              "properties": {
                                "edited": {
                                  "type": "boolean"
                                },
                                "has_translation": {
                                  "type": "boolean"
                                },
                                "created_at": {
                                  "type": "number"
                                },
                                "text": {
                                  "type": "string"
                                }
                              },
                              "required": [
                                "edited",
                                "has_translation",
                                "created_at",
                                "text"
                              ]
                            },
                            "video": {
                              "type": "object",
                              "properties": {
                                "url": {
                                  "type": "string"
                                },
                                "width": {
                                  "type": "number"
                                },
                                "height": {
                                  "type": "number"
                                }
                              },
                              "required": [
                                "url",
                                "width",
                                "height"
                              ]
                            },
                            "preview_image": {
                              "type": "object",
                              "properties": {
                                "url": {
                                  "type": "string"
                                },
                                "width": {
                                  "type": "number"
                                },
                                "height": {
                                  "type": "number"
                                }
                              },
                              "required": [
                                "url",
                                "width",
                                "height"
                              ]
                            },
                            "owner": {
                              "type": "object",
                              "properties": {
                                "id": {
                                  "type": "string"
                                },
                                "username": {
                                  "type": "string"
                                },
                                "profile_pic_url": {
                                  "type": "string"
                                },
                                "is_verified": {
                                  "type": "boolean"
                                },
                                "is_private": {
                                  "type": "boolean"
                                }
                              },
                              "required": [
                                "id",
                                "username",
                                "profile_pic_url",
                                "is_verified",
                                "is_private"
                              ]
                            },
                            "location": {
                              "anyOf": [
                                {
                                  "type": "object",
                                  "properties": {
                                    "name": {
                                      "type": "string"
                                    },
                                    "lat": {
                                      "type": "number"
                                    },
                                    "lng": {
                                      "type": "number"
                                    }
                                  },
                                  "required": [
                                    "name",
                                    "lat",
                                    "lng"
                                  ]
                                },
                                {
                                  "nullable": true
                                }
                              ]
                            }
                          },
                          "required": [
                            "provider",
                            "provider_id",
                            "has_audio",
                            "has_liked",
                            "like_count",
                            "comment_count",
                            "like_and_view_counts_disabled",
                            "comments_disabled",
                            "accessibility_caption",
                            "preview_image",
                            "owner",
                            "location"
                          ]
                        }
                      ]
                    },
                    {
                      "type": "object",
                      "properties": {
                        "object": {
                          "type": "string",
                          "enum": [
                            "Post"
                          ]
                        }
                      },
                      "required": [
                        "object"
                      ]
                    }
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
          "Posts"
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
      "name": "Posts",
      "description": "Posts features"
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