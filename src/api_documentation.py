"""
API Documentation with Swagger/OpenAPI
Complete API documentation for P&L Card System
"""

from flask import Flask, Blueprint, jsonify
from flask_cors import CORS
import yaml
from pathlib import Path

def create_openapi_spec():
    """Create OpenAPI specification for P&L Card API"""
    
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "P&L Card API",
            "description": "API for generating and sharing P&L cards",
            "version": "1.0.0",
            "contact": {
                "name": "Crypto Predict Monitor",
                "url": "https://cryptopredict.monitor"
            },
            "license": {
                "name": "MIT"
            }
        },
        "servers": [
            {
                "url": "http://localhost:5000",
                "description": "Development server"
            },
            {
                "url": "https://api.cryptopredict.monitor",
                "description": "Production server"
            }
        ],
        "paths": {
            "/health": {
                "get": {
                    "summary": "Health check",
                    "description": "Check if the API is running and healthy",
                    "tags": ["Health"],
                    "responses": {
                        "200": {
                            "description": "Service is healthy",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string"},
                                            "timestamp": {"type": "string"},
                                            "version": {"type": "string"},
                                            "services": {
                                                "type": "object",
                                                "properties": {
                                                    "pnl_cards": {"type": "string"},
                                                    "database": {"type": "string"},
                                                    "s3": {"type": "string"}
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/health": {
                "get": {
                    "summary": "API health check",
                    "description": "Check API endpoints status",
                    "tags": ["Health"],
                    "responses": {
                        "200": {
                            "description": "API is healthy",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "api": {"type": "string"},
                                            "endpoints": {
                                                "type": "object",
                                                "properties": {
                                                    "pnl_cards": {"type": "string"},
                                                    "leaderboard": {"type": "string"}
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/pnl-card/{user_id}": {
                "get": {
                    "summary": "Download P&L card",
                    "description": "Generate and download a P&L card for a user",
                    "tags": ["P&L Cards"],
                    "security": [{"BearerAuth": []}],
                    "parameters": [
                        {
                            "name": "user_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "User ID to generate card for"
                        },
                        {
                            "name": "period",
                            "in": "query",
                            "required": False,
                            "schema": {
                                "type": "string",
                                "enum": ["daily", "weekly", "monthly"],
                                "default": "daily"
                            },
                            "description": "Time period for P&L calculation"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "P&L card generated successfully",
                            "content": {
                                "image/png": {
                                    "schema": {
                                        "type": "string",
                                        "format": "binary"
                                    }
                                }
                            }
                        },
                        "401": {
                            "description": "Unauthorized",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            }
                        },
                        "404": {
                            "description": "User not found or no P&L data",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            }
                        },
                        "429": {
                            "description": "Rate limit exceeded",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            }
                        },
                        "500": {
                            "description": "Internal server error",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/pnl-card/{user_id}/share": {
                "get": {
                    "summary": "Get P&L card sharing metadata",
                    "description": "Get metadata for sharing P&L card on social media",
                    "tags": ["P&L Cards"],
                    "security": [{"BearerAuth": []}],
                    "parameters": [
                        {
                            "name": "user_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "User ID to generate metadata for"
                        },
                        {
                            "name": "period",
                            "in": "query",
                            "required": False,
                            "schema": {
                                "type": "string",
                                "enum": ["daily", "weekly", "monthly"],
                                "default": "daily"
                            },
                            "description": "Time period for P&L calculation"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Sharing metadata generated successfully",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/ShareMetadata"
                                    }
                                }
                            }
                        },
                        "401": {
                            "description": "Unauthorized",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            }
                        },
                        "404": {
                            "description": "User not found or no P&L data",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            }
                        },
                        "429": {
                            "description": "Rate limit exceeded",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            }
                        },
                        "500": {
                            "description": "Internal server error",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/pnl-card/{user_id}/leaderboard": {
                "get": {
                    "summary": "Get user leaderboard stats",
                    "description": "Get user's position and stats on the leaderboard",
                    "tags": ["Leaderboard"],
                    "security": [{"BearerAuth": []}],
                    "parameters": [
                        {
                            "name": "user_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "User ID to get stats for"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Leaderboard stats retrieved successfully",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/LeaderboardStats"
                                    }
                                }
                            }
                        },
                        "401": {
                            "description": "Unauthorized",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            }
                        },
                        "404": {
                            "description": "User not found",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            }
                        },
                        "500": {
                            "description": "Internal server error",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Error"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            },
            "schemas": {
                "Error": {
                    "type": "object",
                    "required": ["error"],
                    "properties": {
                        "error": {
                            "type": "string",
                            "description": "Error message"
                        },
                        "code": {
                            "type": "string",
                            "description": "Error code"
                        },
                        "details": {
                            "type": "object",
                            "description": "Additional error details"
                        }
                    }
                },
                "ShareMetadata": {
                    "type": "object",
                    "required": ["share_text", "twitter_url", "discord_url"],
                    "properties": {
                        "share_text": {
                            "type": "string",
                            "description": "Text for sharing on social media"
                        },
                        "twitter_url": {
                            "type": "string",
                            "description": "Twitter share URL"
                        },
                        "discord_url": {
                            "type": "string",
                            "description": "Discord share URL"
                        },
                        "card_url": {
                            "type": "string",
                            "description": "URL to the generated card image"
                        },
                        "pnl_data": {
                            "type": "object",
                            "description": "P&L data used for the card",
                            "properties": {
                                "total_pnl_percentage": {"type": "number"},
                                "total_trades": {"type": "integer"},
                                "win_rate": {"type": "number"},
                                "period": {"type": "string"}
                            }
                        }
                    }
                },
                "LeaderboardStats": {
                    "type": "object",
                    "required": ["user_stats", "rank"],
                    "properties": {
                        "user_stats": {
                            "type": "object",
                            "properties": {
                                "total_pnl": {"type": "number"},
                                "total_trades": {"type": "integer"},
                                "win_rate": {"type": "number"},
                                "username": {"type": "string"},
                                "avatar_url": {"type": "string"}
                            }
                        },
                        "rank": {
                            "type": "integer",
                            "description": "User's rank on the leaderboard"
                        },
                        "total_users": {
                            "type": "integer",
                            "description": "Total number of users on leaderboard"
                        },
                        "top_performers": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "rank": {"type": "integer"},
                                    "username": {"type": "string"},
                                    "total_pnl": {"type": "number"},
                                    "win_rate": {"type": "number"}
                                }
                            }
                        }
                    }
                }
            }
        },
        "tags": [
            {
                "name": "Health",
                "description": "Health check endpoints"
            },
            {
                "name": "P&L Cards",
                "description": "P&L card generation and sharing endpoints"
            },
            {
                "name": "Leaderboard",
                "description": "Leaderboard and user stats endpoints"
            }
        ]
    }
    
    return spec

def create_docs_blueprint():
    """Create Flask blueprint for API documentation"""
    
    docs_bp = Blueprint('docs', __name__)
    
    @docs_bp.route('/docs')
    def docs_home():
        """Redirect to Swagger UI"""
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>P&L Card API Documentation</title>
            <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@3.52.5/swagger-ui.css" />
            <style>
                html { box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }
                *, *:before, *:after { box-sizing: inherit; }
                body { margin:0; background: #fafafa; }
            </style>
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script src="https://unpkg.com/swagger-ui-dist@3.52.5/swagger-ui-bundle.js"></script>
            <script src="https://unpkg.com/swagger-ui-dist@3.52.5/swagger-ui-standalone-preset.js"></script>
            <script>
                window.onload = function() {
                    const ui = SwaggerUIBundle({
                        url: '/docs/openapi.yaml',
                        dom_id: '#swagger-ui',
                        deepLinking: true,
                        presets: [
                            SwaggerUIBundle.presets.apis,
                            SwaggerUIStandalonePreset
                        ],
                        plugins: [
                            SwaggerUIBundle.plugins.DownloadUrl
                        ],
                        layout: "StandaloneLayout"
                    });
                };
            </script>
        </body>
        </html>
        '''
    
    @docs_bp.route('/docs/openapi.yaml')
    def openapi_spec():
        """Serve OpenAPI specification as YAML"""
        spec = create_openapi_spec()
        return yaml.dump(spec, default_flow_style=False), 200, {
            'Content-Type': 'application/x-yaml'
        }
    
    @docs_bp.route('/docs/openapi.json')
    def openapi_spec_json():
        """Serve OpenAPI specification as JSON"""
        spec = create_openapi_spec()
        return jsonify(spec)
    
    @docs_bp.route('/docs/redoc')
    def redoc_docs():
        """ReDoc documentation interface"""
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>P&L Card API Documentation - ReDoc</title>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
            <style>
                body { margin: 0; padding: 0; font-family: sans-serif; }
                .redoc-container { height: 100vh; }
            </style>
        </head>
        <body>
            <redoc spec-url="/docs/openapi.json"></redoc>
            <script src="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js"></script>
        </body>
        </html>
        '''
    
    return docs_bp

def save_openapi_spec():
    """Save OpenAPI specification to file"""
    spec = create_openapi_spec()
    
    # Save as JSON
    json_path = Path("docs/openapi.json")
    json_path.parent.mkdir(exist_ok=True)
    
    with open(json_path, 'w') as f:
        import json
        json.dump(spec, f, indent=2)
    
    # Save as YAML
    yaml_path = Path("docs/openapi.yaml")
    with open(yaml_path, 'w') as f:
        yaml.dump(spec, f, default_flow_style=False)
    
    print(f"OpenAPI spec saved to {json_path} and {yaml_path}")

# Example usage
if __name__ == "__main__":
    # Save specification files
    save_openapi_spec()
    
    # Create test app
    app = Flask(__name__)
    CORS(app)
    
    # Register docs blueprint
    docs_bp = create_docs_blueprint()
    app.register_blueprint(docs_bp)
    
    print("API Documentation available at:")
    print("- Swagger UI: http://localhost:5000/docs")
    print("- ReDoc: http://localhost:5000/docs/redoc")
    print("- OpenAPI JSON: http://localhost:5000/docs/openapi.json")
    print("- OpenAPI YAML: http://localhost:5000/docs/openapi.yaml")
    
    app.run(debug=True, port=5000)
