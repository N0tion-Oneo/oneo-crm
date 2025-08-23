Retrieve a company profile

# OpenAPI definition
```json
{
  "openapi": "3.0.0",
  "paths": {
    "/api/v1/linkedin/company/{identifier}": {
      "get": {
        "operationId": "LinkedinController_getCompanyProfile",
        "summary": "Retrieve a company profile",
        "description": "Get a company profile from its name or ID.",
        "parameters": [
          {
            "name": "account_id",
            "required": true,
            "in": "query",
            "description": "The ID of the account to trigger the request from.",
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "identifier",
            "required": true,
            "in": "path",
            "description": "The identifier of the company: either the public identifier, the ID or the URN.",
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
                  "type": "object",
                  "properties": {
                    "object": {
                      "type": "string",
                      "enum": [
                        "CompanyProfile"
                      ]
                    },
                    "id": {
                      "type": "string"
                    },
                    "name": {
                      "type": "string"
                    },
                    "description": {
                      "type": "string"
                    },
                    "entity_urn": {
                      "type": "string"
                    },
                    "public_identifier": {
                      "type": "string"
                    },
                    "profile_url": {
                      "type": "string"
                    },
                    "tagline": {
                      "type": "string"
                    },
                    "followers_count": {
                      "type": "number"
                    },
                    "is_following": {
                      "type": "boolean"
                    },
                    "is_employee": {
                      "type": "boolean"
                    },
                    "hashtags": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "title": {
                            "type": "string"
                          }
                        },
                        "required": [
                          "title"
                        ]
                      }
                    },
                    "messaging": {
                      "type": "object",
                      "properties": {
                        "is_enabled": {
                          "type": "boolean"
                        },
                        "id": {
                          "type": "string"
                        },
                        "entity_urn": {
                          "type": "string"
                        }
                      },
                      "required": [
                        "is_enabled"
                      ]
                    },
                    "claimed": {
                      "type": "boolean"
                    },
                    "viewer_permissions": {
                      "type": "object",
                      "properties": {
                        "canMembersInviteToFollow": {
                          "type": "boolean"
                        },
                        "canReadContentSuggestions": {
                          "type": "boolean"
                        },
                        "canReadMessages": {
                          "type": "boolean"
                        },
                        "canUpdateOrganizationProfile": {
                          "type": "boolean"
                        },
                        "canCreateOrganicShare": {
                          "type": "boolean"
                        },
                        "canReadAdminDashboard": {
                          "type": "boolean"
                        },
                        "canReadOrganizationActivity": {
                          "type": "boolean"
                        },
                        "canEditCurators": {
                          "type": "boolean"
                        },
                        "canManageOrganizationalPageFollow": {
                          "type": "boolean"
                        },
                        "canReadOrganizationFollowerAnalytics": {
                          "type": "boolean"
                        },
                        "canInviteMemberToFollow": {
                          "type": "boolean"
                        },
                        "canReadOrganizationLeadsAnalytics": {
                          "type": "boolean"
                        },
                        "canEditPendingAdministrators": {
                          "type": "boolean"
                        },
                        "canManageMessagingAccess": {
                          "type": "boolean"
                        },
                        "canSeeEmployeeExperienceAsMember": {
                          "type": "boolean"
                        },
                        "canEmployeesInviteToFollow": {
                          "type": "boolean"
                        },
                        "canSeeOrganizationAdministrativePage": {
                          "type": "boolean"
                        },
                        "canManageAdminRoles": {
                          "type": "boolean"
                        },
                        "canEditOrganizationDetails": {
                          "type": "boolean"
                        },
                        "canApproveContent": {
                          "type": "boolean"
                        },
                        "canViewTeamPerformance": {
                          "type": "boolean"
                        },
                        "canManageOrganizationSettings": {
                          "type": "boolean"
                        },
                        "canAccessAdvancedAnalytics": {
                          "type": "boolean"
                        },
                        "canModerateComments": {
                          "type": "boolean"
                        },
                        "canCreateAds": {
                          "type": "boolean"
                        },
                        "canManageAdBudgets": {
                          "type": "boolean"
                        },
                        "canEditPageTheme": {
                          "type": "boolean"
                        },
                        "canPublishNewsletters": {
                          "type": "boolean"
                        },
                        "canEditCustomTabs": {
                          "type": "boolean"
                        },
                        "canManageIntegrations": {
                          "type": "boolean"
                        },
                        "canAssignRoles": {
                          "type": "boolean"
                        },
                        "canApprovePendingMembers": {
                          "type": "boolean"
                        },
                        "canEditCareerPageSettings": {
                          "type": "boolean"
                        },
                        "canViewBillingInformation": {
                          "type": "boolean"
                        }
                      },
                      "required": [
                        "canMembersInviteToFollow",
                        "canReadContentSuggestions",
                        "canReadMessages",
                        "canUpdateOrganizationProfile",
                        "canCreateOrganicShare",
                        "canReadAdminDashboard",
                        "canReadOrganizationActivity",
                        "canEditCurators",
                        "canManageOrganizationalPageFollow",
                        "canReadOrganizationFollowerAnalytics",
                        "canInviteMemberToFollow",
                        "canReadOrganizationLeadsAnalytics",
                        "canEditPendingAdministrators",
                        "canManageMessagingAccess",
                        "canSeeEmployeeExperienceAsMember",
                        "canEmployeesInviteToFollow",
                        "canSeeOrganizationAdministrativePage",
                        "canManageAdminRoles",
                        "canEditOrganizationDetails",
                        "canApproveContent",
                        "canViewTeamPerformance",
                        "canManageOrganizationSettings",
                        "canAccessAdvancedAnalytics",
                        "canModerateComments",
                        "canCreateAds",
                        "canManageAdBudgets",
                        "canEditPageTheme",
                        "canPublishNewsletters",
                        "canEditCustomTabs",
                        "canManageIntegrations",
                        "canAssignRoles",
                        "canApprovePendingMembers",
                        "canEditCareerPageSettings",
                        "canViewBillingInformation"
                      ]
                    },
                    "organization_type": {
                      "anyOf": [
                        {
                          "type": "string",
                          "enum": [
                            "PUBLIC_COMPANY"
                          ]
                        },
                        {
                          "type": "string",
                          "enum": [
                            "EDUCATIONAL"
                          ]
                        },
                        {
                          "type": "string",
                          "enum": [
                            "SELF_EMPLOYED"
                          ]
                        },
                        {
                          "type": "string",
                          "enum": [
                            "GOVERNMENT_AGENCY"
                          ]
                        },
                        {
                          "type": "string",
                          "enum": [
                            "NON_PROFIT"
                          ]
                        },
                        {
                          "type": "string",
                          "enum": [
                            "SELF_OWNED"
                          ]
                        },
                        {
                          "type": "string",
                          "enum": [
                            "PRIVATELY_HELD"
                          ]
                        },
                        {
                          "type": "string",
                          "enum": [
                            "PARTNERSHIP"
                          ]
                        },
                        {
                          "nullable": true
                        }
                      ]
                    },
                    "locations": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "is_headquarter": {
                            "type": "boolean"
                          },
                          "country": {
                            "type": "string"
                          },
                          "city": {
                            "type": "string"
                          },
                          "postalCode": {
                            "type": "string"
                          },
                          "street": {
                            "type": "array",
                            "items": {
                              "type": "string"
                            }
                          },
                          "description": {
                            "type": "string"
                          },
                          "area": {
                            "type": "string"
                          }
                        },
                        "required": [
                          "is_headquarter",
                          "country",
                          "city",
                          "street"
                        ]
                      }
                    },
                    "logo": {
                      "type": "string"
                    },
                    "localized_description": {
                      "type": "array",
                      "items": {
                        "description": "In this localized object, the key corresponds to the locale of the value e.g. fr_FR, en_US...",
                        "type": "object",
                        "x-patternProperties": {
                          "^(.*)$": {
                            "type": "string"
                          }
                        },
                        "additionalProperties": true
                      }
                    },
                    "localized_name": {
                      "type": "array",
                      "items": {
                        "description": "In this localized object, the key corresponds to the locale of the value e.g. fr_FR, en_US...",
                        "type": "object",
                        "x-patternProperties": {
                          "^(.*)$": {
                            "type": "string"
                          }
                        },
                        "additionalProperties": true
                      }
                    },
                    "localized_tagline": {
                      "type": "array",
                      "items": {
                        "description": "In this localized object, the key corresponds to the locale of the value e.g. fr_FR, en_US...",
                        "type": "object",
                        "x-patternProperties": {
                          "^(.*)$": {
                            "type": "string"
                          }
                        },
                        "additionalProperties": true
                      }
                    },
                    "industry": {
                      "type": "array",
                      "items": {
                        "type": "string"
                      }
                    },
                    "activities": {
                      "type": "array",
                      "items": {
                        "type": "string"
                      }
                    },
                    "employee_count": {
                      "type": "number"
                    },
                    "employee_count_range": {
                      "type": "object",
                      "properties": {
                        "from": {
                          "type": "number"
                        },
                        "to": {
                          "type": "number"
                        }
                      },
                      "required": [
                        "from",
                        "to"
                      ]
                    },
                    "website": {
                      "type": "string"
                    },
                    "foundation_date": {
                      "type": "string"
                    },
                    "phone": {
                      "type": "string"
                    },
                    "insights": {
                      "type": "object",
                      "properties": {
                        "employeesCount": {
                          "type": "object",
                          "properties": {
                            "totalCount": {
                              "type": "number"
                            },
                            "averageTenure": {
                              "type": "string"
                            },
                            "employeesCountGraph": {
                              "type": "array",
                              "items": {
                                "type": "object",
                                "properties": {
                                  "date": {
                                    "type": "string"
                                  },
                                  "count": {
                                    "type": "number"
                                  }
                                },
                                "required": [
                                  "date",
                                  "count"
                                ]
                              }
                            },
                            "growthGraph": {
                              "type": "array",
                              "items": {
                                "type": "object",
                                "properties": {
                                  "monthRange": {
                                    "type": "number"
                                  },
                                  "growthPercentage": {
                                    "type": "number"
                                  }
                                },
                                "required": [
                                  "monthRange",
                                  "growthPercentage"
                                ]
                              }
                            }
                          },
                          "required": [
                            "totalCount",
                            "averageTenure",
                            "employeesCountGraph",
                            "growthGraph"
                          ]
                        }
                      }
                    },
                    "acquired_by": {
                      "type": "object",
                      "properties": {
                        "id": {
                          "type": "string"
                        },
                        "name": {
                          "type": "string"
                        },
                        "public_identifier": {
                          "type": "string"
                        },
                        "profile_url": {
                          "type": "string"
                        }
                      },
                      "required": [
                        "id",
                        "name",
                        "public_identifier",
                        "profile_url"
                      ]
                    },
                    "crunchbase_funding": {
                      "type": "object",
                      "properties": {
                        "last_updated_at": {
                          "type": "string"
                        },
                        "company_url": {
                          "type": "string"
                        },
                        "rounds": {
                          "type": "object",
                          "properties": {
                            "url": {
                              "type": "string"
                            },
                            "total_count": {
                              "type": "number"
                            },
                            "last_round": {
                              "type": "object",
                              "properties": {
                                "announced_on": {
                                  "type": "string"
                                },
                                "url": {
                                  "type": "string"
                                },
                                "funding_type": {
                                  "type": "string"
                                },
                                "investors_count": {
                                  "type": "number"
                                },
                                "lead_investors": {
                                  "type": "array",
                                  "items": {
                                    "type": "object",
                                    "properties": {
                                      "name": {
                                        "type": "string"
                                      },
                                      "url": {
                                        "type": "string"
                                      },
                                      "logo": {
                                        "type": "string"
                                      }
                                    },
                                    "required": [
                                      "name",
                                      "url"
                                    ]
                                  }
                                },
                                "money_raised": {
                                  "type": "object",
                                  "properties": {
                                    "amount": {
                                      "type": "number"
                                    },
                                    "currency": {
                                      "type": "string"
                                    }
                                  },
                                  "required": [
                                    "amount",
                                    "currency"
                                  ]
                                }
                              },
                              "required": [
                                "announced_on",
                                "url",
                                "funding_type",
                                "investors_count",
                                "lead_investors"
                              ]
                            }
                          },
                          "required": [
                            "url",
                            "total_count",
                            "last_round"
                          ]
                        }
                      },
                      "required": [
                        "last_updated_at",
                        "company_url",
                        "rounds"
                      ]
                    }
                  },
                  "required": [
                    "object",
                    "id",
                    "name",
                    "description",
                    "entity_urn",
                    "public_identifier",
                    "profile_url",
                    "hashtags",
                    "messaging",
                    "claimed",
                    "viewer_permissions",
                    "organization_type",
                    "locations"
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
            "description": "\n        ## Not Found\n        ### Resource not found.\n        The requested resource were not found.\nCompany not found",
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