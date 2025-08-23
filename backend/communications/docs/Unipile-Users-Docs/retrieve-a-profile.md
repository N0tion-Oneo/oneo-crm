Retrieve a profile

# OpenAPI definition
```json
{
  "openapi": "3.0.0",
  "paths": {
    "/api/v1/users/{identifier}": {
      "get": {
        "operationId": "UsersController_getProfileByIdentifier",
        "x-readme": {
          "code-samples": [
            {
              "language": "node",
              "code": "import { UnipileClient } from \"unipile-node-sdk\"\n\n// SDK setup\nconst BASE_URL = \"your base url\"\nconst ACCESS_TOKEN = \"your access token\"\n// Inputs\nconst account_id = \"account id\"\nconst identifier = \"identifier\"\n\ntry {\n\tconst client = new UnipileClient(BASE_URL, ACCESS_TOKEN)\n\n\tconst response = await client.users.getProfile({\n\t\taccount_id,\n\t\tidentifier,\n\t})\n} catch (error) {\n\tconsole.log(error)\n}\n",
              "name": "unipile-node-sdk",
              "install": "npm install unipile-node-sdk"
            }
          ]
        },
        "summary": "Retrieve a profile",
        "description": "Retrieve the profile of a user. Ensure careful implementation of this action and consult provider limits and restrictions: https://developer.unipile.com/docs/provider-limits-and-restrictions",
        "parameters": [
          {
            "name": "linkedin_sections",
            "required": false,
            "in": "query",
            "description": "The sections that should be synchronized on Linkedin calls.",
            "schema": {
              "anyOf": [
                {
                  "description": "A string with a section name.",
                  "type": "string",
                  "enum": [
                    "experience",
                    "education",
                    "languages",
                    "skills",
                    "certifications",
                    "about",
                    "volunteering_experience",
                    "projects",
                    "recommendations_received",
                    "recommendations_given"
                  ]
                },
                {
                  "description": "A string with * character that stands for all sections.",
                  "type": "string",
                  "enum": [
                    "*"
                  ]
                },
                {
                  "description": "An array of section names.",
                  "type": "array",
                  "items": {
                    "description": "A string with a section name.",
                    "type": "string",
                    "enum": [
                      "experience",
                      "education",
                      "languages",
                      "skills",
                      "certifications",
                      "about",
                      "volunteering_experience",
                      "projects",
                      "recommendations_received",
                      "recommendations_given"
                    ]
                  }
                }
              ]
            }
          },
          {
            "name": "linkedin_api",
            "required": false,
            "in": "query",
            "description": "The LinkedIn API that should be used to get the profile (relative features must be subscribed), if different from classic.",
            "schema": {
              "enum": [
                "recruiter",
                "sales_navigator"
              ],
              "type": "string"
            }
          },
          {
            "name": "notify",
            "required": false,
            "in": "query",
            "description": "Whether the profile visit should be notified to the viewee or not. Default is false.",
            "schema": {
              "type": "boolean"
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
          },
          {
            "name": "identifier",
            "required": true,
            "in": "path",
            "description": "Can be the provider’s internal id OR the provider’s public id of the requested user.",
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
                  "anyOf": [
                    {
                      "title": "LinkedIn",
                      "type": "object",
                      "properties": {
                        "provider": {
                          "type": "string",
                          "enum": [
                            "LINKEDIN"
                          ]
                        },
                        "provider_id": {
                          "type": "string"
                        },
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
                        "first_name": {
                          "anyOf": [
                            {
                              "type": "string"
                            },
                            {
                              "nullable": true
                            }
                          ]
                        },
                        "last_name": {
                          "anyOf": [
                            {
                              "type": "string"
                            },
                            {
                              "nullable": true
                            }
                          ]
                        },
                        "headline": {
                          "type": "string"
                        },
                        "summary": {
                          "type": "string"
                        },
                        "contact_info": {
                          "type": "object",
                          "properties": {
                            "emails": {
                              "type": "array",
                              "items": {
                                "type": "string"
                              }
                            },
                            "phones": {
                              "type": "array",
                              "items": {
                                "type": "string"
                              }
                            },
                            "adresses": {
                              "type": "array",
                              "items": {
                                "type": "string"
                              }
                            },
                            "socials": {
                              "type": "array",
                              "items": {
                                "type": "object",
                                "properties": {
                                  "type": {
                                    "type": "string"
                                  },
                                  "name": {
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "type",
                                  "name"
                                ]
                              }
                            }
                          }
                        },
                        "birthdate": {
                          "type": "object",
                          "properties": {
                            "month": {
                              "type": "number"
                            },
                            "day": {
                              "type": "number"
                            }
                          },
                          "required": [
                            "month",
                            "day"
                          ]
                        },
                        "primary_locale": {
                          "type": "object",
                          "properties": {
                            "country": {
                              "type": "string"
                            },
                            "language": {
                              "type": "string"
                            }
                          },
                          "required": [
                            "country",
                            "language"
                          ]
                        },
                        "location": {
                          "type": "string"
                        },
                        "websites": {
                          "type": "array",
                          "items": {
                            "type": "string"
                          }
                        },
                        "profile_picture_url": {
                          "type": "string"
                        },
                        "profile_picture_url_large": {
                          "type": "string"
                        },
                        "background_picture_url": {
                          "type": "string"
                        },
                        "hashtags": {
                          "type": "array",
                          "items": {
                            "type": "string"
                          }
                        },
                        "can_send_inmail": {
                          "type": "boolean"
                        },
                        "is_open_profile": {
                          "type": "boolean"
                        },
                        "is_premium": {
                          "type": "boolean"
                        },
                        "is_influencer": {
                          "type": "boolean"
                        },
                        "is_creator": {
                          "type": "boolean"
                        },
                        "is_hiring": {
                          "type": "boolean"
                        },
                        "is_open_to_work": {
                          "type": "boolean"
                        },
                        "is_saved_lead": {
                          "type": "boolean"
                        },
                        "is_crm_imported": {
                          "type": "boolean"
                        },
                        "is_relationship": {
                          "type": "boolean"
                        },
                        "is_self": {
                          "type": "boolean"
                        },
                        "invitation": {
                          "type": "object",
                          "properties": {
                            "type": {
                              "anyOf": [
                                {
                                  "type": "string",
                                  "enum": [
                                    "SENT"
                                  ]
                                },
                                {
                                  "type": "string",
                                  "enum": [
                                    "RECEIVED"
                                  ]
                                }
                              ]
                            },
                            "status": {
                              "anyOf": [
                                {
                                  "type": "string",
                                  "enum": [
                                    "PENDING"
                                  ]
                                },
                                {
                                  "type": "string",
                                  "enum": [
                                    "IGNORED"
                                  ]
                                },
                                {
                                  "type": "string",
                                  "enum": [
                                    "WITHDRAWN"
                                  ]
                                }
                              ]
                            }
                          },
                          "required": [
                            "type",
                            "status"
                          ]
                        },
                        "work_experience": {
                          "type": "array",
                          "items": {
                            "type": "object",
                            "properties": {
                              "position": {
                                "type": "string"
                              },
                              "company_id": {
                                "type": "string"
                              },
                              "company": {
                                "type": "string"
                              },
                              "location": {
                                "type": "string"
                              },
                              "description": {
                                "type": "string"
                              },
                              "skills": {
                                "type": "array",
                                "items": {
                                  "type": "string"
                                }
                              },
                              "current": {
                                "type": "boolean"
                              },
                              "status": {
                                "type": "string"
                              },
                              "start": {
                                "anyOf": [
                                  {
                                    "type": "string"
                                  },
                                  {
                                    "nullable": true
                                  }
                                ]
                              },
                              "end": {
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
                              "position",
                              "company",
                              "skills",
                              "start",
                              "end"
                            ]
                          }
                        },
                        "volunteering_experience": {
                          "type": "array",
                          "items": {
                            "type": "object",
                            "properties": {
                              "company": {
                                "type": "string"
                              },
                              "description": {
                                "type": "string"
                              },
                              "role": {
                                "type": "string"
                              },
                              "cause": {
                                "type": "string"
                              },
                              "start": {
                                "anyOf": [
                                  {
                                    "type": "string"
                                  },
                                  {
                                    "nullable": true
                                  }
                                ]
                              },
                              "end": {
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
                              "company",
                              "description",
                              "role",
                              "cause",
                              "start",
                              "end"
                            ]
                          }
                        },
                        "education": {
                          "type": "array",
                          "items": {
                            "type": "object",
                            "properties": {
                              "degree": {
                                "type": "string"
                              },
                              "school": {
                                "type": "string"
                              },
                              "school_id": {
                                "type": "string"
                              },
                              "field_of_study": {
                                "type": "string"
                              },
                              "start": {
                                "anyOf": [
                                  {
                                    "type": "string"
                                  },
                                  {
                                    "nullable": true
                                  }
                                ]
                              },
                              "end": {
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
                              "school",
                              "start",
                              "end"
                            ]
                          }
                        },
                        "skills": {
                          "type": "array",
                          "items": {
                            "type": "object",
                            "properties": {
                              "name": {
                                "type": "string"
                              },
                              "endorsement_count": {
                                "type": "number"
                              },
                              "endorsement_id": {
                                "anyOf": [
                                  {
                                    "type": "number"
                                  },
                                  {
                                    "nullable": true
                                  }
                                ]
                              },
                              "insights": {
                                "type": "array",
                                "items": {
                                  "type": "string"
                                }
                              },
                              "endorsed": {
                                "type": "boolean"
                              }
                            },
                            "required": [
                              "name",
                              "endorsement_count",
                              "endorsement_id",
                              "insights",
                              "endorsed"
                            ]
                          }
                        },
                        "languages": {
                          "type": "array",
                          "items": {
                            "type": "object",
                            "properties": {
                              "name": {
                                "type": "string"
                              },
                              "proficiency": {
                                "type": "string"
                              }
                            },
                            "required": [
                              "name"
                            ]
                          }
                        },
                        "certifications": {
                          "type": "array",
                          "items": {
                            "type": "object",
                            "properties": {
                              "name": {
                                "type": "string"
                              },
                              "organization": {
                                "type": "string"
                              },
                              "url": {
                                "type": "string"
                              }
                            },
                            "required": [
                              "name",
                              "organization"
                            ]
                          }
                        },
                        "projects": {
                          "type": "array",
                          "items": {
                            "type": "object",
                            "properties": {
                              "name": {
                                "type": "string"
                              },
                              "description": {
                                "type": "string"
                              },
                              "skills": {
                                "type": "array",
                                "items": {
                                  "type": "string"
                                }
                              },
                              "start": {
                                "anyOf": [
                                  {
                                    "type": "string"
                                  },
                                  {
                                    "nullable": true
                                  }
                                ]
                              },
                              "end": {
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
                              "name",
                              "description",
                              "skills",
                              "start",
                              "end"
                            ]
                          }
                        },
                        "recommendations": {
                          "type": "object",
                          "properties": {
                            "received": {
                              "type": "array",
                              "items": {
                                "type": "object",
                                "properties": {
                                  "text": {
                                    "type": "string"
                                  },
                                  "caption": {
                                    "type": "string"
                                  },
                                  "actor": {
                                    "type": "object",
                                    "properties": {
                                      "first_name": {
                                        "type": "string"
                                      },
                                      "last_name": {
                                        "type": "string"
                                      },
                                      "provider_id": {
                                        "type": "string"
                                      },
                                      "headline": {
                                        "type": "string"
                                      },
                                      "public_identifier": {
                                        "type": "string"
                                      },
                                      "public_profile_url": {
                                        "type": "string"
                                      },
                                      "profile_picture_url": {
                                        "type": "string"
                                      }
                                    },
                                    "required": [
                                      "first_name",
                                      "last_name",
                                      "provider_id",
                                      "headline",
                                      "public_identifier",
                                      "public_profile_url"
                                    ]
                                  }
                                },
                                "required": [
                                  "text",
                                  "caption",
                                  "actor"
                                ]
                              }
                            },
                            "given": {
                              "type": "array",
                              "items": {
                                "type": "object",
                                "properties": {
                                  "text": {
                                    "type": "string"
                                  },
                                  "caption": {
                                    "type": "string"
                                  },
                                  "actor": {
                                    "type": "object",
                                    "properties": {
                                      "first_name": {
                                        "type": "string"
                                      },
                                      "last_name": {
                                        "type": "string"
                                      },
                                      "provider_id": {
                                        "type": "string"
                                      },
                                      "headline": {
                                        "type": "string"
                                      },
                                      "public_identifier": {
                                        "type": "string"
                                      },
                                      "public_profile_url": {
                                        "type": "string"
                                      },
                                      "profile_picture_url": {
                                        "type": "string"
                                      }
                                    },
                                    "required": [
                                      "first_name",
                                      "last_name",
                                      "provider_id",
                                      "headline",
                                      "public_identifier",
                                      "public_profile_url"
                                    ]
                                  }
                                },
                                "required": [
                                  "text",
                                  "caption",
                                  "actor"
                                ]
                              }
                            }
                          }
                        },
                        "follower_count": {
                          "type": "number"
                        },
                        "connections_count": {
                          "type": "number"
                        },
                        "shared_connections_count": {
                          "type": "number"
                        },
                        "network_distance": {
                          "anyOf": [
                            {
                              "type": "string",
                              "enum": [
                                "FIRST_DEGREE"
                              ]
                            },
                            {
                              "type": "string",
                              "enum": [
                                "SECOND_DEGREE"
                              ]
                            },
                            {
                              "type": "string",
                              "enum": [
                                "THIRD_DEGREE"
                              ]
                            },
                            {
                              "type": "string",
                              "enum": [
                                "OUT_OF_NETWORK"
                              ]
                            }
                          ]
                        },
                        "public_profile_url": {
                          "type": "string"
                        },
                        "object": {
                          "type": "string",
                          "enum": [
                            "UserProfile"
                          ]
                        }
                      },
                      "required": [
                        "provider",
                        "provider_id",
                        "public_identifier",
                        "first_name",
                        "last_name",
                        "headline",
                        "websites",
                        "object"
                      ]
                    },
                    {
                      "title": "Whatsapp",
                      "type": "object",
                      "properties": {
                        "provider": {
                          "type": "string",
                          "enum": [
                            "WHATSAPP"
                          ]
                        },
                        "id": {
                          "type": "string"
                        },
                        "object": {
                          "type": "string",
                          "enum": [
                            "UserProfile"
                          ]
                        }
                      },
                      "required": [
                        "provider",
                        "id",
                        "object"
                      ]
                    },
                    {
                      "title": "Instagram",
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
                        "provider_messaging_id": {
                          "type": "string"
                        },
                        "public_identifier": {
                          "type": "string"
                        },
                        "full_name": {
                          "type": "string"
                        },
                        "profile_picture_url": {
                          "type": "string"
                        },
                        "profile_picture_url_large": {
                          "type": "string"
                        },
                        "biography": {
                          "type": "string"
                        },
                        "category": {
                          "type": "string"
                        },
                        "followers_count": {
                          "type": "number"
                        },
                        "mutual_followers_count": {
                          "type": "number"
                        },
                        "following_count": {
                          "type": "number"
                        },
                        "posts_count": {
                          "type": "number"
                        },
                        "profile_type": {
                          "anyOf": [
                            {
                              "type": "string",
                              "enum": [
                                "PERSONNAL"
                              ]
                            },
                            {
                              "type": "string",
                              "enum": [
                                "BUSINESS"
                              ]
                            },
                            {
                              "type": "string",
                              "enum": [
                                "PROFESSIONNAL"
                              ]
                            }
                          ]
                        },
                        "is_verified": {
                          "type": "boolean"
                        },
                        "is_private": {
                          "type": "boolean"
                        },
                        "external_links": {
                          "type": "array",
                          "items": {
                            "type": "string"
                          }
                        },
                        "relationship_status": {
                          "type": "object",
                          "properties": {
                            "following": {
                              "type": "boolean"
                            },
                            "followed_by": {
                              "type": "boolean"
                            },
                            "has_sent_invitation": {
                              "type": "boolean"
                            },
                            "has_received_invitation": {
                              "type": "boolean"
                            }
                          },
                          "required": [
                            "following",
                            "followed_by",
                            "has_sent_invitation",
                            "has_received_invitation"
                          ]
                        },
                        "business": {
                          "type": "object",
                          "properties": {
                            "category": {
                              "anyOf": [
                                {
                                  "type": "string"
                                },
                                {
                                  "nullable": true
                                }
                              ]
                            },
                            "address_street": {
                              "anyOf": [
                                {
                                  "type": "string"
                                },
                                {
                                  "nullable": true
                                }
                              ]
                            },
                            "address_city": {
                              "anyOf": [
                                {
                                  "type": "string"
                                },
                                {
                                  "nullable": true
                                }
                              ]
                            },
                            "address_zipcode": {
                              "anyOf": [
                                {
                                  "type": "string"
                                },
                                {
                                  "nullable": true
                                }
                              ]
                            },
                            "phone_number": {
                              "anyOf": [
                                {
                                  "type": "string"
                                },
                                {
                                  "nullable": true
                                }
                              ]
                            },
                            "email": {
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
                            "category",
                            "address_street",
                            "address_city",
                            "address_zipcode",
                            "phone_number",
                            "email"
                          ]
                        },
                        "object": {
                          "type": "string",
                          "enum": [
                            "UserProfile"
                          ]
                        }
                      },
                      "required": [
                        "provider",
                        "provider_id",
                        "public_identifier",
                        "full_name",
                        "followers_count",
                        "mutual_followers_count",
                        "following_count",
                        "posts_count",
                        "profile_type",
                        "is_verified",
                        "is_private",
                        "external_links",
                        "relationship_status",
                        "object"
                      ]
                    },
                    {
                      "title": "Telegram",
                      "type": "object",
                      "properties": {
                        "provider": {
                          "type": "string",
                          "enum": [
                            "TELEGRAM"
                          ]
                        },
                        "provider_id": {
                          "type": "string"
                        },
                        "self": {
                          "anyOf": [
                            {
                              "type": "boolean"
                            },
                            {
                              "nullable": true
                            }
                          ]
                        },
                        "contact": {
                          "anyOf": [
                            {
                              "type": "boolean"
                            },
                            {
                              "nullable": true
                            }
                          ]
                        },
                        "mutual_contact": {
                          "anyOf": [
                            {
                              "type": "boolean"
                            },
                            {
                              "nullable": true
                            }
                          ]
                        },
                        "deleted": {
                          "anyOf": [
                            {
                              "type": "boolean"
                            },
                            {
                              "nullable": true
                            }
                          ]
                        },
                        "bot": {
                          "anyOf": [
                            {
                              "type": "boolean"
                            },
                            {
                              "nullable": true
                            }
                          ]
                        },
                        "verified": {
                          "anyOf": [
                            {
                              "type": "boolean"
                            },
                            {
                              "nullable": true
                            }
                          ]
                        },
                        "restricted": {
                          "anyOf": [
                            {
                              "type": "boolean"
                            },
                            {
                              "nullable": true
                            }
                          ]
                        },
                        "fake": {
                          "anyOf": [
                            {
                              "type": "boolean"
                            },
                            {
                              "nullable": true
                            }
                          ]
                        },
                        "premium": {
                          "anyOf": [
                            {
                              "type": "boolean"
                            },
                            {
                              "nullable": true
                            }
                          ]
                        },
                        "close_friend": {
                          "anyOf": [
                            {
                              "type": "boolean"
                            },
                            {
                              "nullable": true
                            }
                          ]
                        },
                        "first_name": {
                          "anyOf": [
                            {
                              "type": "string"
                            },
                            {
                              "nullable": true
                            }
                          ]
                        },
                        "last_name": {
                          "anyOf": [
                            {
                              "type": "string"
                            },
                            {
                              "nullable": true
                            }
                          ]
                        },
                        "username": {
                          "anyOf": [
                            {
                              "type": "string"
                            },
                            {
                              "nullable": true
                            }
                          ]
                        },
                        "phone": {
                          "anyOf": [
                            {
                              "type": "string"
                            },
                            {
                              "nullable": true
                            }
                          ]
                        },
                        "profile_picture_url": {
                          "type": "string"
                        },
                        "status": {
                          "anyOf": [
                            {
                              "type": "object",
                              "properties": {
                                "name": {
                                  "type": "string"
                                },
                                "expires": {
                                  "type": "number"
                                },
                                "was_online": {
                                  "type": "number"
                                }
                              },
                              "required": [
                                "name"
                              ]
                            },
                            {
                              "nullable": true
                            }
                          ]
                        },
                        "restriction_reason": {
                          "anyOf": [
                            {
                              "type": "array",
                              "items": {
                                "type": "object",
                                "properties": {
                                  "platform": {
                                    "type": "string"
                                  },
                                  "reason": {
                                    "type": "string"
                                  },
                                  "text": {
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "platform",
                                  "reason",
                                  "text"
                                ]
                              }
                            },
                            {
                              "nullable": true
                            }
                          ]
                        },
                        "lang_code": {
                          "anyOf": [
                            {
                              "type": "string"
                            },
                            {
                              "nullable": true
                            }
                          ]
                        },
                        "object": {
                          "type": "string",
                          "enum": [
                            "UserProfile"
                          ]
                        }
                      },
                      "required": [
                        "provider",
                        "provider_id",
                        "profile_picture_url",
                        "object"
                      ]
                    },
                    {
                      "title": "Twitter",
                      "type": "object",
                      "properties": {
                        "provider": {
                          "type": "string",
                          "enum": [
                            "TWITTER"
                          ]
                        },
                        "id": {
                          "type": "string"
                        },
                        "name": {
                          "type": "string"
                        },
                        "screen_name": {
                          "type": "string"
                        },
                        "location": {
                          "type": "string"
                        },
                        "description": {
                          "anyOf": [
                            {
                              "nullable": true
                            },
                            {
                              "type": "string"
                            }
                          ]
                        },
                        "url": {
                          "anyOf": [
                            {
                              "nullable": true
                            },
                            {
                              "type": "string"
                            }
                          ]
                        },
                        "entities": {
                          "type": "object",
                          "properties": {
                            "description": {
                              "type": "object",
                              "properties": {
                                "urls": {
                                  "type": "array",
                                  "items": {}
                                }
                              },
                              "required": [
                                "urls"
                              ]
                            }
                          },
                          "required": [
                            "description"
                          ]
                        },
                        "protected": {
                          "type": "boolean"
                        },
                        "verified": {
                          "type": "boolean"
                        },
                        "followers_count": {
                          "type": "number"
                        },
                        "friends_count": {
                          "type": "number"
                        },
                        "listed_count": {
                          "type": "number"
                        },
                        "favourites_count": {
                          "type": "number"
                        },
                        "statuses_count": {
                          "type": "number"
                        },
                        "created_at": {
                          "type": "string"
                        },
                        "profile_banner_url": {
                          "anyOf": [
                            {
                              "type": "string"
                            },
                            {
                              "nullable": true
                            }
                          ]
                        },
                        "profile_image_url_https": {
                          "type": "string"
                        },
                        "default_profile": {
                          "type": "boolean"
                        },
                        "default_profile_image": {
                          "type": "boolean"
                        },
                        "withheld_in_countries": {
                          "type": "array",
                          "items": {
                            "type": "string"
                          }
                        },
                        "followed_by": {
                          "anyOf": [
                            {
                              "nullable": true
                            },
                            {
                              "type": "boolean"
                            }
                          ]
                        },
                        "following": {
                          "anyOf": [
                            {
                              "nullable": true
                            },
                            {
                              "type": "boolean"
                            }
                          ]
                        },
                        "follow_request_sent": {
                          "anyOf": [
                            {
                              "nullable": true
                            },
                            {
                              "type": "boolean"
                            }
                          ]
                        },
                        "has_extended_profile": {
                          "anyOf": [
                            {
                              "nullable": true
                            },
                            {
                              "type": "boolean"
                            }
                          ]
                        },
                        "notifications": {
                          "anyOf": [
                            {
                              "nullable": true
                            },
                            {
                              "type": "boolean"
                            }
                          ]
                        },
                        "advertiser_account_type": {
                          "anyOf": [
                            {
                              "nullable": true
                            },
                            {
                              "type": "string"
                            }
                          ]
                        },
                        "business_profile_state": {
                          "anyOf": [
                            {
                              "nullable": true
                            },
                            {
                              "type": "string"
                            }
                          ]
                        },
                        "require_some_consent": {
                          "anyOf": [
                            {
                              "nullable": true
                            },
                            {
                              "type": "boolean"
                            }
                          ]
                        },
                        "object": {
                          "type": "string",
                          "enum": [
                            "UserProfile"
                          ]
                        }
                      },
                      "required": [
                        "provider",
                        "id",
                        "name",
                        "screen_name",
                        "location",
                        "description",
                        "url",
                        "entities",
                        "protected",
                        "verified",
                        "followers_count",
                        "friends_count",
                        "listed_count",
                        "favourites_count",
                        "statuses_count",
                        "created_at",
                        "profile_image_url_https",
                        "default_profile",
                        "default_profile_image",
                        "withheld_in_countries",
                        "object"
                      ]
                    }
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