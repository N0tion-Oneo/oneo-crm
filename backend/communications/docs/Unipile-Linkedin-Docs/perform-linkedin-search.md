Perform Linkedin search

# OpenAPI definition
```json
{
  "openapi": "3.0.0",
  "paths": {
    "/api/v1/linkedin/search": {
      "post": {
        "operationId": "LinkedinController_search",
        "summary": "Perform Linkedin search",
        "description": "Search people and companies from the Linkedin Classic as well as Sales Navigator APIs. Check out our Guide with examples to master LinkedIn search : https://developer.unipile.com/docs/linkedin-search",
        "parameters": [
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
            "name": "limit",
            "required": false,
            "in": "query",
            "schema": {
              "minimum": 0,
              "maximum": 100,
              "description": "A limit for the number of items returned in the response. Can bet set up to 100 results for Sales Navigator and Recruiter, but Linkedin Classic shouldn't exceed 50.",
              "default": 10,
              "type": "integer"
            }
          },
          {
            "name": "account_id",
            "required": true,
            "in": "query",
            "description": "The ID of the account to trigger the request from.",
            "schema": {
              "type": "string"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "anyOf": [
                  {
                    "title": "Classic - People",
                    "type": "object",
                    "properties": {
                      "api": {
                        "type": "string",
                        "enum": [
                          "classic"
                        ]
                      },
                      "category": {
                        "type": "string",
                        "enum": [
                          "people"
                        ]
                      },
                      "keywords": {
                        "description": "Linkedin native filter : KEYWORDS.",
                        "type": "string"
                      },
                      "industry": {
                        "description": "The ID of the parameter. Use type INDUSTRY on the List search parameters route to find out the right ID.\nLinkedin native filter : INDUSTRY.",
                        "minItems": 1,
                        "type": "array",
                        "items": {
                          "type": "string",
                          "pattern": "^\\d+$"
                        }
                      },
                      "location": {
                        "description": "The ID of the parameter. Use type LOCATION on the List search parameters route to find out the right ID.\nLinkedin native filter : LOCATIONS.",
                        "minItems": 1,
                        "type": "array",
                        "items": {
                          "type": "string",
                          "pattern": "^\\d+$"
                        }
                      },
                      "profile_language": {
                        "description": "ISO 639-1 language code.\nLinkedin native filter : PROFILE LANGUAGE.",
                        "type": "array",
                        "items": {
                          "minLength": 2,
                          "maxLength": 2,
                          "type": "string"
                        }
                      },
                      "network_distance": {
                        "description": "First, second or third+ degree.\nLinkedin native filter : CONNECTIONS.",
                        "type": "array",
                        "items": {
                          "type": "number",
                          "enum": [
                            1,
                            2,
                            3
                          ]
                        }
                      },
                      "company": {
                        "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.\nLinkedin native filter : CURRENT COMPANY.",
                        "minItems": 1,
                        "type": "array",
                        "items": {
                          "type": "string",
                          "pattern": "^\\d+$"
                        }
                      },
                      "past_company": {
                        "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.\nLinkedin native filter : PAST COMPANY.",
                        "minItems": 1,
                        "type": "array",
                        "items": {
                          "type": "string",
                          "pattern": "^\\d+$"
                        }
                      },
                      "school": {
                        "description": "The ID of the parameter. Use type SCHOOL on the List search parameters route to find out the right ID.\nLinkedin native filter : SCHOOL.",
                        "minItems": 1,
                        "type": "array",
                        "items": {
                          "type": "string",
                          "pattern": "^\\d+$"
                        }
                      },
                      "service": {
                        "description": "The ID of the parameter. Use type SERVICE on the List search parameters route to find out the right ID.\nLinkedin native filter : SERVICE CATEGORIES.",
                        "minItems": 1,
                        "type": "array",
                        "items": {
                          "type": "string",
                          "pattern": "^\\d+$"
                        }
                      },
                      "connections_of": {
                        "description": "The ID of the parameter. Use type CONNECTIONS on the List search parameters route to find out the right ID.\nLinkedin native filter : CONNECTIONS OF.",
                        "minItems": 1,
                        "type": "array",
                        "items": {
                          "type": "string",
                          "pattern": "^.+$"
                        }
                      },
                      "followers_of": {
                        "description": "The ID of the parameter. Use type PEOPLE on the List search parameters route to find out the right ID.\nLinkedin native filter : FOLLOWERS OF.",
                        "minItems": 1,
                        "type": "array",
                        "items": {
                          "type": "string",
                          "pattern": "^.+$"
                        }
                      },
                      "open_to": {
                        "description": "Linkedin native filter : OPEN TO.",
                        "type": "array",
                        "items": {
                          "type": "string",
                          "enum": [
                            "proBono",
                            "boardMember"
                          ]
                        }
                      },
                      "advanced_keywords": {
                        "type": "object",
                        "properties": {
                          "first_name": {
                            "description": "Linkedin native filter : KEYWORDS / FIRST NAME.",
                            "type": "string"
                          },
                          "last_name": {
                            "description": "Linkedin native filter : KEYWORDS / LAST NAME.",
                            "type": "string"
                          },
                          "title": {
                            "description": "Linkedin native filter : KEYWORDS / TITLE.",
                            "type": "string"
                          },
                          "company": {
                            "description": "Linkedin native filter : KEYWORDS / COMPANY.",
                            "type": "string"
                          },
                          "school": {
                            "description": "Linkedin native filter : KEYWORDS / SCHOOL.",
                            "type": "string"
                          }
                        }
                      }
                    },
                    "required": [
                      "api",
                      "category"
                    ]
                  },
                  {
                    "title": "Classic - Companies",
                    "type": "object",
                    "properties": {
                      "api": {
                        "type": "string",
                        "enum": [
                          "classic"
                        ]
                      },
                      "category": {
                        "type": "string",
                        "enum": [
                          "companies"
                        ]
                      },
                      "keywords": {
                        "description": "Linkedin native filter : KEYWORDS.",
                        "type": "string"
                      },
                      "industry": {
                        "description": "The ID of the parameter. Use type INDUSTRY on the List search parameters route to find out the right ID.\nLinkedin native filter : INDUSTRY.",
                        "minItems": 1,
                        "type": "array",
                        "items": {
                          "type": "string",
                          "pattern": "^\\d+$"
                        }
                      },
                      "location": {
                        "description": "The ID of the parameter. Use type LOCATION on the List search parameters route to find out the right ID.\nLinkedin native filter : LOCATIONS.",
                        "minItems": 1,
                        "type": "array",
                        "items": {
                          "type": "string",
                          "pattern": "^\\d+$"
                        }
                      },
                      "has_job_offers": {
                        "description": "Linkedin native filter : JOB LISTINGS ON LINKEDIN.",
                        "type": "boolean"
                      },
                      "headcount": {
                        "description": "Linkedin native filter : COMPANY SIZE.",
                        "type": "array",
                        "items": {
                          "type": "object",
                          "properties": {
                            "min": {
                              "type": "number",
                              "enum": [
                                1,
                                11,
                                51,
                                201,
                                501,
                                1001,
                                5001,
                                10001
                              ]
                            },
                            "max": {
                              "type": "number",
                              "enum": [
                                10,
                                50,
                                200,
                                500,
                                1000,
                                5000,
                                10000
                              ]
                            }
                          }
                        }
                      },
                      "network_distance": {
                        "description": "First, second or third+ degree.\nLinkedin native filter : CONNECTIONS.",
                        "type": "array",
                        "items": {
                          "type": "number",
                          "enum": [
                            1,
                            2,
                            3
                          ]
                        }
                      }
                    },
                    "required": [
                      "api",
                      "category"
                    ]
                  },
                  {
                    "title": "Classic - POSTS",
                    "type": "object",
                    "properties": {
                      "api": {
                        "type": "string",
                        "enum": [
                          "classic"
                        ]
                      },
                      "category": {
                        "type": "string",
                        "enum": [
                          "posts"
                        ]
                      },
                      "keywords": {
                        "description": "Linkedin native filter : KEYWORDS.",
                        "type": "string"
                      },
                      "sort_by": {
                        "description": "Default value is relevance.\nLinkedin native filter : SORT BY.",
                        "type": "string",
                        "enum": [
                          "relevance",
                          "date"
                        ]
                      },
                      "date_posted": {
                        "description": "Linkedin native filter : DATE POSTED.",
                        "type": "string",
                        "enum": [
                          "past_day",
                          "past_week",
                          "past_month"
                        ]
                      },
                      "content_type": {
                        "description": "Linkedin native filter : CONTENT TYPE.",
                        "type": "string",
                        "enum": [
                          "videos",
                          "images",
                          "live_videos",
                          "collaborative_articles",
                          "documents"
                        ]
                      },
                      "posted_by": {
                        "minProperties": 1,
                        "type": "object",
                        "properties": {
                          "member": {
                            "description": "The ID of the parameter. Use type PEOPLE on the List search parameters route to find out the right ID.\nLinkedin native filter : FROM MEMBER.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^.+$"
                            }
                          },
                          "company": {
                            "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.\nLinkedin native filter : FROM COMPANY.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          },
                          "me": {
                            "description": "Linkedin native filter : POSTED BY [ME].",
                            "type": "boolean"
                          },
                          "first_connections": {
                            "description": "Linkedin native filter : POSTED BY [1ST CONNECTIONS].",
                            "type": "boolean"
                          },
                          "people_you_follow": {
                            "description": "Linkedin native filter : POSTED BY [PEOPLE YOU FOLLOW].",
                            "type": "boolean"
                          }
                        }
                      },
                      "mentioning": {
                        "minProperties": 1,
                        "type": "object",
                        "properties": {
                          "member": {
                            "description": "The ID of the parameter. Use type PEOPLE on the List search parameters route to find out the right ID.\nLinkedin native filter : MENTIONING MEMBER.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^.+$"
                            }
                          },
                          "company": {
                            "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.\nLinkedin native filter : MENTIONING COMPANY.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          }
                        }
                      },
                      "author": {
                        "minProperties": 1,
                        "type": "object",
                        "properties": {
                          "industry": {
                            "description": "The ID of the parameter. Use type INDUSTRY on the List search parameters route to find out the right ID.\nLinkedin native filter : AUTHOR INDUSTRY.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          },
                          "company": {
                            "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.\nLinkedin native filter : AUTHOR COMPANY.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          },
                          "keywords": {
                            "description": "Linkedin native filter : AUTHOR KEYWORDS.",
                            "type": "string"
                          }
                        }
                      }
                    },
                    "required": [
                      "api",
                      "category"
                    ]
                  },
                  {
                    "title": "Classic - JOBS",
                    "type": "object",
                    "properties": {
                      "api": {
                        "type": "string",
                        "enum": [
                          "classic"
                        ]
                      },
                      "category": {
                        "type": "string",
                        "enum": [
                          "jobs"
                        ]
                      },
                      "keywords": {
                        "description": "Linkedin native filter : KEYWORDS.",
                        "type": "string"
                      },
                      "sort_by": {
                        "description": "Default value is relevance.\nLinkedin native filter : SORT BY.",
                        "type": "string",
                        "enum": [
                          "relevance",
                          "date"
                        ]
                      },
                      "date_posted": {
                        "description": "The timespan in days since today for the filter to be applied.\nLinkedin native filter : DATE POSTED.",
                        "type": "number"
                      },
                      "region": {
                        "description": "The ID of the parameter. Use type LOCATION on the List search parameters route to find out the right ID.\nLinkedin native filter : GLOBAL LOCATION.",
                        "type": "string",
                        "pattern": "^\\d+$"
                      },
                      "location": {
                        "description": "The ID of the parameter. Use type LOCATION on the List search parameters route to find out the right ID.\nLinkedin native filter : LOCATION.",
                        "minItems": 1,
                        "type": "array",
                        "items": {
                          "type": "string",
                          "pattern": "^\\d+$"
                        }
                      },
                      "location_within_area": {
                        "description": "The search zone around the location in miles.\nLinkedin native filter : DISTANCE.",
                        "type": "number"
                      },
                      "industry": {
                        "description": "The ID of the parameter. Use type INDUSTRY on the List search parameters route to find out the right ID.\nLinkedin native filter : INDUSTRY.",
                        "minItems": 1,
                        "type": "array",
                        "items": {
                          "type": "string",
                          "pattern": "^\\d+$"
                        }
                      },
                      "seniority": {
                        "description": "Linkedin native filter : EXPERIENCE LEVEL.",
                        "type": "array",
                        "items": {
                          "type": "string",
                          "enum": [
                            "executive",
                            "director",
                            "mid_senior",
                            "associate",
                            "entry",
                            "intern"
                          ]
                        }
                      },
                      "function": {
                        "description": "The ID of the parameter. Use type JOB_FUNCTION on the List search parameters route to find out the right ID.\nLinkedin native filter : JOB FUNCTION.",
                        "minItems": 1,
                        "type": "array",
                        "items": {
                          "type": "string",
                          "pattern": "^[a-z]+$"
                        }
                      },
                      "role": {
                        "description": "The ID of the parameter. Use type JOB_TITLE on the List search parameters route to find out the right ID.\nLinkedin native filter : TITLE.",
                        "minItems": 1,
                        "type": "array",
                        "items": {
                          "type": "string",
                          "pattern": "^\\d+$"
                        }
                      },
                      "job_type": {
                        "description": "Linkedin native filter : JOB TYPE.",
                        "type": "array",
                        "items": {
                          "type": "string",
                          "enum": [
                            "full_time",
                            "part_time",
                            "contract",
                            "temporary",
                            "volunteer",
                            "internship",
                            "other"
                          ]
                        }
                      },
                      "company": {
                        "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.\nLinkedin native filter : COMPANY.",
                        "minItems": 1,
                        "type": "array",
                        "items": {
                          "type": "string",
                          "pattern": "^\\d+$"
                        }
                      },
                      "presence": {
                        "type": "array",
                        "items": {
                          "type": "string",
                          "enum": [
                            "on_site",
                            "hybrid",
                            "remote"
                          ]
                        }
                      },
                      "easy_apply": {
                        "description": "Linkedin native filter : EASY APPLY.",
                        "type": "boolean"
                      },
                      "has_verifications": {
                        "description": "Linkedin native filter : HAS VERIFICATIONS.",
                        "type": "boolean"
                      },
                      "under_10_applicants": {
                        "description": "Linkedin native filter : UNDER 10 APPLICANTS.",
                        "type": "boolean"
                      },
                      "in_your_network": {
                        "description": "Linkedin native filter : IN YOUR NETWORK.",
                        "type": "boolean"
                      },
                      "fair_chance_employer": {
                        "description": "Linkedin native filter : FAIR CHANCE EMPLOYER.",
                        "type": "boolean"
                      },
                      "benefits": {
                        "description": "Linkedin native filter : BENEFITS.",
                        "type": "array",
                        "items": {
                          "type": "string",
                          "enum": [
                            "medical_insurance",
                            "vision_insurance",
                            "dental_insurance",
                            "disability_insurance",
                            "401(k)",
                            "pension_plan",
                            "paid_maternity_leave",
                            "paid_paternity_leave",
                            "commuter_benefits",
                            "student_loan_assistance",
                            "tuition_assistance"
                          ]
                        }
                      },
                      "commitments": {
                        "description": "Linkedin native filter : COMMITMENTS.",
                        "type": "array",
                        "items": {
                          "type": "string",
                          "enum": [
                            "career_growth_and_learning",
                            "diversity_equity_and_inclusion",
                            "environmental_sustainability",
                            "social_impact",
                            "work_life_balance"
                          ]
                        }
                      },
                      "minimum_salary": {
                        "description": "Linkedin native filter : SALARY.",
                        "anyOf": [
                          {
                            "title": "Dollar based",
                            "type": "object",
                            "properties": {
                              "currency": {
                                "anyOf": [
                                  {
                                    "type": "string",
                                    "enum": [
                                      "USD"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "AUD"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "CAD"
                                    ]
                                  }
                                ]
                              },
                              "value": {
                                "description": "Value in thousands of dollars.",
                                "type": "number",
                                "enum": [
                                  40,
                                  60,
                                  80,
                                  100,
                                  120,
                                  140,
                                  160,
                                  180,
                                  200
                                ]
                              }
                            },
                            "required": [
                              "currency",
                              "value"
                            ]
                          },
                          {
                            "title": "Pound based",
                            "type": "object",
                            "properties": {
                              "currency": {
                                "type": "string",
                                "enum": [
                                  "GBP"
                                ]
                              },
                              "value": {
                                "description": "Value in thousands of pounds.",
                                "type": "number",
                                "enum": [
                                  20,
                                  30,
                                  40,
                                  50,
                                  60,
                                  70,
                                  80,
                                  90,
                                  100
                                ]
                              }
                            },
                            "required": [
                              "currency",
                              "value"
                            ]
                          }
                        ]
                      }
                    },
                    "required": [
                      "api",
                      "category"
                    ]
                  },
                  {
                    "title": "Sales Navigator - People",
                    "type": "object",
                    "properties": {
                      "api": {
                        "type": "string",
                        "enum": [
                          "sales_navigator"
                        ]
                      },
                      "category": {
                        "type": "string",
                        "enum": [
                          "people"
                        ]
                      },
                      "keywords": {
                        "description": "Linkedin native filter : KEYWORDS.",
                        "type": "string"
                      },
                      "last_viewed_at": {
                        "description": "Unix timestamp to be used with a saved search to filter new results from this date.",
                        "type": "number"
                      },
                      "saved_search_id": {
                        "description": "The ID of the parameter. Use type SAVED_SEARCHES on the List search parameters route to find out the right ID.\nOverrides all other parameters.",
                        "type": "string",
                        "pattern": "^\\d+$"
                      },
                      "recent_search_id": {
                        "description": "The ID of the parameter. Use type RECENT_SEARCHES on the List search parameters route to find out the right ID.\nOverrides all other parameters.",
                        "type": "string",
                        "pattern": "^\\d+$"
                      },
                      "location": {
                        "description": "Linkedin native filter : GEOGRAPHY.",
                        "type": "object",
                        "properties": {
                          "include": {
                            "description": "The ID of the parameter. Use type LOCATION on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          },
                          "exclude": {
                            "description": "The ID of the parameter. Use type LOCATION on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          }
                        }
                      },
                      "location_by_postal_code": {
                        "type": "object",
                        "properties": {
                          "include": {
                            "description": "The ID of the parameter. Use type POSTAL_CODE on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          },
                          "exclude": {
                            "description": "The ID of the parameter. Use type POSTAL_CODE on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          },
                          "within_area": {
                            "description": "The search zone around the location in miles.",
                            "type": "number"
                          }
                        }
                      },
                      "industry": {
                        "description": "Linkedin native filter : INDUSTRY.",
                        "type": "object",
                        "properties": {
                          "include": {
                            "description": "The ID of the parameter. Use type SALES_INDUSTRY on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          },
                          "exclude": {
                            "description": "The ID of the parameter. Use type SALES_INDUSTRY on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          }
                        }
                      },
                      "first_name": {
                        "description": "Linkedin native filter : FIRST NAME.",
                        "type": "string"
                      },
                      "last_name": {
                        "description": "Linkedin native filter : LAST NAME.",
                        "type": "string"
                      },
                      "tenure": {
                        "description": "Linkedin native filter : YEARS OF EXPERIENCE.",
                        "type": "array",
                        "items": {
                          "type": "object",
                          "properties": {
                            "min": {
                              "type": "number",
                              "enum": [
                                0,
                                1,
                                3,
                                6,
                                10
                              ]
                            },
                            "max": {
                              "type": "number",
                              "enum": [
                                1,
                                2,
                                5,
                                10
                              ]
                            }
                          }
                        }
                      },
                      "groups": {
                        "description": "The ID of the parameter. Use type GROUPS on the List search parameters route to find out the right ID.\nLinkedin native filter : GROUPS.",
                        "minItems": 1,
                        "type": "array",
                        "items": {
                          "type": "string",
                          "pattern": "^\\d+$"
                        }
                      },
                      "school": {
                        "description": "Linkedin native filter : SCHOOL.",
                        "type": "object",
                        "properties": {
                          "include": {
                            "description": "The ID of the parameter. Use type SCHOOL on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          },
                          "exclude": {
                            "description": "The ID of the parameter. Use type SCHOOL on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          }
                        }
                      },
                      "profile_language": {
                        "description": "ISO 639-1 language code.\nLinkedin native filter : PROFILE LANGUAGE.",
                        "type": "array",
                        "items": {
                          "minLength": 2,
                          "maxLength": 2,
                          "type": "string"
                        }
                      },
                      "company": {
                        "description": "Linkedin native filter : CURRENT COMPANY.",
                        "type": "object",
                        "properties": {
                          "include": {
                            "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.\nYou can also set a plain text company name instead.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": ".+"
                            }
                          },
                          "exclude": {
                            "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.\nYou can also set a plain text company name instead.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": ".+"
                            }
                          }
                        }
                      },
                      "company_headcount": {
                        "description": "Linkedin native filter : COMPANY HEADCOUNT.",
                        "type": "array",
                        "items": {
                          "type": "object",
                          "properties": {
                            "min": {
                              "type": "number",
                              "enum": [
                                1,
                                11,
                                51,
                                201,
                                501,
                                1001,
                                5001,
                                10001
                              ]
                            },
                            "max": {
                              "type": "number",
                              "enum": [
                                10,
                                50,
                                200,
                                500,
                                1000,
                                5000,
                                10000
                              ]
                            }
                          }
                        }
                      },
                      "company_type": {
                        "description": "Linkedin native filter : COMPANY TYPE.",
                        "type": "array",
                        "items": {
                          "type": "string",
                          "enum": [
                            "public_company",
                            "privately_held",
                            "non_profit",
                            "educational_institution",
                            "partnership",
                            "self_employed",
                            "self_owned",
                            "government_agency"
                          ]
                        }
                      },
                      "company_location": {
                        "description": "Linkedin native filter : COMPANY HEADQUARTERS LOCATION.",
                        "type": "object",
                        "properties": {
                          "include": {
                            "description": "The ID of the parameter. Use type LOCATION on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          },
                          "exclude": {
                            "description": "The ID of the parameter. Use type LOCATION on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          }
                        }
                      },
                      "tenure_at_company": {
                        "description": "Linkedin native filter : YEARS IN CURRENT COMPANY.",
                        "type": "array",
                        "items": {
                          "type": "object",
                          "properties": {
                            "min": {
                              "type": "number",
                              "enum": [
                                0,
                                1,
                                3,
                                6,
                                10
                              ]
                            },
                            "max": {
                              "type": "number",
                              "enum": [
                                1,
                                2,
                                5,
                                10
                              ]
                            }
                          }
                        }
                      },
                      "past_company": {
                        "description": "Linkedin native filter : PAST COMPANY.",
                        "type": "object",
                        "properties": {
                          "include": {
                            "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.\nYou can also set a plain text company name instead.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": ".+"
                            }
                          },
                          "exclude": {
                            "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.\nYou can also set a plain text company name instead.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": ".+"
                            }
                          }
                        }
                      },
                      "function": {
                        "description": "Linkedin native filter : FUNCTION.",
                        "type": "object",
                        "properties": {
                          "include": {
                            "description": "The ID of the parameter. Use type DEPARTMENT on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          },
                          "exclude": {
                            "description": "The ID of the parameter. Use type DEPARTMENT on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          }
                        }
                      },
                      "role": {
                        "description": "Linkedin native filter : CURRENT JOB TITLE.",
                        "type": "object",
                        "properties": {
                          "include": {
                            "description": "The ID of the parameter. Use type JOB_TITLE on the List search parameters route to find out the right ID.\nYou can also set a plain text job title instead.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": ".+"
                            }
                          },
                          "exclude": {
                            "description": "The ID of the parameter. Use type JOB_TITLE on the List search parameters route to find out the right ID.\nYou can also set a plain text job title instead.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": ".+"
                            }
                          }
                        }
                      },
                      "tenure_at_role": {
                        "description": "Linkedin native filter : YEARS IN CURRENT POSITION.",
                        "type": "array",
                        "items": {
                          "type": "object",
                          "properties": {
                            "min": {
                              "type": "number",
                              "enum": [
                                0,
                                1,
                                3,
                                6,
                                10
                              ]
                            },
                            "max": {
                              "type": "number",
                              "enum": [
                                1,
                                2,
                                5,
                                10
                              ]
                            }
                          }
                        }
                      },
                      "seniority": {
                        "description": "Linkedin native filter : SENIORITY LEVEL.",
                        "type": "object",
                        "properties": {
                          "include": {
                            "type": "array",
                            "items": {
                              "type": "string",
                              "enum": [
                                "owner/partner",
                                "cxo",
                                "vice_president",
                                "director",
                                "experienced_manager",
                                "entry_level_manager",
                                "strategic",
                                "senior",
                                "entry_level",
                                "in_training"
                              ]
                            }
                          },
                          "exclude": {
                            "type": "array",
                            "items": {
                              "type": "string",
                              "enum": [
                                "owner/partner",
                                "cxo",
                                "vice_president",
                                "director",
                                "experienced_manager",
                                "entry_level_manager",
                                "strategic",
                                "senior",
                                "entry_level",
                                "in_training"
                              ]
                            }
                          }
                        }
                      },
                      "past_role": {
                        "description": "Linkedin native filter : PAST JOB TITLE.",
                        "type": "object",
                        "properties": {
                          "include": {
                            "description": "The ID of the parameter. Use type JOB_TITLE on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          },
                          "exclude": {
                            "description": "The ID of the parameter. Use type JOB_TITLE on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          }
                        }
                      },
                      "following_your_company": {
                        "description": "Linkedin native filter : FOLLOWING YOUR COMPANY.",
                        "type": "boolean"
                      },
                      "viewed_your_profile_recently": {
                        "description": "Linkedin native filter : VIEWED YOUR PROFILE RECENTLY.",
                        "type": "boolean"
                      },
                      "network_distance": {
                        "description": "First, second, third+ degree or GROUP.\nLinkedin native filter : CONNECTION.",
                        "type": "array",
                        "items": {
                          "anyOf": [
                            {
                              "type": "number",
                              "enum": [
                                1,
                                2,
                                3
                              ]
                            },
                            {
                              "type": "string",
                              "enum": [
                                "GROUP"
                              ]
                            }
                          ]
                        }
                      },
                      "connections_of": {
                        "description": "The ID of the parameter. Use type PEOPLE on the List search parameters route to find out the right ID.\nLinkedin native filter : CONNECTIONS OF.",
                        "minItems": 1,
                        "type": "array",
                        "items": {
                          "type": "string",
                          "pattern": "^.+$"
                        }
                      },
                      "past_colleague": {
                        "description": "Linkedin native filter : PAST COLLEAGUE.",
                        "type": "boolean"
                      },
                      "shared_experiences": {
                        "description": "Linkedin native filter : SHARED EXPERIENCES.",
                        "type": "boolean"
                      },
                      "changed_jobs": {
                        "description": "Linkedin native filter : CHANGED JOBS.",
                        "type": "boolean"
                      },
                      "posted_on_linkedin": {
                        "description": "Linkedin native filter : POSTED ON LINKEDIN.",
                        "type": "boolean"
                      },
                      "mentionned_in_news": {
                        "description": "Linkedin native filter : MENTIONNED IN NEWS.",
                        "type": "boolean"
                      },
                      "persona": {
                        "description": "The ID of the parameter. Use type PERSONA on the List search parameters route to find out the right ID.\nLinkedin native filter : PERSONA.",
                        "minItems": 1,
                        "type": "array",
                        "items": {
                          "type": "string",
                          "pattern": "^\\d+$"
                        }
                      },
                      "account_lists": {
                        "description": "Linkedin native filter : ACCOUNT LISTS.",
                        "type": "object",
                        "properties": {
                          "include": {
                            "description": "The ID of the parameter. Use type ACCOUNT_LISTS on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^(\\d+|ALL)$"
                            }
                          },
                          "exclude": {
                            "description": "The ID of the parameter. Use type ACCOUNT_LISTS on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^(\\d+|ALL)$"
                            }
                          }
                        }
                      },
                      "lead_lists": {
                        "description": "Linkedin native filter : LEAD LISTS.",
                        "type": "object",
                        "properties": {
                          "include": {
                            "description": "The ID of the parameter. Use type LEAD_LISTS on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^(\\d+|ALL)$"
                            }
                          },
                          "exclude": {
                            "description": "The ID of the parameter. Use type LEAD_LISTS on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^(\\d+|ALL)$"
                            }
                          }
                        }
                      },
                      "viewed_profile_recently": {
                        "description": "Linkedin native filter : PEOPLE YOU INTERACTED WITH / VIEWED PROFILE.",
                        "type": "boolean"
                      },
                      "messaged_recently": {
                        "description": "Linkedin native filter : PEOPLE YOU INTERACTED WITH / MESSAGED.",
                        "type": "boolean"
                      },
                      "include_saved_leads": {
                        "description": "Linkedin native filter : SAVED LEADS AND ACCOUNTS / ALL MY SAVED LEADS.",
                        "type": "boolean"
                      },
                      "include_saved_accounts": {
                        "description": "Linkedin native filter : SAVED LEADS AND ACCOUNTS / ALL MY SAVED ACCOUNTS.",
                        "type": "boolean"
                      }
                    },
                    "required": [
                      "api",
                      "category"
                    ]
                  },
                  {
                    "title": "Sales Navigator - Companies",
                    "type": "object",
                    "properties": {
                      "api": {
                        "type": "string",
                        "enum": [
                          "sales_navigator"
                        ]
                      },
                      "category": {
                        "type": "string",
                        "enum": [
                          "companies"
                        ]
                      },
                      "keywords": {
                        "description": "Linkedin native filter : KEYWORDS.",
                        "type": "string"
                      },
                      "last_viewed_at": {
                        "description": "Unix timestamp to be used with a saved search to filter new results from this date.",
                        "type": "number"
                      },
                      "saved_search_id": {
                        "description": "The ID of the parameter. Use type SAVED_SEARCHES on the List search parameters route to find out the right ID.\nOverrides all other parameters.",
                        "type": "string",
                        "pattern": "^\\d+$"
                      },
                      "recent_search_id": {
                        "description": "The ID of the parameter. Use type RECENT_SEARCHES on the List search parameters route to find out the right ID.\nOverrides all other parameters.",
                        "type": "string",
                        "pattern": "^\\d+$"
                      },
                      "industry": {
                        "description": "Linkedin native filter : INDUSTRY.",
                        "type": "object",
                        "properties": {
                          "include": {
                            "description": "The ID of the parameter. Use type SALES_INDUSTRY on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          },
                          "exclude": {
                            "description": "The ID of the parameter. Use type SALES_INDUSTRY on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          }
                        }
                      },
                      "location": {
                        "description": "Linkedin native filter : HEADQUARTERS LOCATION.",
                        "type": "object",
                        "properties": {
                          "include": {
                            "description": "The ID of the parameter. Use type LOCATION on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          },
                          "exclude": {
                            "description": "The ID of the parameter. Use type LOCATION on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          }
                        }
                      },
                      "location_by_postal_code": {
                        "type": "object",
                        "properties": {
                          "include": {
                            "description": "The ID of the parameter. Use type POSTAL_CODE on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          },
                          "exclude": {
                            "description": "The ID of the parameter. Use type POSTAL_CODE on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          },
                          "within_area": {
                            "description": "The search zone around the location in miles.",
                            "type": "number"
                          }
                        }
                      },
                      "has_job_offers": {
                        "description": "Linkedin native filter : JOB OPPORTUNITIES / HIRING ON LINKEDIN.",
                        "type": "boolean"
                      },
                      "headcount": {
                        "description": "Linkedin native filter : COMPANY HEADCOUNT.",
                        "type": "array",
                        "items": {
                          "type": "object",
                          "properties": {
                            "min": {
                              "type": "number",
                              "enum": [
                                1,
                                11,
                                51,
                                201,
                                501,
                                1001,
                                5001,
                                10001
                              ]
                            },
                            "max": {
                              "type": "number",
                              "enum": [
                                10,
                                50,
                                200,
                                500,
                                1000,
                                5000,
                                10000
                              ]
                            }
                          }
                        }
                      },
                      "headcount_growth": {
                        "description": "Linkedin native filter : COMPANY HEADCOUNT GROWTH.",
                        "type": "object",
                        "properties": {
                          "min": {
                            "type": "number"
                          },
                          "max": {
                            "type": "number"
                          }
                        }
                      },
                      "department_headcount": {
                        "description": "Linkedin native filter : DEPARTMENT HEADCOUNT.",
                        "type": "object",
                        "properties": {
                          "department": {
                            "description": "The ID of the parameter. Use type DEPARTMENT on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          },
                          "min": {
                            "type": "number"
                          },
                          "max": {
                            "type": "number"
                          }
                        },
                        "required": [
                          "department"
                        ]
                      },
                      "department_headcount_growth": {
                        "description": "Linkedin native filter : DEPARTMENT HEADCOUNT GROWTH.",
                        "type": "object",
                        "properties": {
                          "department": {
                            "description": "The ID of the parameter. Use type DEPARTMENT on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          },
                          "min": {
                            "type": "number"
                          },
                          "max": {
                            "type": "number"
                          }
                        },
                        "required": [
                          "department"
                        ]
                      },
                      "network_distance": {
                        "description": "First, second or third+ degree.\nLinkedin native filter : CONNECTION.",
                        "type": "array",
                        "items": {
                          "type": "number",
                          "enum": [
                            1,
                            2,
                            3
                          ]
                        }
                      },
                      "annual_revenue": {
                        "description": "Linkedin native filter : ANNUAL REVENUE. If you want to use the '1000+' value, please set the 'max' value field to 1001.",
                        "type": "object",
                        "properties": {
                          "currency": {
                            "minLength": 3,
                            "maxLength": 3,
                            "description": "ISO 4217 currency code.",
                            "type": "string"
                          },
                          "min": {
                            "type": "number",
                            "enum": [
                              0,
                              0.2,
                              1,
                              2.5,
                              5,
                              10,
                              20,
                              50,
                              100,
                              500,
                              1000,
                              1001
                            ]
                          },
                          "max": {
                            "type": "number",
                            "enum": [
                              0,
                              0.2,
                              1,
                              2.5,
                              5,
                              10,
                              20,
                              50,
                              100,
                              500,
                              1000,
                              1001
                            ]
                          }
                        },
                        "required": [
                          "currency",
                          "min",
                          "max"
                        ]
                      },
                      "followers_count": {
                        "description": "Linkedin native filter : NUMBER OF FOLLOWERS.",
                        "type": "array",
                        "items": {
                          "type": "object",
                          "properties": {
                            "min": {
                              "type": "number",
                              "enum": [
                                1,
                                51,
                                101,
                                1001,
                                5001
                              ]
                            },
                            "max": {
                              "type": "number",
                              "enum": [
                                50,
                                100,
                                1000,
                                5000
                              ]
                            }
                          }
                        }
                      },
                      "fortune": {
                        "description": "Linkedin native filter : FORTUNE.",
                        "type": "array",
                        "items": {
                          "type": "object",
                          "properties": {
                            "min": {
                              "type": "number",
                              "enum": [
                                0,
                                51,
                                101,
                                251
                              ]
                            },
                            "max": {
                              "type": "number",
                              "enum": [
                                50,
                                100,
                                250,
                                500
                              ]
                            }
                          }
                        }
                      },
                      "technologies": {
                        "description": "The ID of the parameter. Use type TECHNOLOGIES on the List search parameters route to find out the right ID.\nLinkedin native filter : TECHNOLOGIES USED.",
                        "minItems": 1,
                        "type": "array",
                        "items": {
                          "type": "string",
                          "pattern": "^\\d+$"
                        }
                      },
                      "recent_activities": {
                        "description": "Linkedin native filter : RECENT ACTIVITIES.",
                        "type": "array",
                        "items": {
                          "type": "string",
                          "enum": [
                            "senior_leadership_changes",
                            "funding_events"
                          ]
                        }
                      },
                      "saved_accounts": {
                        "description": "The ID of the parameter. Use type SAVED_ACCOUNTS on the List search parameters route to find out the right ID.\nLinkedin native filter : SAVED ACCOUNTS.",
                        "minItems": 1,
                        "type": "array",
                        "items": {
                          "type": "string",
                          "pattern": "^.+$"
                        }
                      },
                      "account_lists": {
                        "description": "Linkedin native filter : ACCOUNT LISTS.",
                        "type": "object",
                        "properties": {
                          "include": {
                            "description": "The ID of the parameter. Use type ACCOUNT_LISTS on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^(\\d+|ALL)$"
                            }
                          },
                          "exclude": {
                            "description": "The ID of the parameter. Use type ACCOUNT_LISTS on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^(\\d+|ALL)$"
                            }
                          }
                        }
                      }
                    },
                    "required": [
                      "api",
                      "category"
                    ]
                  },
                  {
                    "title": "Recruiter - People",
                    "type": "object",
                    "properties": {
                      "api": {
                        "type": "string",
                        "enum": [
                          "recruiter"
                        ]
                      },
                      "category": {
                        "type": "string",
                        "enum": [
                          "people"
                        ]
                      },
                      "keywords": {
                        "minLength": 1,
                        "description": "Boolean modifiers can be used to refine your search.\nExample : developers AND product owners NOT managers",
                        "type": "string"
                      },
                      "saved_search": {
                        "description": "This parameter will override all others.",
                        "type": "object",
                        "properties": {
                          "id": {
                            "description": "The ID of the parameter. Use type SAVED_SEARCHES on the List search parameters route to find out the right ID.",
                            "type": "string",
                            "pattern": "^\\d+$"
                          },
                          "project_id": {
                            "description": "The ID of the parameter. Use type SAVED_SEARCHES on the List search parameters route to find out the right ID.",
                            "type": "string",
                            "pattern": "^\\d+$"
                          }
                        },
                        "required": [
                          "id",
                          "project_id"
                        ]
                      },
                      "saved_filter": {
                        "description": "The ID of the parameter. Use type SAVED_FILTERS on the List search parameters route to find out the right ID.",
                        "type": "string",
                        "pattern": "^\\d+$"
                      },
                      "location": {
                        "type": "array",
                        "items": {
                          "type": "object",
                          "properties": {
                            "id": {
                              "description": "The ID of the parameter. Use type LOCATION on the List search parameters route to find out the right ID.",
                              "type": "string",
                              "pattern": "^\\d+$"
                            },
                            "priority": {
                              "type": "string",
                              "enum": [
                                "CAN_HAVE",
                                "MUST_HAVE",
                                "DOESNT_HAVE"
                              ]
                            },
                            "scope": {
                              "type": "string",
                              "enum": [
                                "CURRENT",
                                "OPEN_TO_RELOCATE_ONLY",
                                "CURRENT_OR_OPEN_TO_RELOCATE"
                              ]
                            },
                            "title": {
                              "description": "The title that came along with the ID in the List search parameters route response. Only necessary if the CURRENT_OR_OPEN_TO_RELOCATE value of the scope parameter is used.",
                              "type": "string"
                            }
                          },
                          "required": [
                            "id"
                          ]
                        }
                      },
                      "location_within_area": {
                        "description": "The search zone around the location in miles.",
                        "type": "number"
                      },
                      "industry": {
                        "description": "Linkedin native filter : INDUSTRIES.",
                        "type": "object",
                        "properties": {
                          "include": {
                            "description": "The ID of the parameter. Use type INDUSTRY on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          },
                          "exclude": {
                            "description": "The ID of the parameter. Use type INDUSTRY on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          }
                        }
                      },
                      "role": {
                        "type": "array",
                        "items": {
                          "description": "Linkedin native filter : JOB TITLES.",
                          "anyOf": [
                            {
                              "title": "ID based",
                              "type": "object",
                              "properties": {
                                "id": {
                                  "description": "The ID of the parameter. Use type JOB_TITLE on the List search parameters route to find out the right ID.",
                                  "type": "string",
                                  "pattern": "^\\d+$"
                                },
                                "is_selection": {
                                  "description": "Linkedin job titles are either strict filters (only the people with that job) or selections (can include people with related jobs). A strict parameter cannot be used as a selection and vice versa. This information is provided on the List search parameters route results.",
                                  "type": "boolean"
                                },
                                "priority": {
                                  "type": "string",
                                  "enum": [
                                    "CAN_HAVE",
                                    "MUST_HAVE",
                                    "DOESNT_HAVE"
                                  ]
                                },
                                "scope": {
                                  "type": "string",
                                  "enum": [
                                    "CURRENT_OR_PAST",
                                    "CURRENT",
                                    "PAST",
                                    "PAST_NOT_CURRENT",
                                    "OPEN_TO_WORK"
                                  ]
                                }
                              },
                              "required": [
                                "id",
                                "is_selection"
                              ],
                              "x-scope": {
                                "type": "string",
                                "enum": [
                                  "CURRENT_OR_PAST",
                                  "CURRENT",
                                  "PAST",
                                  "PAST_NOT_CURRENT",
                                  "OPEN_TO_WORK"
                                ]
                              }
                            },
                            {
                              "title": "Keywords based",
                              "type": "object",
                              "properties": {
                                "keywords": {
                                  "minLength": 1,
                                  "description": "Boolean modifiers can be used to refine your search.\nExample : developers AND product owners NOT managers",
                                  "type": "string"
                                },
                                "priority": {
                                  "type": "string",
                                  "enum": [
                                    "CAN_HAVE",
                                    "MUST_HAVE",
                                    "DOESNT_HAVE"
                                  ]
                                },
                                "scope": {
                                  "type": "string",
                                  "enum": [
                                    "CURRENT_OR_PAST",
                                    "CURRENT",
                                    "PAST",
                                    "PAST_NOT_CURRENT",
                                    "OPEN_TO_WORK"
                                  ]
                                }
                              },
                              "required": [
                                "keywords"
                              ],
                              "x-scope": {
                                "type": "string",
                                "enum": [
                                  "CURRENT_OR_PAST",
                                  "CURRENT",
                                  "PAST",
                                  "PAST_NOT_CURRENT",
                                  "OPEN_TO_WORK"
                                ]
                              }
                            }
                          ]
                        }
                      },
                      "skills": {
                        "type": "array",
                        "items": {
                          "description": "Linkedin native filter : SKILLS AND ASSESSMENTS.",
                          "anyOf": [
                            {
                              "title": "ID based",
                              "type": "object",
                              "properties": {
                                "id": {
                                  "description": "The ID of the parameter. Use type SKILL on the List search parameters route to find out the right ID.",
                                  "type": "string",
                                  "pattern": "^\\d+$"
                                },
                                "priority": {
                                  "type": "string",
                                  "enum": [
                                    "CAN_HAVE",
                                    "MUST_HAVE",
                                    "DOESNT_HAVE"
                                  ]
                                }
                              },
                              "required": [
                                "id"
                              ]
                            },
                            {
                              "title": "Keywords based",
                              "type": "object",
                              "properties": {
                                "keywords": {
                                  "minLength": 1,
                                  "description": "Boolean modifiers can be used to refine your search.\nExample : developers AND product owners NOT managers",
                                  "type": "string"
                                },
                                "priority": {
                                  "type": "string",
                                  "enum": [
                                    "CAN_HAVE",
                                    "MUST_HAVE",
                                    "DOESNT_HAVE"
                                  ]
                                }
                              },
                              "required": [
                                "keywords"
                              ]
                            }
                          ]
                        }
                      },
                      "company": {
                        "type": "array",
                        "items": {
                          "description": "Linkedin native filter : COMPANIES.",
                          "anyOf": [
                            {
                              "title": "ID based",
                              "type": "object",
                              "properties": {
                                "id": {
                                  "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.",
                                  "type": "string",
                                  "pattern": "^\\d+$"
                                },
                                "priority": {
                                  "type": "string",
                                  "enum": [
                                    "CAN_HAVE",
                                    "MUST_HAVE",
                                    "DOESNT_HAVE"
                                  ]
                                },
                                "scope": {
                                  "type": "string",
                                  "enum": [
                                    "CURRENT_OR_PAST",
                                    "CURRENT",
                                    "PAST",
                                    "PAST_NOT_CURRENT"
                                  ]
                                }
                              },
                              "required": [
                                "id"
                              ],
                              "x-scope": {
                                "type": "string",
                                "enum": [
                                  "CURRENT_OR_PAST",
                                  "CURRENT",
                                  "PAST",
                                  "PAST_NOT_CURRENT"
                                ]
                              }
                            },
                            {
                              "title": "Keywords based",
                              "type": "object",
                              "properties": {
                                "keywords": {
                                  "minLength": 1,
                                  "description": "Boolean modifiers can be used to refine your search.\nExample : developers AND product owners NOT managers",
                                  "type": "string"
                                },
                                "priority": {
                                  "type": "string",
                                  "enum": [
                                    "CAN_HAVE",
                                    "MUST_HAVE",
                                    "DOESNT_HAVE"
                                  ]
                                },
                                "scope": {
                                  "type": "string",
                                  "enum": [
                                    "CURRENT_OR_PAST",
                                    "CURRENT",
                                    "PAST",
                                    "PAST_NOT_CURRENT"
                                  ]
                                }
                              },
                              "required": [
                                "keywords"
                              ],
                              "x-scope": {
                                "type": "string",
                                "enum": [
                                  "CURRENT_OR_PAST",
                                  "CURRENT",
                                  "PAST",
                                  "PAST_NOT_CURRENT"
                                ]
                              }
                            }
                          ]
                        }
                      },
                      "company_headcount": {
                        "description": "Linkedin native filter : COMPANY SIZES.",
                        "type": "array",
                        "items": {
                          "type": "object",
                          "properties": {
                            "min": {
                              "type": "number",
                              "enum": [
                                1,
                                11,
                                51,
                                201,
                                501,
                                1001,
                                5001,
                                10001
                              ]
                            },
                            "max": {
                              "type": "number",
                              "enum": [
                                10,
                                50,
                                200,
                                500,
                                1000,
                                5000,
                                10000
                              ]
                            }
                          }
                        }
                      },
                      "current_company": {
                        "type": "array",
                        "items": {
                          "description": "Linkedin native filter : CURRENT COMPANIES.",
                          "type": "object",
                          "properties": {
                            "id": {
                              "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.",
                              "type": "string",
                              "pattern": "^\\d+$"
                            },
                            "priority": {
                              "type": "string",
                              "enum": [
                                "CAN_HAVE",
                                "MUST_HAVE",
                                "DOESNT_HAVE"
                              ]
                            }
                          },
                          "required": [
                            "id"
                          ]
                        }
                      },
                      "past_company": {
                        "type": "array",
                        "items": {
                          "description": "Linkedin native filter : PAST COMPANIES.",
                          "type": "object",
                          "properties": {
                            "id": {
                              "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.",
                              "type": "string",
                              "pattern": "^\\d+$"
                            },
                            "priority": {
                              "type": "string",
                              "enum": [
                                "CAN_HAVE",
                                "MUST_HAVE",
                                "DOESNT_HAVE"
                              ]
                            }
                          },
                          "required": [
                            "id"
                          ]
                        }
                      },
                      "school": {
                        "type": "array",
                        "items": {
                          "description": "Linkedin native filter : SCHOOLS.",
                          "type": "object",
                          "properties": {
                            "id": {
                              "description": "The ID of the parameter. Use type SCHOOL on the List search parameters route to find out the right ID.",
                              "type": "string",
                              "pattern": "^\\d+$"
                            },
                            "priority": {
                              "type": "string",
                              "enum": [
                                "CAN_HAVE",
                                "MUST_HAVE",
                                "DOESNT_HAVE"
                              ]
                            }
                          },
                          "required": [
                            "id"
                          ]
                        }
                      },
                      "groups": {
                        "description": "The ID of the parameter. Use type GROUPS on the List search parameters route to find out the right ID.\nLinkedin native filter : ALL GROUPS.",
                        "minItems": 1,
                        "type": "array",
                        "items": {
                          "type": "string",
                          "pattern": "^\\d+$"
                        }
                      },
                      "graduation_year": {
                        "description": "A range of years.\nLinkedin native filter : YEAR OF GRADUATION.",
                        "type": "object",
                        "properties": {
                          "min": {
                            "minimum": 1000,
                            "maximum": 9999,
                            "type": "number"
                          },
                          "max": {
                            "minimum": 1000,
                            "maximum": 9999,
                            "type": "number"
                          }
                        }
                      },
                      "tenure": {
                        "description": "Linkedin native filter : YEARS OF EXPERIENCE.",
                        "type": "object",
                        "properties": {
                          "min": {
                            "type": "number"
                          },
                          "max": {
                            "type": "number"
                          }
                        }
                      },
                      "seniority": {
                        "description": "Linkedin native filter : SENIORITY.",
                        "type": "object",
                        "properties": {
                          "include": {
                            "type": "array",
                            "items": {
                              "type": "string",
                              "enum": [
                                "owner",
                                "partner",
                                "cxo",
                                "vp",
                                "director",
                                "manager",
                                "senior",
                                "entry",
                                "training",
                                "unpaid"
                              ]
                            }
                          },
                          "exclude": {
                            "type": "array",
                            "items": {
                              "type": "string",
                              "enum": [
                                "owner",
                                "partner",
                                "cxo",
                                "vp",
                                "director",
                                "manager",
                                "senior",
                                "entry",
                                "training",
                                "unpaid"
                              ]
                            }
                          }
                        }
                      },
                      "function": {
                        "description": "The ID of the parameter. Use type DEPARTMENT on the List search parameters route to find out the right ID.\nLinkedin native filter : JOB FUNCTIONS.",
                        "minItems": 1,
                        "type": "array",
                        "items": {
                          "type": "string",
                          "pattern": "^\\d+$"
                        }
                      },
                      "network_distance": {
                        "description": "First, second, third+ degree or GROUP.\nLinkedin native filter : NETWORK RELATIONSHIPS.",
                        "type": "array",
                        "items": {
                          "anyOf": [
                            {
                              "type": "number",
                              "enum": [
                                1,
                                2,
                                3
                              ]
                            },
                            {
                              "type": "string",
                              "enum": [
                                "GROUP"
                              ]
                            }
                          ]
                        }
                      },
                      "spoken_languages": {
                        "type": "array",
                        "items": {
                          "description": "Linkedin native filter : SPOKEN LANGUAGES.",
                          "type": "object",
                          "properties": {
                            "language": {
                              "type": "string"
                            },
                            "priority": {
                              "type": "string",
                              "enum": [
                                "CAN_HAVE",
                                "MUST_HAVE",
                                "DOESNT_HAVE"
                              ]
                            },
                            "scope": {
                              "type": "string",
                              "enum": [
                                "ELEMENTARY",
                                "LIMITED_WORKING",
                                "PROFESSIONAL_WORKING",
                                "NATIVE_OR_BILINGUAL"
                              ]
                            }
                          },
                          "required": [
                            "language"
                          ],
                          "x-scope": {
                            "type": "string",
                            "enum": [
                              "ELEMENTARY",
                              "LIMITED_WORKING",
                              "PROFESSIONAL_WORKING",
                              "NATIVE_OR_BILINGUAL"
                            ]
                          }
                        }
                      },
                      "hide_previously_viewed": {
                        "description": "Linkedin native filter : HIDE PREVIOUSLY VIEWED.",
                        "type": "object",
                        "properties": {
                          "timespan": {
                            "description": "The timespan in days since today for the filter to be applied.",
                            "type": "number"
                          }
                        },
                        "required": [
                          "timespan"
                        ]
                      },
                      "profile_language": {
                        "description": "ISO 639-1 language code.\nLinkedin native filter : PROFILE LANGUAGES.",
                        "type": "array",
                        "items": {
                          "minLength": 2,
                          "maxLength": 2,
                          "type": "string"
                        }
                      },
                      "recently_joined": {
                        "description": "Linkedin native filter : RECENTLY JOINED LINKEDIN.",
                        "type": "array",
                        "items": {
                          "type": "object",
                          "properties": {
                            "min": {
                              "type": "number",
                              "enum": [
                                2,
                                8,
                                15,
                                31
                              ]
                            },
                            "max": {
                              "type": "number",
                              "enum": [
                                1,
                                7,
                                14,
                                30,
                                90
                              ]
                            }
                          }
                        }
                      },
                      "spotlights": {
                        "description": "Linkedin native filter : SPOTLIGHTS. For users with advanced Recruiter subscription.",
                        "type": "array",
                        "items": {
                          "type": "string",
                          "enum": [
                            "OPEN_TO_WORK",
                            "ACTIVE_TALENT",
                            "REDISCOVERED_CANDIDATES",
                            "INTERNAL_CANDIDATES",
                            "INTERESTED_IN_YOUR_COMPANY",
                            "HAVE_COMPANY_CONNECTIONS"
                          ]
                        }
                      },
                      "first_name": {
                        "description": "Linkedin native filter : FIRST NAMES.",
                        "type": "array",
                        "items": {
                          "minLength": 1,
                          "description": "Boolean modifiers can be used to refine your search.\nExample : developers AND product owners NOT managers",
                          "type": "string"
                        }
                      },
                      "last_name": {
                        "description": "Linkedin native filter : LAST NAMES.",
                        "type": "array",
                        "items": {
                          "minLength": 1,
                          "description": "Boolean modifiers can be used to refine your search.\nExample : developers AND product owners NOT managers",
                          "type": "string"
                        }
                      },
                      "has_military_background": {
                        "description": "Linkedin native filter : HAS US MILITARY BACKGROUND.",
                        "type": "boolean"
                      },
                      "past_applicants": {
                        "description": "Linkedin native filter : PAST APPLICANTS.",
                        "type": "boolean"
                      },
                      "hiring_projects": {
                        "description": "Linkedin native filter : PROJECTS.",
                        "type": "object",
                        "properties": {
                          "include": {
                            "description": "The ID of the parameter. Use type HIRING_PROJECTS on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          },
                          "exclude": {
                            "description": "The ID of the parameter. Use type HIRING_PROJECTS on the List search parameters route to find out the right ID.",
                            "minItems": 1,
                            "type": "array",
                            "items": {
                              "type": "string",
                              "pattern": "^\\d+$"
                            }
                          }
                        }
                      },
                      "recruiting_activity": {
                        "type": "array",
                        "items": {
                          "description": "Linkedin native filter : RECRUITING ACTIVITY.",
                          "type": "object",
                          "properties": {
                            "id": {
                              "type": "string",
                              "enum": [
                                "messages",
                                "tags",
                                "notes",
                                "projects",
                                "resumes",
                                "reviews"
                              ]
                            },
                            "priority": {
                              "type": "string",
                              "enum": [
                                "CAN_HAVE",
                                "MUST_HAVE",
                                "DOESNT_HAVE"
                              ]
                            },
                            "timespan": {
                              "description": "The timespan in days since today for the filter to be applied.",
                              "type": "number"
                            }
                          },
                          "required": [
                            "id"
                          ],
                          "x-timespan": {
                            "description": "The timespan in days since today for the filter to be applied.",
                            "type": "number"
                          }
                        }
                      },
                      "notes": {
                        "description": "Linkedin native filter : NOTES.",
                        "type": "array",
                        "items": {
                          "minLength": 1,
                          "type": "string"
                        }
                      }
                    },
                    "required": [
                      "api",
                      "category"
                    ]
                  },
                  {
                    "title": "Search from URL",
                    "type": "object",
                    "properties": {
                      "url": {
                        "description": "Linkedin's public search URL. Setting this parameter will override the entire body.",
                        "type": "string"
                      }
                    },
                    "required": [
                      "url"
                    ]
                  },
                  {
                    "title": "Cursor",
                    "description": "In the case of a long cursor, you may want to set it in the body rather than in the query parameters.",
                    "type": "object",
                    "properties": {
                      "cursor": {
                        "title": "CursorParam",
                        "description": "A cursor for pagination purposes. To get the next page of entries, you need to make a new request and fulfill this field with the cursor received in the preceding request. This process should be repeated until all entries have been retrieved.",
                        "minLength": 1,
                        "type": "string"
                      }
                    },
                    "required": [
                      "cursor"
                    ]
                  }
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
                        "LinkedinSearch"
                      ]
                    },
                    "items": {
                      "type": "array",
                      "items": {
                        "anyOf": [
                          {
                            "type": "object",
                            "properties": {
                              "object": {
                                "type": "string",
                                "enum": [
                                  "SearchResult"
                                ]
                              },
                              "type": {
                                "type": "string",
                                "enum": [
                                  "PEOPLE"
                                ]
                              },
                              "id": {
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
                              "public_profile_url": {
                                "anyOf": [
                                  {
                                    "type": "string"
                                  },
                                  {
                                    "nullable": true
                                  }
                                ]
                              },
                              "profile_url": {
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
                                "anyOf": [
                                  {
                                    "type": "string"
                                  },
                                  {
                                    "nullable": true
                                  }
                                ]
                              },
                              "profile_picture_url_large": {
                                "anyOf": [
                                  {
                                    "type": "string"
                                  },
                                  {
                                    "nullable": true
                                  }
                                ]
                              },
                              "member_urn": {
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
                              "first_name": {
                                "type": "string"
                              },
                              "last_name": {
                                "type": "string"
                              },
                              "network_distance": {
                                "anyOf": [
                                  {
                                    "type": "string",
                                    "enum": [
                                      "SELF"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "DISTANCE_1"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "DISTANCE_2"
                                    ]
                                  },
                                  {
                                    "type": "string",
                                    "enum": [
                                      "DISTANCE_3"
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
                              "location": {
                                "anyOf": [
                                  {
                                    "type": "string"
                                  },
                                  {
                                    "nullable": true
                                  }
                                ]
                              },
                              "industry": {
                                "anyOf": [
                                  {
                                    "type": "string"
                                  },
                                  {
                                    "nullable": true
                                  }
                                ]
                              },
                              "keywords_match": {
                                "type": "string"
                              },
                              "headline": {
                                "type": "string"
                              },
                              "connections_count": {
                                "type": "number"
                              },
                              "followers_count": {
                                "type": "number"
                              },
                              "pending_invitation": {
                                "type": "boolean"
                              },
                              "can_send_inmail": {
                                "type": "boolean"
                              },
                              "hiddenCandidate": {
                                "type": "boolean"
                              },
                              "interestLikelihood": {
                                "type": "string"
                              },
                              "privacySettings": {
                                "type": "object",
                                "properties": {
                                  "allowConnectionsBrowse": {
                                    "type": "boolean"
                                  },
                                  "showPremiumSubscriberIcon": {
                                    "type": "boolean"
                                  }
                                },
                                "required": [
                                  "allowConnectionsBrowse",
                                  "showPremiumSubscriberIcon"
                                ]
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
                                    }
                                  },
                                  "required": [
                                    "name",
                                    "endorsement_count"
                                  ]
                                }
                              },
                              "recruiter_candidate_id": {
                                "type": "string"
                              },
                              "recruiter_pipeline_category": {
                                "type": "string"
                              },
                              "premium": {
                                "type": "boolean"
                              },
                              "verified": {
                                "type": "boolean"
                              },
                              "open_profile": {
                                "type": "boolean"
                              },
                              "shared_connections_count": {
                                "type": "number"
                              },
                              "recent_posts_count": {
                                "type": "number"
                              },
                              "recently_hired": {
                                "type": "boolean"
                              },
                              "mentioned_in_the_news": {
                                "type": "boolean"
                              },
                              "last_outreach_activity": {
                                "type": "object",
                                "properties": {
                                  "type": {
                                    "anyOf": [
                                      {
                                        "type": "string",
                                        "enum": [
                                          "SEND_MESSAGE"
                                        ]
                                      },
                                      {
                                        "type": "string",
                                        "enum": [
                                          "ACCEPT_INVITATION"
                                        ]
                                      }
                                    ]
                                  },
                                  "performed_at": {
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "type",
                                  "performed_at"
                                ]
                              },
                              "current_positions": {
                                "type": "array",
                                "items": {
                                  "type": "object",
                                  "properties": {
                                    "company": {
                                      "type": "string"
                                    },
                                    "company_id": {
                                      "anyOf": [
                                        {
                                          "type": "string"
                                        },
                                        {
                                          "nullable": true
                                        }
                                      ]
                                    },
                                    "description": {
                                      "anyOf": [
                                        {
                                          "type": "string"
                                        },
                                        {
                                          "nullable": true
                                        }
                                      ]
                                    },
                                    "role": {
                                      "type": "string"
                                    },
                                    "location": {
                                      "anyOf": [
                                        {
                                          "type": "string"
                                        },
                                        {
                                          "nullable": true
                                        }
                                      ]
                                    },
                                    "industry": {
                                      "type": "array",
                                      "items": {
                                        "type": "string"
                                      }
                                    },
                                    "tenure_at_role": {
                                      "type": "object",
                                      "properties": {
                                        "years": {
                                          "type": "number"
                                        },
                                        "months": {
                                          "type": "number"
                                        }
                                      }
                                    },
                                    "tenure_at_company": {
                                      "type": "object",
                                      "properties": {
                                        "years": {
                                          "type": "number"
                                        },
                                        "months": {
                                          "type": "number"
                                        }
                                      }
                                    },
                                    "start": {
                                      "type": "object",
                                      "properties": {
                                        "year": {
                                          "type": "number"
                                        },
                                        "month": {
                                          "type": "number"
                                        }
                                      }
                                    },
                                    "end": {
                                      "type": "object",
                                      "properties": {
                                        "year": {
                                          "type": "number"
                                        },
                                        "month": {
                                          "type": "number"
                                        }
                                      }
                                    },
                                    "skills": {
                                      "anyOf": [
                                        {
                                          "type": "array",
                                          "items": {
                                            "type": "object",
                                            "properties": {
                                              "name": {
                                                "type": "string"
                                              },
                                              "endorsement_count": {
                                                "type": "number"
                                              }
                                            },
                                            "required": [
                                              "name",
                                              "endorsement_count"
                                            ]
                                          }
                                        },
                                        {
                                          "nullable": true
                                        }
                                      ]
                                    }
                                  },
                                  "required": [
                                    "company",
                                    "company_id",
                                    "description",
                                    "role",
                                    "location",
                                    "industry",
                                    "skills"
                                  ]
                                }
                              },
                              "education": {
                                "type": "array",
                                "items": {
                                  "type": "object",
                                  "properties": {
                                    "degree": {
                                      "anyOf": [
                                        {
                                          "type": "string"
                                        },
                                        {
                                          "nullable": true
                                        }
                                      ]
                                    },
                                    "field_of_study": {
                                      "anyOf": [
                                        {
                                          "type": "string"
                                        },
                                        {
                                          "nullable": true
                                        }
                                      ]
                                    },
                                    "school": {
                                      "type": "string"
                                    },
                                    "school_id": {
                                      "anyOf": [
                                        {
                                          "type": "string"
                                        },
                                        {
                                          "nullable": true
                                        }
                                      ]
                                    },
                                    "start": {
                                      "type": "object",
                                      "properties": {
                                        "year": {
                                          "type": "number"
                                        },
                                        "month": {
                                          "type": "number"
                                        }
                                      }
                                    },
                                    "end": {
                                      "type": "object",
                                      "properties": {
                                        "year": {
                                          "type": "number"
                                        },
                                        "month": {
                                          "type": "number"
                                        }
                                      }
                                    },
                                    "school_details": {
                                      "type": "object",
                                      "properties": {
                                        "name": {
                                          "type": "string"
                                        },
                                        "employeeCount": {
                                          "type": "number"
                                        },
                                        "location": {
                                          "type": "string"
                                        },
                                        "description": {
                                          "type": "string"
                                        },
                                        "url": {
                                          "type": "string"
                                        },
                                        "logo": {
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
                                        "employeeCount",
                                        "location",
                                        "description",
                                        "url",
                                        "logo"
                                      ]
                                    }
                                  },
                                  "required": [
                                    "degree",
                                    "field_of_study",
                                    "school",
                                    "school_id",
                                    "start"
                                  ]
                                }
                              },
                              "work_experience": {
                                "type": "array",
                                "items": {
                                  "type": "object",
                                  "properties": {
                                    "company": {
                                      "type": "string"
                                    },
                                    "company_id": {
                                      "anyOf": [
                                        {
                                          "type": "string"
                                        },
                                        {
                                          "nullable": true
                                        }
                                      ]
                                    },
                                    "role": {
                                      "type": "string"
                                    },
                                    "industry": {
                                      "anyOf": [
                                        {
                                          "type": "string"
                                        },
                                        {
                                          "nullable": true
                                        }
                                      ]
                                    },
                                    "start": {
                                      "type": "object",
                                      "properties": {
                                        "year": {
                                          "type": "number"
                                        },
                                        "month": {
                                          "type": "number"
                                        }
                                      }
                                    },
                                    "end": {
                                      "type": "object",
                                      "properties": {
                                        "year": {
                                          "type": "number"
                                        },
                                        "month": {
                                          "type": "number"
                                        }
                                      }
                                    },
                                    "skills": {
                                      "anyOf": [
                                        {
                                          "type": "array",
                                          "items": {
                                            "type": "object",
                                            "properties": {
                                              "name": {
                                                "type": "string"
                                              },
                                              "endorsement_count": {
                                                "type": "number"
                                              }
                                            },
                                            "required": [
                                              "name",
                                              "endorsement_count"
                                            ]
                                          }
                                        },
                                        {
                                          "nullable": true
                                        }
                                      ]
                                    }
                                  },
                                  "required": [
                                    "company",
                                    "company_id",
                                    "role",
                                    "industry",
                                    "start",
                                    "skills"
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
                                    "organization_id": {
                                      "anyOf": [
                                        {
                                          "type": "string"
                                        },
                                        {
                                          "nullable": true
                                        }
                                      ]
                                    },
                                    "url": {
                                      "type": "string"
                                    },
                                    "start": {
                                      "type": "object",
                                      "properties": {
                                        "year": {
                                          "type": "number"
                                        },
                                        "month": {
                                          "type": "string"
                                        }
                                      },
                                      "required": [
                                        "year"
                                      ]
                                    },
                                    "end": {
                                      "type": "object",
                                      "properties": {
                                        "year": {
                                          "type": "number"
                                        },
                                        "month": {
                                          "type": "string"
                                        }
                                      },
                                      "required": [
                                        "year"
                                      ]
                                    }
                                  },
                                  "required": [
                                    "name",
                                    "organization",
                                    "organization_id"
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
                                      "type": "object",
                                      "properties": {
                                        "year": {
                                          "type": "number"
                                        },
                                        "month": {
                                          "type": "string"
                                        }
                                      },
                                      "required": [
                                        "year"
                                      ]
                                    },
                                    "end": {
                                      "type": "object",
                                      "properties": {
                                        "year": {
                                          "type": "number"
                                        },
                                        "month": {
                                          "type": "string"
                                        }
                                      },
                                      "required": [
                                        "year"
                                      ]
                                    }
                                  },
                                  "required": [
                                    "name",
                                    "description",
                                    "skills"
                                  ]
                                }
                              },
                              "interests": {
                                "type": "string"
                              }
                            },
                            "required": [
                              "object",
                              "type",
                              "id",
                              "public_identifier",
                              "public_profile_url",
                              "profile_url",
                              "profile_picture_url",
                              "profile_picture_url_large",
                              "member_urn",
                              "name",
                              "network_distance",
                              "location",
                              "industry",
                              "headline"
                            ]
                          },
                          {
                            "type": "object",
                            "properties": {
                              "object": {
                                "type": "string",
                                "enum": [
                                  "SearchResult"
                                ]
                              },
                              "type": {
                                "type": "string",
                                "enum": [
                                  "COMPANY"
                                ]
                              },
                              "id": {
                                "type": "string"
                              },
                              "name": {
                                "type": "string"
                              },
                              "location": {
                                "anyOf": [
                                  {
                                    "type": "string"
                                  },
                                  {
                                    "nullable": true
                                  }
                                ]
                              },
                              "profile_url": {
                                "type": "string"
                              },
                              "industry": {
                                "type": "string"
                              },
                              "summary": {
                                "anyOf": [
                                  {
                                    "type": "string"
                                  },
                                  {
                                    "nullable": true
                                  }
                                ]
                              },
                              "followers_count": {
                                "type": "number"
                              },
                              "job_offers_count": {
                                "type": "number"
                              },
                              "headcount": {
                                "type": "string"
                              },
                              "revenue_range": {
                                "type": "object",
                                "properties": {
                                  "min": {
                                    "type": "number"
                                  },
                                  "max": {
                                    "type": "number"
                                  },
                                  "currency": {
                                    "type": "string"
                                  }
                                },
                                "required": [
                                  "min",
                                  "max",
                                  "currency"
                                ]
                              }
                            },
                            "required": [
                              "object",
                              "type",
                              "id",
                              "name",
                              "location",
                              "profile_url",
                              "industry",
                              "summary"
                            ]
                          },
                          {
                            "type": "object",
                            "properties": {
                              "object": {
                                "type": "string",
                                "enum": [
                                  "SearchResult"
                                ]
                              },
                              "type": {
                                "type": "string",
                                "enum": [
                                  "POST"
                                ]
                              },
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
                              "object",
                              "type",
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
                              "object": {
                                "type": "string",
                                "enum": [
                                  "SearchResult"
                                ]
                              },
                              "type": {
                                "type": "string",
                                "enum": [
                                  "JOB"
                                ]
                              },
                              "id": {
                                "type": "string"
                              },
                              "reference_id": {
                                "type": "string"
                              },
                              "title": {
                                "type": "string"
                              },
                              "location": {
                                "anyOf": [
                                  {
                                    "type": "string"
                                  },
                                  {
                                    "nullable": true
                                  }
                                ]
                              },
                              "posted_at": {
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
                              "reposted": {
                                "type": "boolean"
                              },
                              "url": {
                                "type": "string"
                              },
                              "promoted": {
                                "type": "boolean"
                              },
                              "benefits": {
                                "type": "array",
                                "items": {
                                  "type": "string"
                                }
                              },
                              "easy_apply": {
                                "type": "boolean"
                              },
                              "company": {
                                "anyOf": [
                                  {
                                    "type": "object",
                                    "properties": {
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
                                      "profile_url": {
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
                                      "id",
                                      "public_identifier",
                                      "name",
                                      "profile_url",
                                      "profile_picture_url"
                                    ]
                                  },
                                  {
                                    "nullable": true
                                  }
                                ]
                              }
                            },
                            "required": [
                              "object",
                              "type",
                              "id",
                              "reference_id",
                              "title",
                              "location",
                              "posted_at",
                              "reposted",
                              "url",
                              "promoted",
                              "benefits",
                              "easy_apply",
                              "company"
                            ]
                          }
                        ]
                      }
                    },
                    "config": {
                      "type": "object",
                      "properties": {
                        "params": {
                          "anyOf": [
                            {
                              "title": "Classic - People",
                              "type": "object",
                              "properties": {
                                "api": {
                                  "type": "string",
                                  "enum": [
                                    "classic"
                                  ]
                                },
                                "category": {
                                  "type": "string",
                                  "enum": [
                                    "people"
                                  ]
                                },
                                "keywords": {
                                  "description": "Linkedin native filter : KEYWORDS.",
                                  "type": "string"
                                },
                                "industry": {
                                  "description": "The ID of the parameter. Use type INDUSTRY on the List search parameters route to find out the right ID.\nLinkedin native filter : INDUSTRY.",
                                  "minItems": 1,
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "pattern": "^\\d+$"
                                  }
                                },
                                "location": {
                                  "description": "The ID of the parameter. Use type LOCATION on the List search parameters route to find out the right ID.\nLinkedin native filter : LOCATIONS.",
                                  "minItems": 1,
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "pattern": "^\\d+$"
                                  }
                                },
                                "profile_language": {
                                  "description": "ISO 639-1 language code.\nLinkedin native filter : PROFILE LANGUAGE.",
                                  "type": "array",
                                  "items": {
                                    "minLength": 2,
                                    "maxLength": 2,
                                    "type": "string"
                                  }
                                },
                                "network_distance": {
                                  "description": "First, second or third+ degree.\nLinkedin native filter : CONNECTIONS.",
                                  "type": "array",
                                  "items": {
                                    "type": "number",
                                    "enum": [
                                      1,
                                      2,
                                      3
                                    ]
                                  }
                                },
                                "company": {
                                  "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.\nLinkedin native filter : CURRENT COMPANY.",
                                  "minItems": 1,
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "pattern": "^\\d+$"
                                  }
                                },
                                "past_company": {
                                  "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.\nLinkedin native filter : PAST COMPANY.",
                                  "minItems": 1,
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "pattern": "^\\d+$"
                                  }
                                },
                                "school": {
                                  "description": "The ID of the parameter. Use type SCHOOL on the List search parameters route to find out the right ID.\nLinkedin native filter : SCHOOL.",
                                  "minItems": 1,
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "pattern": "^\\d+$"
                                  }
                                },
                                "service": {
                                  "description": "The ID of the parameter. Use type SERVICE on the List search parameters route to find out the right ID.\nLinkedin native filter : SERVICE CATEGORIES.",
                                  "minItems": 1,
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "pattern": "^\\d+$"
                                  }
                                },
                                "connections_of": {
                                  "description": "The ID of the parameter. Use type CONNECTIONS on the List search parameters route to find out the right ID.\nLinkedin native filter : CONNECTIONS OF.",
                                  "minItems": 1,
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "pattern": "^.+$"
                                  }
                                },
                                "followers_of": {
                                  "description": "The ID of the parameter. Use type PEOPLE on the List search parameters route to find out the right ID.\nLinkedin native filter : FOLLOWERS OF.",
                                  "minItems": 1,
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "pattern": "^.+$"
                                  }
                                },
                                "open_to": {
                                  "description": "Linkedin native filter : OPEN TO.",
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "enum": [
                                      "proBono",
                                      "boardMember"
                                    ]
                                  }
                                },
                                "advanced_keywords": {
                                  "type": "object",
                                  "properties": {
                                    "first_name": {
                                      "description": "Linkedin native filter : KEYWORDS / FIRST NAME.",
                                      "type": "string"
                                    },
                                    "last_name": {
                                      "description": "Linkedin native filter : KEYWORDS / LAST NAME.",
                                      "type": "string"
                                    },
                                    "title": {
                                      "description": "Linkedin native filter : KEYWORDS / TITLE.",
                                      "type": "string"
                                    },
                                    "company": {
                                      "description": "Linkedin native filter : KEYWORDS / COMPANY.",
                                      "type": "string"
                                    },
                                    "school": {
                                      "description": "Linkedin native filter : KEYWORDS / SCHOOL.",
                                      "type": "string"
                                    }
                                  }
                                }
                              },
                              "required": [
                                "api",
                                "category"
                              ]
                            },
                            {
                              "title": "Classic - Companies",
                              "type": "object",
                              "properties": {
                                "api": {
                                  "type": "string",
                                  "enum": [
                                    "classic"
                                  ]
                                },
                                "category": {
                                  "type": "string",
                                  "enum": [
                                    "companies"
                                  ]
                                },
                                "keywords": {
                                  "description": "Linkedin native filter : KEYWORDS.",
                                  "type": "string"
                                },
                                "industry": {
                                  "description": "The ID of the parameter. Use type INDUSTRY on the List search parameters route to find out the right ID.\nLinkedin native filter : INDUSTRY.",
                                  "minItems": 1,
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "pattern": "^\\d+$"
                                  }
                                },
                                "location": {
                                  "description": "The ID of the parameter. Use type LOCATION on the List search parameters route to find out the right ID.\nLinkedin native filter : LOCATIONS.",
                                  "minItems": 1,
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "pattern": "^\\d+$"
                                  }
                                },
                                "has_job_offers": {
                                  "description": "Linkedin native filter : JOB LISTINGS ON LINKEDIN.",
                                  "type": "boolean"
                                },
                                "headcount": {
                                  "description": "Linkedin native filter : COMPANY SIZE.",
                                  "type": "array",
                                  "items": {
                                    "type": "object",
                                    "properties": {
                                      "min": {
                                        "type": "number",
                                        "enum": [
                                          1,
                                          11,
                                          51,
                                          201,
                                          501,
                                          1001,
                                          5001,
                                          10001
                                        ]
                                      },
                                      "max": {
                                        "type": "number",
                                        "enum": [
                                          10,
                                          50,
                                          200,
                                          500,
                                          1000,
                                          5000,
                                          10000
                                        ]
                                      }
                                    }
                                  }
                                },
                                "network_distance": {
                                  "description": "First, second or third+ degree.\nLinkedin native filter : CONNECTIONS.",
                                  "type": "array",
                                  "items": {
                                    "type": "number",
                                    "enum": [
                                      1,
                                      2,
                                      3
                                    ]
                                  }
                                }
                              },
                              "required": [
                                "api",
                                "category"
                              ]
                            },
                            {
                              "title": "Classic - POSTS",
                              "type": "object",
                              "properties": {
                                "api": {
                                  "type": "string",
                                  "enum": [
                                    "classic"
                                  ]
                                },
                                "category": {
                                  "type": "string",
                                  "enum": [
                                    "posts"
                                  ]
                                },
                                "keywords": {
                                  "description": "Linkedin native filter : KEYWORDS.",
                                  "type": "string"
                                },
                                "sort_by": {
                                  "description": "Default value is relevance.\nLinkedin native filter : SORT BY.",
                                  "type": "string",
                                  "enum": [
                                    "relevance",
                                    "date"
                                  ]
                                },
                                "date_posted": {
                                  "description": "Linkedin native filter : DATE POSTED.",
                                  "type": "string",
                                  "enum": [
                                    "past_day",
                                    "past_week",
                                    "past_month"
                                  ]
                                },
                                "content_type": {
                                  "description": "Linkedin native filter : CONTENT TYPE.",
                                  "type": "string",
                                  "enum": [
                                    "videos",
                                    "images",
                                    "live_videos",
                                    "collaborative_articles",
                                    "documents"
                                  ]
                                },
                                "posted_by": {
                                  "minProperties": 1,
                                  "type": "object",
                                  "properties": {
                                    "member": {
                                      "description": "The ID of the parameter. Use type PEOPLE on the List search parameters route to find out the right ID.\nLinkedin native filter : FROM MEMBER.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^.+$"
                                      }
                                    },
                                    "company": {
                                      "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.\nLinkedin native filter : FROM COMPANY.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    },
                                    "me": {
                                      "description": "Linkedin native filter : POSTED BY [ME].",
                                      "type": "boolean"
                                    },
                                    "first_connections": {
                                      "description": "Linkedin native filter : POSTED BY [1ST CONNECTIONS].",
                                      "type": "boolean"
                                    },
                                    "people_you_follow": {
                                      "description": "Linkedin native filter : POSTED BY [PEOPLE YOU FOLLOW].",
                                      "type": "boolean"
                                    }
                                  }
                                },
                                "mentioning": {
                                  "minProperties": 1,
                                  "type": "object",
                                  "properties": {
                                    "member": {
                                      "description": "The ID of the parameter. Use type PEOPLE on the List search parameters route to find out the right ID.\nLinkedin native filter : MENTIONING MEMBER.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^.+$"
                                      }
                                    },
                                    "company": {
                                      "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.\nLinkedin native filter : MENTIONING COMPANY.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    }
                                  }
                                },
                                "author": {
                                  "minProperties": 1,
                                  "type": "object",
                                  "properties": {
                                    "industry": {
                                      "description": "The ID of the parameter. Use type INDUSTRY on the List search parameters route to find out the right ID.\nLinkedin native filter : AUTHOR INDUSTRY.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    },
                                    "company": {
                                      "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.\nLinkedin native filter : AUTHOR COMPANY.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    },
                                    "keywords": {
                                      "description": "Linkedin native filter : AUTHOR KEYWORDS.",
                                      "type": "string"
                                    }
                                  }
                                }
                              },
                              "required": [
                                "api",
                                "category"
                              ]
                            },
                            {
                              "title": "Classic - JOBS",
                              "type": "object",
                              "properties": {
                                "api": {
                                  "type": "string",
                                  "enum": [
                                    "classic"
                                  ]
                                },
                                "category": {
                                  "type": "string",
                                  "enum": [
                                    "jobs"
                                  ]
                                },
                                "keywords": {
                                  "description": "Linkedin native filter : KEYWORDS.",
                                  "type": "string"
                                },
                                "sort_by": {
                                  "description": "Default value is relevance.\nLinkedin native filter : SORT BY.",
                                  "type": "string",
                                  "enum": [
                                    "relevance",
                                    "date"
                                  ]
                                },
                                "date_posted": {
                                  "description": "The timespan in days since today for the filter to be applied.\nLinkedin native filter : DATE POSTED.",
                                  "type": "number"
                                },
                                "region": {
                                  "description": "The ID of the parameter. Use type LOCATION on the List search parameters route to find out the right ID.\nLinkedin native filter : GLOBAL LOCATION.",
                                  "type": "string",
                                  "pattern": "^\\d+$"
                                },
                                "location": {
                                  "description": "The ID of the parameter. Use type LOCATION on the List search parameters route to find out the right ID.\nLinkedin native filter : LOCATION.",
                                  "minItems": 1,
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "pattern": "^\\d+$"
                                  }
                                },
                                "location_within_area": {
                                  "description": "The search zone around the location in miles.\nLinkedin native filter : DISTANCE.",
                                  "type": "number"
                                },
                                "industry": {
                                  "description": "The ID of the parameter. Use type INDUSTRY on the List search parameters route to find out the right ID.\nLinkedin native filter : INDUSTRY.",
                                  "minItems": 1,
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "pattern": "^\\d+$"
                                  }
                                },
                                "seniority": {
                                  "description": "Linkedin native filter : EXPERIENCE LEVEL.",
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "enum": [
                                      "executive",
                                      "director",
                                      "mid_senior",
                                      "associate",
                                      "entry",
                                      "intern"
                                    ]
                                  }
                                },
                                "function": {
                                  "description": "The ID of the parameter. Use type JOB_FUNCTION on the List search parameters route to find out the right ID.\nLinkedin native filter : JOB FUNCTION.",
                                  "minItems": 1,
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "pattern": "^[a-z]+$"
                                  }
                                },
                                "role": {
                                  "description": "The ID of the parameter. Use type JOB_TITLE on the List search parameters route to find out the right ID.\nLinkedin native filter : TITLE.",
                                  "minItems": 1,
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "pattern": "^\\d+$"
                                  }
                                },
                                "job_type": {
                                  "description": "Linkedin native filter : JOB TYPE.",
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "enum": [
                                      "full_time",
                                      "part_time",
                                      "contract",
                                      "temporary",
                                      "volunteer",
                                      "internship",
                                      "other"
                                    ]
                                  }
                                },
                                "company": {
                                  "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.\nLinkedin native filter : COMPANY.",
                                  "minItems": 1,
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "pattern": "^\\d+$"
                                  }
                                },
                                "presence": {
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "enum": [
                                      "on_site",
                                      "hybrid",
                                      "remote"
                                    ]
                                  }
                                },
                                "easy_apply": {
                                  "description": "Linkedin native filter : EASY APPLY.",
                                  "type": "boolean"
                                },
                                "has_verifications": {
                                  "description": "Linkedin native filter : HAS VERIFICATIONS.",
                                  "type": "boolean"
                                },
                                "under_10_applicants": {
                                  "description": "Linkedin native filter : UNDER 10 APPLICANTS.",
                                  "type": "boolean"
                                },
                                "in_your_network": {
                                  "description": "Linkedin native filter : IN YOUR NETWORK.",
                                  "type": "boolean"
                                },
                                "fair_chance_employer": {
                                  "description": "Linkedin native filter : FAIR CHANCE EMPLOYER.",
                                  "type": "boolean"
                                },
                                "benefits": {
                                  "description": "Linkedin native filter : BENEFITS.",
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "enum": [
                                      "medical_insurance",
                                      "vision_insurance",
                                      "dental_insurance",
                                      "disability_insurance",
                                      "401(k)",
                                      "pension_plan",
                                      "paid_maternity_leave",
                                      "paid_paternity_leave",
                                      "commuter_benefits",
                                      "student_loan_assistance",
                                      "tuition_assistance"
                                    ]
                                  }
                                },
                                "commitments": {
                                  "description": "Linkedin native filter : COMMITMENTS.",
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "enum": [
                                      "career_growth_and_learning",
                                      "diversity_equity_and_inclusion",
                                      "environmental_sustainability",
                                      "social_impact",
                                      "work_life_balance"
                                    ]
                                  }
                                },
                                "minimum_salary": {
                                  "description": "Linkedin native filter : SALARY.",
                                  "anyOf": [
                                    {
                                      "title": "Dollar based",
                                      "type": "object",
                                      "properties": {
                                        "currency": {
                                          "anyOf": [
                                            {
                                              "type": "string",
                                              "enum": [
                                                "USD"
                                              ]
                                            },
                                            {
                                              "type": "string",
                                              "enum": [
                                                "AUD"
                                              ]
                                            },
                                            {
                                              "type": "string",
                                              "enum": [
                                                "CAD"
                                              ]
                                            }
                                          ]
                                        },
                                        "value": {
                                          "description": "Value in thousands of dollars.",
                                          "type": "number",
                                          "enum": [
                                            40,
                                            60,
                                            80,
                                            100,
                                            120,
                                            140,
                                            160,
                                            180,
                                            200
                                          ]
                                        }
                                      },
                                      "required": [
                                        "currency",
                                        "value"
                                      ]
                                    },
                                    {
                                      "title": "Pound based",
                                      "type": "object",
                                      "properties": {
                                        "currency": {
                                          "type": "string",
                                          "enum": [
                                            "GBP"
                                          ]
                                        },
                                        "value": {
                                          "description": "Value in thousands of pounds.",
                                          "type": "number",
                                          "enum": [
                                            20,
                                            30,
                                            40,
                                            50,
                                            60,
                                            70,
                                            80,
                                            90,
                                            100
                                          ]
                                        }
                                      },
                                      "required": [
                                        "currency",
                                        "value"
                                      ]
                                    }
                                  ]
                                }
                              },
                              "required": [
                                "api",
                                "category"
                              ]
                            },
                            {
                              "title": "Sales Navigator - People",
                              "type": "object",
                              "properties": {
                                "api": {
                                  "type": "string",
                                  "enum": [
                                    "sales_navigator"
                                  ]
                                },
                                "category": {
                                  "type": "string",
                                  "enum": [
                                    "people"
                                  ]
                                },
                                "keywords": {
                                  "description": "Linkedin native filter : KEYWORDS.",
                                  "type": "string"
                                },
                                "last_viewed_at": {
                                  "description": "Unix timestamp to be used with a saved search to filter new results from this date.",
                                  "type": "number"
                                },
                                "saved_search_id": {
                                  "description": "The ID of the parameter. Use type SAVED_SEARCHES on the List search parameters route to find out the right ID.\nOverrides all other parameters.",
                                  "type": "string",
                                  "pattern": "^\\d+$"
                                },
                                "recent_search_id": {
                                  "description": "The ID of the parameter. Use type RECENT_SEARCHES on the List search parameters route to find out the right ID.\nOverrides all other parameters.",
                                  "type": "string",
                                  "pattern": "^\\d+$"
                                },
                                "location": {
                                  "description": "Linkedin native filter : GEOGRAPHY.",
                                  "type": "object",
                                  "properties": {
                                    "include": {
                                      "description": "The ID of the parameter. Use type LOCATION on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    },
                                    "exclude": {
                                      "description": "The ID of the parameter. Use type LOCATION on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    }
                                  }
                                },
                                "location_by_postal_code": {
                                  "type": "object",
                                  "properties": {
                                    "include": {
                                      "description": "The ID of the parameter. Use type POSTAL_CODE on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    },
                                    "exclude": {
                                      "description": "The ID of the parameter. Use type POSTAL_CODE on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    },
                                    "within_area": {
                                      "description": "The search zone around the location in miles.",
                                      "type": "number"
                                    }
                                  }
                                },
                                "industry": {
                                  "description": "Linkedin native filter : INDUSTRY.",
                                  "type": "object",
                                  "properties": {
                                    "include": {
                                      "description": "The ID of the parameter. Use type SALES_INDUSTRY on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    },
                                    "exclude": {
                                      "description": "The ID of the parameter. Use type SALES_INDUSTRY on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    }
                                  }
                                },
                                "first_name": {
                                  "description": "Linkedin native filter : FIRST NAME.",
                                  "type": "string"
                                },
                                "last_name": {
                                  "description": "Linkedin native filter : LAST NAME.",
                                  "type": "string"
                                },
                                "tenure": {
                                  "description": "Linkedin native filter : YEARS OF EXPERIENCE.",
                                  "type": "array",
                                  "items": {
                                    "type": "object",
                                    "properties": {
                                      "min": {
                                        "type": "number",
                                        "enum": [
                                          0,
                                          1,
                                          3,
                                          6,
                                          10
                                        ]
                                      },
                                      "max": {
                                        "type": "number",
                                        "enum": [
                                          1,
                                          2,
                                          5,
                                          10
                                        ]
                                      }
                                    }
                                  }
                                },
                                "groups": {
                                  "description": "The ID of the parameter. Use type GROUPS on the List search parameters route to find out the right ID.\nLinkedin native filter : GROUPS.",
                                  "minItems": 1,
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "pattern": "^\\d+$"
                                  }
                                },
                                "school": {
                                  "description": "Linkedin native filter : SCHOOL.",
                                  "type": "object",
                                  "properties": {
                                    "include": {
                                      "description": "The ID of the parameter. Use type SCHOOL on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    },
                                    "exclude": {
                                      "description": "The ID of the parameter. Use type SCHOOL on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    }
                                  }
                                },
                                "profile_language": {
                                  "description": "ISO 639-1 language code.\nLinkedin native filter : PROFILE LANGUAGE.",
                                  "type": "array",
                                  "items": {
                                    "minLength": 2,
                                    "maxLength": 2,
                                    "type": "string"
                                  }
                                },
                                "company": {
                                  "description": "Linkedin native filter : CURRENT COMPANY.",
                                  "type": "object",
                                  "properties": {
                                    "include": {
                                      "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.\nYou can also set a plain text company name instead.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": ".+"
                                      }
                                    },
                                    "exclude": {
                                      "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.\nYou can also set a plain text company name instead.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": ".+"
                                      }
                                    }
                                  }
                                },
                                "company_headcount": {
                                  "description": "Linkedin native filter : COMPANY HEADCOUNT.",
                                  "type": "array",
                                  "items": {
                                    "type": "object",
                                    "properties": {
                                      "min": {
                                        "type": "number",
                                        "enum": [
                                          1,
                                          11,
                                          51,
                                          201,
                                          501,
                                          1001,
                                          5001,
                                          10001
                                        ]
                                      },
                                      "max": {
                                        "type": "number",
                                        "enum": [
                                          10,
                                          50,
                                          200,
                                          500,
                                          1000,
                                          5000,
                                          10000
                                        ]
                                      }
                                    }
                                  }
                                },
                                "company_type": {
                                  "description": "Linkedin native filter : COMPANY TYPE.",
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "enum": [
                                      "public_company",
                                      "privately_held",
                                      "non_profit",
                                      "educational_institution",
                                      "partnership",
                                      "self_employed",
                                      "self_owned",
                                      "government_agency"
                                    ]
                                  }
                                },
                                "company_location": {
                                  "description": "Linkedin native filter : COMPANY HEADQUARTERS LOCATION.",
                                  "type": "object",
                                  "properties": {
                                    "include": {
                                      "description": "The ID of the parameter. Use type LOCATION on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    },
                                    "exclude": {
                                      "description": "The ID of the parameter. Use type LOCATION on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    }
                                  }
                                },
                                "tenure_at_company": {
                                  "description": "Linkedin native filter : YEARS IN CURRENT COMPANY.",
                                  "type": "array",
                                  "items": {
                                    "type": "object",
                                    "properties": {
                                      "min": {
                                        "type": "number",
                                        "enum": [
                                          0,
                                          1,
                                          3,
                                          6,
                                          10
                                        ]
                                      },
                                      "max": {
                                        "type": "number",
                                        "enum": [
                                          1,
                                          2,
                                          5,
                                          10
                                        ]
                                      }
                                    }
                                  }
                                },
                                "past_company": {
                                  "description": "Linkedin native filter : PAST COMPANY.",
                                  "type": "object",
                                  "properties": {
                                    "include": {
                                      "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.\nYou can also set a plain text company name instead.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": ".+"
                                      }
                                    },
                                    "exclude": {
                                      "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.\nYou can also set a plain text company name instead.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": ".+"
                                      }
                                    }
                                  }
                                },
                                "function": {
                                  "description": "Linkedin native filter : FUNCTION.",
                                  "type": "object",
                                  "properties": {
                                    "include": {
                                      "description": "The ID of the parameter. Use type DEPARTMENT on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    },
                                    "exclude": {
                                      "description": "The ID of the parameter. Use type DEPARTMENT on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    }
                                  }
                                },
                                "role": {
                                  "description": "Linkedin native filter : CURRENT JOB TITLE.",
                                  "type": "object",
                                  "properties": {
                                    "include": {
                                      "description": "The ID of the parameter. Use type JOB_TITLE on the List search parameters route to find out the right ID.\nYou can also set a plain text job title instead.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": ".+"
                                      }
                                    },
                                    "exclude": {
                                      "description": "The ID of the parameter. Use type JOB_TITLE on the List search parameters route to find out the right ID.\nYou can also set a plain text job title instead.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": ".+"
                                      }
                                    }
                                  }
                                },
                                "tenure_at_role": {
                                  "description": "Linkedin native filter : YEARS IN CURRENT POSITION.",
                                  "type": "array",
                                  "items": {
                                    "type": "object",
                                    "properties": {
                                      "min": {
                                        "type": "number",
                                        "enum": [
                                          0,
                                          1,
                                          3,
                                          6,
                                          10
                                        ]
                                      },
                                      "max": {
                                        "type": "number",
                                        "enum": [
                                          1,
                                          2,
                                          5,
                                          10
                                        ]
                                      }
                                    }
                                  }
                                },
                                "seniority": {
                                  "description": "Linkedin native filter : SENIORITY LEVEL.",
                                  "type": "object",
                                  "properties": {
                                    "include": {
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "enum": [
                                          "owner/partner",
                                          "cxo",
                                          "vice_president",
                                          "director",
                                          "experienced_manager",
                                          "entry_level_manager",
                                          "strategic",
                                          "senior",
                                          "entry_level",
                                          "in_training"
                                        ]
                                      }
                                    },
                                    "exclude": {
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "enum": [
                                          "owner/partner",
                                          "cxo",
                                          "vice_president",
                                          "director",
                                          "experienced_manager",
                                          "entry_level_manager",
                                          "strategic",
                                          "senior",
                                          "entry_level",
                                          "in_training"
                                        ]
                                      }
                                    }
                                  }
                                },
                                "past_role": {
                                  "description": "Linkedin native filter : PAST JOB TITLE.",
                                  "type": "object",
                                  "properties": {
                                    "include": {
                                      "description": "The ID of the parameter. Use type JOB_TITLE on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    },
                                    "exclude": {
                                      "description": "The ID of the parameter. Use type JOB_TITLE on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    }
                                  }
                                },
                                "following_your_company": {
                                  "description": "Linkedin native filter : FOLLOWING YOUR COMPANY.",
                                  "type": "boolean"
                                },
                                "viewed_your_profile_recently": {
                                  "description": "Linkedin native filter : VIEWED YOUR PROFILE RECENTLY.",
                                  "type": "boolean"
                                },
                                "network_distance": {
                                  "description": "First, second, third+ degree or GROUP.\nLinkedin native filter : CONNECTION.",
                                  "type": "array",
                                  "items": {
                                    "anyOf": [
                                      {
                                        "type": "number",
                                        "enum": [
                                          1,
                                          2,
                                          3
                                        ]
                                      },
                                      {
                                        "type": "string",
                                        "enum": [
                                          "GROUP"
                                        ]
                                      }
                                    ]
                                  }
                                },
                                "connections_of": {
                                  "description": "The ID of the parameter. Use type PEOPLE on the List search parameters route to find out the right ID.\nLinkedin native filter : CONNECTIONS OF.",
                                  "minItems": 1,
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "pattern": "^.+$"
                                  }
                                },
                                "past_colleague": {
                                  "description": "Linkedin native filter : PAST COLLEAGUE.",
                                  "type": "boolean"
                                },
                                "shared_experiences": {
                                  "description": "Linkedin native filter : SHARED EXPERIENCES.",
                                  "type": "boolean"
                                },
                                "changed_jobs": {
                                  "description": "Linkedin native filter : CHANGED JOBS.",
                                  "type": "boolean"
                                },
                                "posted_on_linkedin": {
                                  "description": "Linkedin native filter : POSTED ON LINKEDIN.",
                                  "type": "boolean"
                                },
                                "mentionned_in_news": {
                                  "description": "Linkedin native filter : MENTIONNED IN NEWS.",
                                  "type": "boolean"
                                },
                                "persona": {
                                  "description": "The ID of the parameter. Use type PERSONA on the List search parameters route to find out the right ID.\nLinkedin native filter : PERSONA.",
                                  "minItems": 1,
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "pattern": "^\\d+$"
                                  }
                                },
                                "account_lists": {
                                  "description": "Linkedin native filter : ACCOUNT LISTS.",
                                  "type": "object",
                                  "properties": {
                                    "include": {
                                      "description": "The ID of the parameter. Use type ACCOUNT_LISTS on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^(\\d+|ALL)$"
                                      }
                                    },
                                    "exclude": {
                                      "description": "The ID of the parameter. Use type ACCOUNT_LISTS on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^(\\d+|ALL)$"
                                      }
                                    }
                                  }
                                },
                                "lead_lists": {
                                  "description": "Linkedin native filter : LEAD LISTS.",
                                  "type": "object",
                                  "properties": {
                                    "include": {
                                      "description": "The ID of the parameter. Use type LEAD_LISTS on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^(\\d+|ALL)$"
                                      }
                                    },
                                    "exclude": {
                                      "description": "The ID of the parameter. Use type LEAD_LISTS on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^(\\d+|ALL)$"
                                      }
                                    }
                                  }
                                },
                                "viewed_profile_recently": {
                                  "description": "Linkedin native filter : PEOPLE YOU INTERACTED WITH / VIEWED PROFILE.",
                                  "type": "boolean"
                                },
                                "messaged_recently": {
                                  "description": "Linkedin native filter : PEOPLE YOU INTERACTED WITH / MESSAGED.",
                                  "type": "boolean"
                                },
                                "include_saved_leads": {
                                  "description": "Linkedin native filter : SAVED LEADS AND ACCOUNTS / ALL MY SAVED LEADS.",
                                  "type": "boolean"
                                },
                                "include_saved_accounts": {
                                  "description": "Linkedin native filter : SAVED LEADS AND ACCOUNTS / ALL MY SAVED ACCOUNTS.",
                                  "type": "boolean"
                                }
                              },
                              "required": [
                                "api",
                                "category"
                              ]
                            },
                            {
                              "title": "Sales Navigator - Companies",
                              "type": "object",
                              "properties": {
                                "api": {
                                  "type": "string",
                                  "enum": [
                                    "sales_navigator"
                                  ]
                                },
                                "category": {
                                  "type": "string",
                                  "enum": [
                                    "companies"
                                  ]
                                },
                                "keywords": {
                                  "description": "Linkedin native filter : KEYWORDS.",
                                  "type": "string"
                                },
                                "last_viewed_at": {
                                  "description": "Unix timestamp to be used with a saved search to filter new results from this date.",
                                  "type": "number"
                                },
                                "saved_search_id": {
                                  "description": "The ID of the parameter. Use type SAVED_SEARCHES on the List search parameters route to find out the right ID.\nOverrides all other parameters.",
                                  "type": "string",
                                  "pattern": "^\\d+$"
                                },
                                "recent_search_id": {
                                  "description": "The ID of the parameter. Use type RECENT_SEARCHES on the List search parameters route to find out the right ID.\nOverrides all other parameters.",
                                  "type": "string",
                                  "pattern": "^\\d+$"
                                },
                                "industry": {
                                  "description": "Linkedin native filter : INDUSTRY.",
                                  "type": "object",
                                  "properties": {
                                    "include": {
                                      "description": "The ID of the parameter. Use type SALES_INDUSTRY on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    },
                                    "exclude": {
                                      "description": "The ID of the parameter. Use type SALES_INDUSTRY on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    }
                                  }
                                },
                                "location": {
                                  "description": "Linkedin native filter : HEADQUARTERS LOCATION.",
                                  "type": "object",
                                  "properties": {
                                    "include": {
                                      "description": "The ID of the parameter. Use type LOCATION on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    },
                                    "exclude": {
                                      "description": "The ID of the parameter. Use type LOCATION on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    }
                                  }
                                },
                                "location_by_postal_code": {
                                  "type": "object",
                                  "properties": {
                                    "include": {
                                      "description": "The ID of the parameter. Use type POSTAL_CODE on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    },
                                    "exclude": {
                                      "description": "The ID of the parameter. Use type POSTAL_CODE on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    },
                                    "within_area": {
                                      "description": "The search zone around the location in miles.",
                                      "type": "number"
                                    }
                                  }
                                },
                                "has_job_offers": {
                                  "description": "Linkedin native filter : JOB OPPORTUNITIES / HIRING ON LINKEDIN.",
                                  "type": "boolean"
                                },
                                "headcount": {
                                  "description": "Linkedin native filter : COMPANY HEADCOUNT.",
                                  "type": "array",
                                  "items": {
                                    "type": "object",
                                    "properties": {
                                      "min": {
                                        "type": "number",
                                        "enum": [
                                          1,
                                          11,
                                          51,
                                          201,
                                          501,
                                          1001,
                                          5001,
                                          10001
                                        ]
                                      },
                                      "max": {
                                        "type": "number",
                                        "enum": [
                                          10,
                                          50,
                                          200,
                                          500,
                                          1000,
                                          5000,
                                          10000
                                        ]
                                      }
                                    }
                                  }
                                },
                                "headcount_growth": {
                                  "description": "Linkedin native filter : COMPANY HEADCOUNT GROWTH.",
                                  "type": "object",
                                  "properties": {
                                    "min": {
                                      "type": "number"
                                    },
                                    "max": {
                                      "type": "number"
                                    }
                                  }
                                },
                                "department_headcount": {
                                  "description": "Linkedin native filter : DEPARTMENT HEADCOUNT.",
                                  "type": "object",
                                  "properties": {
                                    "department": {
                                      "description": "The ID of the parameter. Use type DEPARTMENT on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    },
                                    "min": {
                                      "type": "number"
                                    },
                                    "max": {
                                      "type": "number"
                                    }
                                  },
                                  "required": [
                                    "department"
                                  ]
                                },
                                "department_headcount_growth": {
                                  "description": "Linkedin native filter : DEPARTMENT HEADCOUNT GROWTH.",
                                  "type": "object",
                                  "properties": {
                                    "department": {
                                      "description": "The ID of the parameter. Use type DEPARTMENT on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    },
                                    "min": {
                                      "type": "number"
                                    },
                                    "max": {
                                      "type": "number"
                                    }
                                  },
                                  "required": [
                                    "department"
                                  ]
                                },
                                "network_distance": {
                                  "description": "First, second or third+ degree.\nLinkedin native filter : CONNECTION.",
                                  "type": "array",
                                  "items": {
                                    "type": "number",
                                    "enum": [
                                      1,
                                      2,
                                      3
                                    ]
                                  }
                                },
                                "annual_revenue": {
                                  "description": "Linkedin native filter : ANNUAL REVENUE. If you want to use the '1000+' value, please set the 'max' value field to 1001.",
                                  "type": "object",
                                  "properties": {
                                    "currency": {
                                      "minLength": 3,
                                      "maxLength": 3,
                                      "description": "ISO 4217 currency code.",
                                      "type": "string"
                                    },
                                    "min": {
                                      "type": "number",
                                      "enum": [
                                        0,
                                        0.2,
                                        1,
                                        2.5,
                                        5,
                                        10,
                                        20,
                                        50,
                                        100,
                                        500,
                                        1000,
                                        1001
                                      ]
                                    },
                                    "max": {
                                      "type": "number",
                                      "enum": [
                                        0,
                                        0.2,
                                        1,
                                        2.5,
                                        5,
                                        10,
                                        20,
                                        50,
                                        100,
                                        500,
                                        1000,
                                        1001
                                      ]
                                    }
                                  },
                                  "required": [
                                    "currency",
                                    "min",
                                    "max"
                                  ]
                                },
                                "followers_count": {
                                  "description": "Linkedin native filter : NUMBER OF FOLLOWERS.",
                                  "type": "array",
                                  "items": {
                                    "type": "object",
                                    "properties": {
                                      "min": {
                                        "type": "number",
                                        "enum": [
                                          1,
                                          51,
                                          101,
                                          1001,
                                          5001
                                        ]
                                      },
                                      "max": {
                                        "type": "number",
                                        "enum": [
                                          50,
                                          100,
                                          1000,
                                          5000
                                        ]
                                      }
                                    }
                                  }
                                },
                                "fortune": {
                                  "description": "Linkedin native filter : FORTUNE.",
                                  "type": "array",
                                  "items": {
                                    "type": "object",
                                    "properties": {
                                      "min": {
                                        "type": "number",
                                        "enum": [
                                          0,
                                          51,
                                          101,
                                          251
                                        ]
                                      },
                                      "max": {
                                        "type": "number",
                                        "enum": [
                                          50,
                                          100,
                                          250,
                                          500
                                        ]
                                      }
                                    }
                                  }
                                },
                                "technologies": {
                                  "description": "The ID of the parameter. Use type TECHNOLOGIES on the List search parameters route to find out the right ID.\nLinkedin native filter : TECHNOLOGIES USED.",
                                  "minItems": 1,
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "pattern": "^\\d+$"
                                  }
                                },
                                "recent_activities": {
                                  "description": "Linkedin native filter : RECENT ACTIVITIES.",
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "enum": [
                                      "senior_leadership_changes",
                                      "funding_events"
                                    ]
                                  }
                                },
                                "saved_accounts": {
                                  "description": "The ID of the parameter. Use type SAVED_ACCOUNTS on the List search parameters route to find out the right ID.\nLinkedin native filter : SAVED ACCOUNTS.",
                                  "minItems": 1,
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "pattern": "^.+$"
                                  }
                                },
                                "account_lists": {
                                  "description": "Linkedin native filter : ACCOUNT LISTS.",
                                  "type": "object",
                                  "properties": {
                                    "include": {
                                      "description": "The ID of the parameter. Use type ACCOUNT_LISTS on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^(\\d+|ALL)$"
                                      }
                                    },
                                    "exclude": {
                                      "description": "The ID of the parameter. Use type ACCOUNT_LISTS on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^(\\d+|ALL)$"
                                      }
                                    }
                                  }
                                }
                              },
                              "required": [
                                "api",
                                "category"
                              ]
                            },
                            {
                              "title": "Recruiter - People",
                              "type": "object",
                              "properties": {
                                "api": {
                                  "type": "string",
                                  "enum": [
                                    "recruiter"
                                  ]
                                },
                                "category": {
                                  "type": "string",
                                  "enum": [
                                    "people"
                                  ]
                                },
                                "keywords": {
                                  "minLength": 1,
                                  "description": "Boolean modifiers can be used to refine your search.\nExample : developers AND product owners NOT managers",
                                  "type": "string"
                                },
                                "saved_search": {
                                  "description": "This parameter will override all others.",
                                  "type": "object",
                                  "properties": {
                                    "id": {
                                      "description": "The ID of the parameter. Use type SAVED_SEARCHES on the List search parameters route to find out the right ID.",
                                      "type": "string",
                                      "pattern": "^\\d+$"
                                    },
                                    "project_id": {
                                      "description": "The ID of the parameter. Use type SAVED_SEARCHES on the List search parameters route to find out the right ID.",
                                      "type": "string",
                                      "pattern": "^\\d+$"
                                    }
                                  },
                                  "required": [
                                    "id",
                                    "project_id"
                                  ]
                                },
                                "saved_filter": {
                                  "description": "The ID of the parameter. Use type SAVED_FILTERS on the List search parameters route to find out the right ID.",
                                  "type": "string",
                                  "pattern": "^\\d+$"
                                },
                                "location": {
                                  "type": "array",
                                  "items": {
                                    "type": "object",
                                    "properties": {
                                      "id": {
                                        "description": "The ID of the parameter. Use type LOCATION on the List search parameters route to find out the right ID.",
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      },
                                      "priority": {
                                        "type": "string",
                                        "enum": [
                                          "CAN_HAVE",
                                          "MUST_HAVE",
                                          "DOESNT_HAVE"
                                        ]
                                      },
                                      "scope": {
                                        "type": "string",
                                        "enum": [
                                          "CURRENT",
                                          "OPEN_TO_RELOCATE_ONLY",
                                          "CURRENT_OR_OPEN_TO_RELOCATE"
                                        ]
                                      },
                                      "title": {
                                        "description": "The title that came along with the ID in the List search parameters route response. Only necessary if the CURRENT_OR_OPEN_TO_RELOCATE value of the scope parameter is used.",
                                        "type": "string"
                                      }
                                    },
                                    "required": [
                                      "id"
                                    ]
                                  }
                                },
                                "location_within_area": {
                                  "description": "The search zone around the location in miles.",
                                  "type": "number"
                                },
                                "industry": {
                                  "description": "Linkedin native filter : INDUSTRIES.",
                                  "type": "object",
                                  "properties": {
                                    "include": {
                                      "description": "The ID of the parameter. Use type INDUSTRY on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    },
                                    "exclude": {
                                      "description": "The ID of the parameter. Use type INDUSTRY on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    }
                                  }
                                },
                                "role": {
                                  "type": "array",
                                  "items": {
                                    "description": "Linkedin native filter : JOB TITLES.",
                                    "anyOf": [
                                      {
                                        "title": "ID based",
                                        "type": "object",
                                        "properties": {
                                          "id": {
                                            "description": "The ID of the parameter. Use type JOB_TITLE on the List search parameters route to find out the right ID.",
                                            "type": "string",
                                            "pattern": "^\\d+$"
                                          },
                                          "is_selection": {
                                            "description": "Linkedin job titles are either strict filters (only the people with that job) or selections (can include people with related jobs). A strict parameter cannot be used as a selection and vice versa. This information is provided on the List search parameters route results.",
                                            "type": "boolean"
                                          },
                                          "priority": {
                                            "type": "string",
                                            "enum": [
                                              "CAN_HAVE",
                                              "MUST_HAVE",
                                              "DOESNT_HAVE"
                                            ]
                                          },
                                          "scope": {
                                            "type": "string",
                                            "enum": [
                                              "CURRENT_OR_PAST",
                                              "CURRENT",
                                              "PAST",
                                              "PAST_NOT_CURRENT",
                                              "OPEN_TO_WORK"
                                            ]
                                          }
                                        },
                                        "required": [
                                          "id",
                                          "is_selection"
                                        ],
                                        "x-scope": {
                                          "type": "string",
                                          "enum": [
                                            "CURRENT_OR_PAST",
                                            "CURRENT",
                                            "PAST",
                                            "PAST_NOT_CURRENT",
                                            "OPEN_TO_WORK"
                                          ]
                                        }
                                      },
                                      {
                                        "title": "Keywords based",
                                        "type": "object",
                                        "properties": {
                                          "keywords": {
                                            "minLength": 1,
                                            "description": "Boolean modifiers can be used to refine your search.\nExample : developers AND product owners NOT managers",
                                            "type": "string"
                                          },
                                          "priority": {
                                            "type": "string",
                                            "enum": [
                                              "CAN_HAVE",
                                              "MUST_HAVE",
                                              "DOESNT_HAVE"
                                            ]
                                          },
                                          "scope": {
                                            "type": "string",
                                            "enum": [
                                              "CURRENT_OR_PAST",
                                              "CURRENT",
                                              "PAST",
                                              "PAST_NOT_CURRENT",
                                              "OPEN_TO_WORK"
                                            ]
                                          }
                                        },
                                        "required": [
                                          "keywords"
                                        ],
                                        "x-scope": {
                                          "type": "string",
                                          "enum": [
                                            "CURRENT_OR_PAST",
                                            "CURRENT",
                                            "PAST",
                                            "PAST_NOT_CURRENT",
                                            "OPEN_TO_WORK"
                                          ]
                                        }
                                      }
                                    ]
                                  }
                                },
                                "skills": {
                                  "type": "array",
                                  "items": {
                                    "description": "Linkedin native filter : SKILLS AND ASSESSMENTS.",
                                    "anyOf": [
                                      {
                                        "title": "ID based",
                                        "type": "object",
                                        "properties": {
                                          "id": {
                                            "description": "The ID of the parameter. Use type SKILL on the List search parameters route to find out the right ID.",
                                            "type": "string",
                                            "pattern": "^\\d+$"
                                          },
                                          "priority": {
                                            "type": "string",
                                            "enum": [
                                              "CAN_HAVE",
                                              "MUST_HAVE",
                                              "DOESNT_HAVE"
                                            ]
                                          }
                                        },
                                        "required": [
                                          "id"
                                        ]
                                      },
                                      {
                                        "title": "Keywords based",
                                        "type": "object",
                                        "properties": {
                                          "keywords": {
                                            "minLength": 1,
                                            "description": "Boolean modifiers can be used to refine your search.\nExample : developers AND product owners NOT managers",
                                            "type": "string"
                                          },
                                          "priority": {
                                            "type": "string",
                                            "enum": [
                                              "CAN_HAVE",
                                              "MUST_HAVE",
                                              "DOESNT_HAVE"
                                            ]
                                          }
                                        },
                                        "required": [
                                          "keywords"
                                        ]
                                      }
                                    ]
                                  }
                                },
                                "company": {
                                  "type": "array",
                                  "items": {
                                    "description": "Linkedin native filter : COMPANIES.",
                                    "anyOf": [
                                      {
                                        "title": "ID based",
                                        "type": "object",
                                        "properties": {
                                          "id": {
                                            "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.",
                                            "type": "string",
                                            "pattern": "^\\d+$"
                                          },
                                          "priority": {
                                            "type": "string",
                                            "enum": [
                                              "CAN_HAVE",
                                              "MUST_HAVE",
                                              "DOESNT_HAVE"
                                            ]
                                          },
                                          "scope": {
                                            "type": "string",
                                            "enum": [
                                              "CURRENT_OR_PAST",
                                              "CURRENT",
                                              "PAST",
                                              "PAST_NOT_CURRENT"
                                            ]
                                          }
                                        },
                                        "required": [
                                          "id"
                                        ],
                                        "x-scope": {
                                          "type": "string",
                                          "enum": [
                                            "CURRENT_OR_PAST",
                                            "CURRENT",
                                            "PAST",
                                            "PAST_NOT_CURRENT"
                                          ]
                                        }
                                      },
                                      {
                                        "title": "Keywords based",
                                        "type": "object",
                                        "properties": {
                                          "keywords": {
                                            "minLength": 1,
                                            "description": "Boolean modifiers can be used to refine your search.\nExample : developers AND product owners NOT managers",
                                            "type": "string"
                                          },
                                          "priority": {
                                            "type": "string",
                                            "enum": [
                                              "CAN_HAVE",
                                              "MUST_HAVE",
                                              "DOESNT_HAVE"
                                            ]
                                          },
                                          "scope": {
                                            "type": "string",
                                            "enum": [
                                              "CURRENT_OR_PAST",
                                              "CURRENT",
                                              "PAST",
                                              "PAST_NOT_CURRENT"
                                            ]
                                          }
                                        },
                                        "required": [
                                          "keywords"
                                        ],
                                        "x-scope": {
                                          "type": "string",
                                          "enum": [
                                            "CURRENT_OR_PAST",
                                            "CURRENT",
                                            "PAST",
                                            "PAST_NOT_CURRENT"
                                          ]
                                        }
                                      }
                                    ]
                                  }
                                },
                                "company_headcount": {
                                  "description": "Linkedin native filter : COMPANY SIZES.",
                                  "type": "array",
                                  "items": {
                                    "type": "object",
                                    "properties": {
                                      "min": {
                                        "type": "number",
                                        "enum": [
                                          1,
                                          11,
                                          51,
                                          201,
                                          501,
                                          1001,
                                          5001,
                                          10001
                                        ]
                                      },
                                      "max": {
                                        "type": "number",
                                        "enum": [
                                          10,
                                          50,
                                          200,
                                          500,
                                          1000,
                                          5000,
                                          10000
                                        ]
                                      }
                                    }
                                  }
                                },
                                "current_company": {
                                  "type": "array",
                                  "items": {
                                    "description": "Linkedin native filter : CURRENT COMPANIES.",
                                    "type": "object",
                                    "properties": {
                                      "id": {
                                        "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.",
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      },
                                      "priority": {
                                        "type": "string",
                                        "enum": [
                                          "CAN_HAVE",
                                          "MUST_HAVE",
                                          "DOESNT_HAVE"
                                        ]
                                      }
                                    },
                                    "required": [
                                      "id"
                                    ]
                                  }
                                },
                                "past_company": {
                                  "type": "array",
                                  "items": {
                                    "description": "Linkedin native filter : PAST COMPANIES.",
                                    "type": "object",
                                    "properties": {
                                      "id": {
                                        "description": "The ID of the parameter. Use type COMPANY on the List search parameters route to find out the right ID.",
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      },
                                      "priority": {
                                        "type": "string",
                                        "enum": [
                                          "CAN_HAVE",
                                          "MUST_HAVE",
                                          "DOESNT_HAVE"
                                        ]
                                      }
                                    },
                                    "required": [
                                      "id"
                                    ]
                                  }
                                },
                                "school": {
                                  "type": "array",
                                  "items": {
                                    "description": "Linkedin native filter : SCHOOLS.",
                                    "type": "object",
                                    "properties": {
                                      "id": {
                                        "description": "The ID of the parameter. Use type SCHOOL on the List search parameters route to find out the right ID.",
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      },
                                      "priority": {
                                        "type": "string",
                                        "enum": [
                                          "CAN_HAVE",
                                          "MUST_HAVE",
                                          "DOESNT_HAVE"
                                        ]
                                      }
                                    },
                                    "required": [
                                      "id"
                                    ]
                                  }
                                },
                                "groups": {
                                  "description": "The ID of the parameter. Use type GROUPS on the List search parameters route to find out the right ID.\nLinkedin native filter : ALL GROUPS.",
                                  "minItems": 1,
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "pattern": "^\\d+$"
                                  }
                                },
                                "graduation_year": {
                                  "description": "A range of years.\nLinkedin native filter : YEAR OF GRADUATION.",
                                  "type": "object",
                                  "properties": {
                                    "min": {
                                      "minimum": 1000,
                                      "maximum": 9999,
                                      "type": "number"
                                    },
                                    "max": {
                                      "minimum": 1000,
                                      "maximum": 9999,
                                      "type": "number"
                                    }
                                  }
                                },
                                "tenure": {
                                  "description": "Linkedin native filter : YEARS OF EXPERIENCE.",
                                  "type": "object",
                                  "properties": {
                                    "min": {
                                      "type": "number"
                                    },
                                    "max": {
                                      "type": "number"
                                    }
                                  }
                                },
                                "seniority": {
                                  "description": "Linkedin native filter : SENIORITY.",
                                  "type": "object",
                                  "properties": {
                                    "include": {
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "enum": [
                                          "owner",
                                          "partner",
                                          "cxo",
                                          "vp",
                                          "director",
                                          "manager",
                                          "senior",
                                          "entry",
                                          "training",
                                          "unpaid"
                                        ]
                                      }
                                    },
                                    "exclude": {
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "enum": [
                                          "owner",
                                          "partner",
                                          "cxo",
                                          "vp",
                                          "director",
                                          "manager",
                                          "senior",
                                          "entry",
                                          "training",
                                          "unpaid"
                                        ]
                                      }
                                    }
                                  }
                                },
                                "function": {
                                  "description": "The ID of the parameter. Use type DEPARTMENT on the List search parameters route to find out the right ID.\nLinkedin native filter : JOB FUNCTIONS.",
                                  "minItems": 1,
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "pattern": "^\\d+$"
                                  }
                                },
                                "network_distance": {
                                  "description": "First, second, third+ degree or GROUP.\nLinkedin native filter : NETWORK RELATIONSHIPS.",
                                  "type": "array",
                                  "items": {
                                    "anyOf": [
                                      {
                                        "type": "number",
                                        "enum": [
                                          1,
                                          2,
                                          3
                                        ]
                                      },
                                      {
                                        "type": "string",
                                        "enum": [
                                          "GROUP"
                                        ]
                                      }
                                    ]
                                  }
                                },
                                "spoken_languages": {
                                  "type": "array",
                                  "items": {
                                    "description": "Linkedin native filter : SPOKEN LANGUAGES.",
                                    "type": "object",
                                    "properties": {
                                      "language": {
                                        "type": "string"
                                      },
                                      "priority": {
                                        "type": "string",
                                        "enum": [
                                          "CAN_HAVE",
                                          "MUST_HAVE",
                                          "DOESNT_HAVE"
                                        ]
                                      },
                                      "scope": {
                                        "type": "string",
                                        "enum": [
                                          "ELEMENTARY",
                                          "LIMITED_WORKING",
                                          "PROFESSIONAL_WORKING",
                                          "NATIVE_OR_BILINGUAL"
                                        ]
                                      }
                                    },
                                    "required": [
                                      "language"
                                    ],
                                    "x-scope": {
                                      "type": "string",
                                      "enum": [
                                        "ELEMENTARY",
                                        "LIMITED_WORKING",
                                        "PROFESSIONAL_WORKING",
                                        "NATIVE_OR_BILINGUAL"
                                      ]
                                    }
                                  }
                                },
                                "hide_previously_viewed": {
                                  "description": "Linkedin native filter : HIDE PREVIOUSLY VIEWED.",
                                  "type": "object",
                                  "properties": {
                                    "timespan": {
                                      "description": "The timespan in days since today for the filter to be applied.",
                                      "type": "number"
                                    }
                                  },
                                  "required": [
                                    "timespan"
                                  ]
                                },
                                "profile_language": {
                                  "description": "ISO 639-1 language code.\nLinkedin native filter : PROFILE LANGUAGES.",
                                  "type": "array",
                                  "items": {
                                    "minLength": 2,
                                    "maxLength": 2,
                                    "type": "string"
                                  }
                                },
                                "recently_joined": {
                                  "description": "Linkedin native filter : RECENTLY JOINED LINKEDIN.",
                                  "type": "array",
                                  "items": {
                                    "type": "object",
                                    "properties": {
                                      "min": {
                                        "type": "number",
                                        "enum": [
                                          2,
                                          8,
                                          15,
                                          31
                                        ]
                                      },
                                      "max": {
                                        "type": "number",
                                        "enum": [
                                          1,
                                          7,
                                          14,
                                          30,
                                          90
                                        ]
                                      }
                                    }
                                  }
                                },
                                "spotlights": {
                                  "description": "Linkedin native filter : SPOTLIGHTS. For users with advanced Recruiter subscription.",
                                  "type": "array",
                                  "items": {
                                    "type": "string",
                                    "enum": [
                                      "OPEN_TO_WORK",
                                      "ACTIVE_TALENT",
                                      "REDISCOVERED_CANDIDATES",
                                      "INTERNAL_CANDIDATES",
                                      "INTERESTED_IN_YOUR_COMPANY",
                                      "HAVE_COMPANY_CONNECTIONS"
                                    ]
                                  }
                                },
                                "first_name": {
                                  "description": "Linkedin native filter : FIRST NAMES.",
                                  "type": "array",
                                  "items": {
                                    "minLength": 1,
                                    "description": "Boolean modifiers can be used to refine your search.\nExample : developers AND product owners NOT managers",
                                    "type": "string"
                                  }
                                },
                                "last_name": {
                                  "description": "Linkedin native filter : LAST NAMES.",
                                  "type": "array",
                                  "items": {
                                    "minLength": 1,
                                    "description": "Boolean modifiers can be used to refine your search.\nExample : developers AND product owners NOT managers",
                                    "type": "string"
                                  }
                                },
                                "has_military_background": {
                                  "description": "Linkedin native filter : HAS US MILITARY BACKGROUND.",
                                  "type": "boolean"
                                },
                                "past_applicants": {
                                  "description": "Linkedin native filter : PAST APPLICANTS.",
                                  "type": "boolean"
                                },
                                "hiring_projects": {
                                  "description": "Linkedin native filter : PROJECTS.",
                                  "type": "object",
                                  "properties": {
                                    "include": {
                                      "description": "The ID of the parameter. Use type HIRING_PROJECTS on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    },
                                    "exclude": {
                                      "description": "The ID of the parameter. Use type HIRING_PROJECTS on the List search parameters route to find out the right ID.",
                                      "minItems": 1,
                                      "type": "array",
                                      "items": {
                                        "type": "string",
                                        "pattern": "^\\d+$"
                                      }
                                    }
                                  }
                                },
                                "recruiting_activity": {
                                  "type": "array",
                                  "items": {
                                    "description": "Linkedin native filter : RECRUITING ACTIVITY.",
                                    "type": "object",
                                    "properties": {
                                      "id": {
                                        "type": "string",
                                        "enum": [
                                          "messages",
                                          "tags",
                                          "notes",
                                          "projects",
                                          "resumes",
                                          "reviews"
                                        ]
                                      },
                                      "priority": {
                                        "type": "string",
                                        "enum": [
                                          "CAN_HAVE",
                                          "MUST_HAVE",
                                          "DOESNT_HAVE"
                                        ]
                                      },
                                      "timespan": {
                                        "description": "The timespan in days since today for the filter to be applied.",
                                        "type": "number"
                                      }
                                    },
                                    "required": [
                                      "id"
                                    ],
                                    "x-timespan": {
                                      "description": "The timespan in days since today for the filter to be applied.",
                                      "type": "number"
                                    }
                                  }
                                },
                                "notes": {
                                  "description": "Linkedin native filter : NOTES.",
                                  "type": "array",
                                  "items": {
                                    "minLength": 1,
                                    "type": "string"
                                  }
                                }
                              },
                              "required": [
                                "api",
                                "category"
                              ]
                            },
                            {
                              "title": "Search from URL",
                              "type": "object",
                              "properties": {
                                "url": {
                                  "description": "Linkedin's public search URL. Setting this parameter will override the entire body.",
                                  "type": "string"
                                }
                              },
                              "required": [
                                "url"
                              ]
                            },
                            {
                              "title": "Cursor",
                              "description": "In the case of a long cursor, you may want to set it in the body rather than in the query parameters.",
                              "type": "object",
                              "properties": {
                                "cursor": {
                                  "title": "CursorParam",
                                  "description": "A cursor for pagination purposes. To get the next page of entries, you need to make a new request and fulfill this field with the cursor received in the preceding request. This process should be repeated until all entries have been retrieved.",
                                  "minLength": 1,
                                  "type": "string"
                                }
                              },
                              "required": [
                                "cursor"
                              ]
                            }
                          ]
                        }
                      }
                    },
                    "paging": {
                      "type": "object",
                      "properties": {
                        "start": {
                          "anyOf": [
                            {
                              "type": "number"
                            },
                            {
                              "nullable": true
                            }
                          ]
                        },
                        "page_count": {
                          "type": "number"
                        },
                        "total_count": {
                          "type": "number"
                        }
                      },
                      "required": [
                        "start",
                        "page_count",
                        "total_count"
                      ]
                    },
                    "cursor": {
                      "anyOf": [
                        {
                          "title": "CursorParam",
                          "description": "A cursor for pagination purposes. To get the next page of entries, you need to make a new request and fulfill this field with the cursor received in the preceding request. This process should be repeated until all entries have been retrieved.",
                          "minLength": 1,
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
                    "items",
                    "config",
                    "paging",
                    "cursor"
                  ]
                }
              }
            }
          },
          "400": {
            "description": "\n          ## Bad Request\n          ### Invalid parameters\n          One or more request parameters are invalid or missing.\nundefined",
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