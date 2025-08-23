Edit own profile

# OpenAPI definition
```json
{
  "openapi": "3.0.0",
  "paths": {
    "/api/v1/users/me/edit": {
      "patch": {
        "operationId": "UsersController_editAccountOwnerProfile",
        "x-readme": {
          "code-samples": [
            {
              "language": "node",
              "code": "import { UnipileClient } from \"unipile-node-sdk\"\n\n// SDK setup\nconst BASE_URL = \"your base url\"\nconst ACCESS_TOKEN = \"your access token\"\n// Inputs\nconst account_id = \"account id\"\n\ntry {\n\tconst client = new UnipileClient(BASE_URL, ACCESS_TOKEN)\n\n\tconst response = await client.users.getOwnProfile(account_id)\n} catch (error) {\n\tconsole.log(error)\n}\n",
              "name": "unipile-node-sdk",
              "install": "npm install unipile-node-sdk"
            }
          ]
        },
        "summary": "Edit own profile",
        "description": "Modify informations on account owner profile.\n⚠️ Interactive documentation does not provide the expected format for nested parameters in code snippet. They should be formatted with brackets like the following examples : `location[id]=105015875`, `picture_settings[filter]=STUDIO` or `picture_settings[layout][bottomLeft][x]=1.25`.\nWhen working with arrays, just set one field for each value with the same key, for example : `experience[skills]=development \\ experience[skills]=management`.",
        "parameters": [],
        "requestBody": {
          "required": true,
          "content": {
            "multipart/form-data": {
              "schema": {
                "type": "object",
                "properties": {
                  "type": {
                    "type": "string",
                    "enum": [
                      "LINKEDIN"
                    ]
                  },
                  "account_id": {
                    "title": "AccountIdParam",
                    "description": "An Unipile account id.",
                    "minLength": 1,
                    "type": "string"
                  },
                  "location": {
                    "type": "object",
                    "properties": {
                      "id": {
                        "description": "The ID of the location. Use the <strong>Retrieve LinkedIn search parameters</strong> route with type LOCATION to find the right one : https://developer.unipile.com/reference/linkedincontroller_getsearchparameterslist",
                        "type": "string"
                      },
                      "postal_code": {
                        "description": "A 5 digits postal code.",
                        "minLength": 5,
                        "maxLength": 5,
                        "type": "string"
                      }
                    },
                    "required": [
                      "id"
                    ]
                  },
                  "headline": {
                    "description": "The subtitle of your profile.",
                    "type": "string"
                  },
                  "summary": {
                    "description": "The ABOUT section of your profile.",
                    "type": "string"
                  },
                  "picture": {
                    "format": "binary",
                    "type": "string"
                  },
                  "picture_settings": {
                    "type": "object",
                    "properties": {
                      "filter": {
                        "type": "string",
                        "enum": [
                          "ORIGINAL",
                          "STUDIO",
                          "SPOTLIGHT",
                          "PRIME",
                          "CLASSIC",
                          "EDGE",
                          "LUMINATE"
                        ]
                      },
                      "layout": {
                        "type": "object",
                        "properties": {
                          "bottomLeft": {
                            "type": "object",
                            "properties": {
                              "x": {
                                "type": "number"
                              },
                              "y": {
                                "type": "number"
                              }
                            },
                            "required": [
                              "x",
                              "y"
                            ]
                          },
                          "bottomRight": {
                            "type": "object",
                            "properties": {
                              "x": {
                                "type": "number"
                              },
                              "y": {
                                "type": "number"
                              }
                            },
                            "required": [
                              "x",
                              "y"
                            ]
                          },
                          "topLeft": {
                            "type": "object",
                            "properties": {
                              "x": {
                                "type": "number"
                              },
                              "y": {
                                "type": "number"
                              }
                            },
                            "required": [
                              "x",
                              "y"
                            ]
                          },
                          "topRight": {
                            "type": "object",
                            "properties": {
                              "x": {
                                "type": "number"
                              },
                              "y": {
                                "type": "number"
                              }
                            },
                            "required": [
                              "x",
                              "y"
                            ]
                          }
                        }
                      },
                      "contrast": {
                        "type": "number"
                      },
                      "vignette": {
                        "type": "number"
                      },
                      "saturation": {
                        "type": "number"
                      },
                      "brightness": {
                        "type": "number"
                      }
                    }
                  },
                  "cover_picture": {
                    "format": "binary",
                    "type": "string"
                  },
                  "cover_picture_settings": {
                    "type": "object",
                    "properties": {
                      "filter": {
                        "type": "string",
                        "enum": [
                          "ORIGINAL",
                          "STUDIO",
                          "SPOTLIGHT",
                          "PRIME",
                          "CLASSIC",
                          "EDGE",
                          "LUMINATE"
                        ]
                      },
                      "layout": {
                        "type": "object",
                        "properties": {
                          "bottomLeft": {
                            "type": "object",
                            "properties": {
                              "x": {
                                "type": "number"
                              },
                              "y": {
                                "type": "number"
                              }
                            },
                            "required": [
                              "x",
                              "y"
                            ]
                          },
                          "bottomRight": {
                            "type": "object",
                            "properties": {
                              "x": {
                                "type": "number"
                              },
                              "y": {
                                "type": "number"
                              }
                            },
                            "required": [
                              "x",
                              "y"
                            ]
                          },
                          "topLeft": {
                            "type": "object",
                            "properties": {
                              "x": {
                                "type": "number"
                              },
                              "y": {
                                "type": "number"
                              }
                            },
                            "required": [
                              "x",
                              "y"
                            ]
                          },
                          "topRight": {
                            "type": "object",
                            "properties": {
                              "x": {
                                "type": "number"
                              },
                              "y": {
                                "type": "number"
                              }
                            },
                            "required": [
                              "x",
                              "y"
                            ]
                          }
                        }
                      },
                      "contrast": {
                        "type": "number"
                      },
                      "vignette": {
                        "type": "number"
                      },
                      "saturation": {
                        "type": "number"
                      },
                      "brightness": {
                        "type": "number"
                      }
                    }
                  },
                  "experience": {
                    "description": "Add or edit a professional experience.",
                    "anyOf": [
                      {
                        "title": "Add a new experience",
                        "type": "object",
                        "properties": {
                          "notify_network": {
                            "type": "boolean"
                          },
                          "role": {
                            "type": "string"
                          },
                          "employment_type": {
                            "description": "The ID of the type. Use the <strong>Retrieve LinkedIn search parameters</strong> route with type EMPLOYMENT_TYPE to find the right one : https://developer.unipile.com/reference/linkedincontroller_getsearchparameterslist.",
                            "type": "string"
                          },
                          "company": {
                            "type": "string"
                          },
                          "location": {
                            "type": "string"
                          },
                          "presence": {
                            "type": "string",
                            "enum": [
                              "ON_SITE",
                              "HYBRID",
                              "REMOTE"
                            ]
                          },
                          "seniority": {
                            "type": "object",
                            "properties": {
                              "start_date": {
                                "type": "object",
                                "properties": {
                                  "month": {
                                    "type": "number"
                                  },
                                  "year": {
                                    "type": "number"
                                  }
                                },
                                "required": [
                                  "month",
                                  "year"
                                ]
                              },
                              "end_date": {
                                "type": "object",
                                "properties": {
                                  "month": {
                                    "type": "number"
                                  },
                                  "year": {
                                    "type": "number"
                                  }
                                },
                                "required": [
                                  "month",
                                  "year"
                                ]
                              }
                            },
                            "required": [
                              "start_date"
                            ]
                          },
                          "description": {
                            "type": "string"
                          },
                          "source_of_hire": {
                            "type": "string",
                            "enum": [
                              "INDEED",
                              "LINKEDIN",
                              "COMPANY_WEBSITE",
                              "OTHER_JOB_SITES",
                              "REFERRAL",
                              "CONTACTED_BY_RECRUITER",
                              "STAFFING_AGENCY",
                              "OTHER"
                            ]
                          },
                          "skills": {
                            "type": "array",
                            "items": {
                              "type": "string"
                            }
                          },
                          "attachment": {
                            "anyOf": [
                              {
                                "title": "Link",
                                "type": "object",
                                "properties": {
                                  "type": {
                                    "type": "string",
                                    "enum": [
                                      "link"
                                    ]
                                  },
                                  "title": {
                                    "type": "string"
                                  },
                                  "description": {
                                    "type": "string"
                                  },
                                  "url": {
                                    "type": "string"
                                  },
                                  "thumbnail": {
                                    "format": "binary",
                                    "description": "A replacement image if the default thumbnail is not satisfactory.",
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "type",
                                  "title",
                                  "url"
                                ]
                              },
                              {
                                "title": "Media",
                                "type": "object",
                                "properties": {
                                  "type": {
                                    "type": "string",
                                    "enum": [
                                      "media"
                                    ]
                                  },
                                  "title": {
                                    "type": "string"
                                  },
                                  "description": {
                                    "type": "string"
                                  },
                                  "file": {
                                    "format": "binary",
                                    "description": "Should be an image or a document (pdf, ppt, doc).",
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "type",
                                  "title"
                                ]
                              }
                            ]
                          }
                        },
                        "required": [
                          "role",
                          "company"
                        ]
                      },
                      {
                        "title": "Edit an existing experience.",
                        "type": "object",
                        "properties": {
                          "id": {
                            "description": "This ID of the experience to be edited.",
                            "type": "string"
                          },
                          "notify_network": {
                            "type": "boolean"
                          },
                          "role": {
                            "type": "string"
                          },
                          "employment_type": {
                            "description": "The ID of the type. Use the <strong>Retrieve LinkedIn search parameters</strong> route with type EMPLOYMENT_TYPE to find the right one : https://developer.unipile.com/reference/linkedincontroller_getsearchparameterslist.",
                            "type": "string"
                          },
                          "company": {
                            "type": "string"
                          },
                          "location": {
                            "type": "string"
                          },
                          "presence": {
                            "type": "string",
                            "enum": [
                              "ON_SITE",
                              "HYBRID",
                              "REMOTE"
                            ]
                          },
                          "seniority": {
                            "type": "object",
                            "properties": {
                              "start_date": {
                                "type": "object",
                                "properties": {
                                  "month": {
                                    "type": "number"
                                  },
                                  "year": {
                                    "type": "number"
                                  }
                                },
                                "required": [
                                  "month",
                                  "year"
                                ]
                              },
                              "end_date": {
                                "type": "object",
                                "properties": {
                                  "month": {
                                    "type": "number"
                                  },
                                  "year": {
                                    "type": "number"
                                  }
                                },
                                "required": [
                                  "month",
                                  "year"
                                ]
                              }
                            },
                            "required": [
                              "start_date"
                            ]
                          },
                          "description": {
                            "type": "string"
                          },
                          "source_of_hire": {
                            "type": "string",
                            "enum": [
                              "INDEED",
                              "LINKEDIN",
                              "COMPANY_WEBSITE",
                              "OTHER_JOB_SITES",
                              "REFERRAL",
                              "CONTACTED_BY_RECRUITER",
                              "STAFFING_AGENCY",
                              "OTHER"
                            ]
                          },
                          "skills": {
                            "type": "array",
                            "items": {
                              "type": "string"
                            }
                          },
                          "attachment": {
                            "anyOf": [
                              {
                                "title": "Link",
                                "type": "object",
                                "properties": {
                                  "type": {
                                    "type": "string",
                                    "enum": [
                                      "link"
                                    ]
                                  },
                                  "title": {
                                    "type": "string"
                                  },
                                  "description": {
                                    "type": "string"
                                  },
                                  "url": {
                                    "type": "string"
                                  },
                                  "thumbnail": {
                                    "format": "binary",
                                    "description": "A replacement image if the default thumbnail is not satisfactory.",
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "type",
                                  "title",
                                  "url"
                                ]
                              },
                              {
                                "title": "Media",
                                "type": "object",
                                "properties": {
                                  "type": {
                                    "type": "string",
                                    "enum": [
                                      "media"
                                    ]
                                  },
                                  "title": {
                                    "type": "string"
                                  },
                                  "description": {
                                    "type": "string"
                                  },
                                  "file": {
                                    "format": "binary",
                                    "description": "Should be an image or a document (pdf, ppt, doc).",
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "type",
                                  "title"
                                ]
                              }
                            ]
                          }
                        },
                        "required": [
                          "id"
                        ]
                      }
                    ]
                  },
                  "education": {
                    "description": "Add or edit an education.",
                    "anyOf": [
                      {
                        "title": "Add a new education",
                        "type": "object",
                        "properties": {
                          "notify_network": {
                            "type": "boolean"
                          },
                          "school": {
                            "type": "string"
                          },
                          "degree": {
                            "type": "string"
                          },
                          "grade": {
                            "type": "string"
                          },
                          "field_of_study": {
                            "type": "string"
                          },
                          "activities": {
                            "type": "string"
                          },
                          "description": {
                            "type": "string"
                          },
                          "start_date": {
                            "type": "object",
                            "properties": {
                              "month": {
                                "type": "number"
                              },
                              "year": {
                                "type": "number"
                              }
                            },
                            "required": [
                              "month",
                              "year"
                            ]
                          },
                          "end_date": {
                            "type": "object",
                            "properties": {
                              "month": {
                                "type": "number"
                              },
                              "year": {
                                "type": "number"
                              }
                            },
                            "required": [
                              "month",
                              "year"
                            ]
                          },
                          "skills": {
                            "type": "array",
                            "items": {
                              "type": "string"
                            }
                          },
                          "attachment": {
                            "anyOf": [
                              {
                                "title": "Link",
                                "type": "object",
                                "properties": {
                                  "type": {
                                    "type": "string",
                                    "enum": [
                                      "link"
                                    ]
                                  },
                                  "title": {
                                    "type": "string"
                                  },
                                  "description": {
                                    "type": "string"
                                  },
                                  "url": {
                                    "type": "string"
                                  },
                                  "thumbnail": {
                                    "format": "binary",
                                    "description": "A replacement image if the default thumbnail is not satisfactory.",
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "type",
                                  "title",
                                  "url"
                                ]
                              },
                              {
                                "title": "Media",
                                "type": "object",
                                "properties": {
                                  "type": {
                                    "type": "string",
                                    "enum": [
                                      "media"
                                    ]
                                  },
                                  "title": {
                                    "type": "string"
                                  },
                                  "description": {
                                    "type": "string"
                                  },
                                  "file": {
                                    "format": "binary",
                                    "description": "Should be an image or a document (pdf, ppt, doc).",
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "type",
                                  "title"
                                ]
                              }
                            ]
                          }
                        },
                        "required": [
                          "school"
                        ]
                      },
                      {
                        "title": "Edit an existing education.",
                        "type": "object",
                        "properties": {
                          "id": {
                            "description": "This ID of the experience to be edited.",
                            "type": "string"
                          },
                          "notify_network": {
                            "type": "boolean"
                          },
                          "role": {
                            "type": "string"
                          },
                          "employment_type": {
                            "description": "The ID of the type. Use the <strong>Retrieve LinkedIn search parameters</strong> route with type EMPLOYMENT_TYPE to find the right one : https://developer.unipile.com/reference/linkedincontroller_getsearchparameterslist.",
                            "type": "string"
                          },
                          "company": {
                            "type": "string"
                          },
                          "location": {
                            "type": "string"
                          },
                          "presence": {
                            "type": "string",
                            "enum": [
                              "ON_SITE",
                              "HYBRID",
                              "REMOTE"
                            ]
                          },
                          "seniority": {
                            "type": "object",
                            "properties": {
                              "start_date": {
                                "type": "object",
                                "properties": {
                                  "month": {
                                    "type": "number"
                                  },
                                  "year": {
                                    "type": "number"
                                  }
                                },
                                "required": [
                                  "month",
                                  "year"
                                ]
                              },
                              "end_date": {
                                "type": "object",
                                "properties": {
                                  "month": {
                                    "type": "number"
                                  },
                                  "year": {
                                    "type": "number"
                                  }
                                },
                                "required": [
                                  "month",
                                  "year"
                                ]
                              }
                            },
                            "required": [
                              "start_date"
                            ]
                          },
                          "description": {
                            "type": "string"
                          },
                          "source_of_hire": {
                            "type": "string",
                            "enum": [
                              "INDEED",
                              "LINKEDIN",
                              "COMPANY_WEBSITE",
                              "OTHER_JOB_SITES",
                              "REFERRAL",
                              "CONTACTED_BY_RECRUITER",
                              "STAFFING_AGENCY",
                              "OTHER"
                            ]
                          },
                          "skills": {
                            "type": "array",
                            "items": {
                              "type": "string"
                            }
                          },
                          "attachment": {
                            "anyOf": [
                              {
                                "title": "Link",
                                "type": "object",
                                "properties": {
                                  "type": {
                                    "type": "string",
                                    "enum": [
                                      "link"
                                    ]
                                  },
                                  "title": {
                                    "type": "string"
                                  },
                                  "description": {
                                    "type": "string"
                                  },
                                  "url": {
                                    "type": "string"
                                  },
                                  "thumbnail": {
                                    "format": "binary",
                                    "description": "A replacement image if the default thumbnail is not satisfactory.",
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "type",
                                  "title",
                                  "url"
                                ]
                              },
                              {
                                "title": "Media",
                                "type": "object",
                                "properties": {
                                  "type": {
                                    "type": "string",
                                    "enum": [
                                      "media"
                                    ]
                                  },
                                  "title": {
                                    "type": "string"
                                  },
                                  "description": {
                                    "type": "string"
                                  },
                                  "file": {
                                    "format": "binary",
                                    "description": "Should be an image or a document (pdf, ppt, doc).",
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "type",
                                  "title"
                                ]
                              }
                            ]
                          }
                        },
                        "required": [
                          "id"
                        ]
                      }
                    ]
                  },
                  "skills": {
                    "type": "array",
                    "items": {
                      "type": "string"
                    }
                  },
                  "skills_follow": {
                    "type": "boolean"
                  }
                },
                "required": [
                  "type",
                  "account_id"
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
                        "ProfileEdited"
                      ]
                    }
                  },
                  "required": [
                    "object"
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
            "description": "\n## Not Found\n### Resource not found.\nThe requested resource were not found.\nUser not found",
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
          "Users"
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
      "name": "Users",
      "description": "Users features"
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