from drf_spectacular.extensions import OpenApiAuthenticationExtension


class MongoBearerScheme(OpenApiAuthenticationExtension):
    target_class = "accounts.authentication.MongoJWTAuthentication"
    name = "BearerAuth"

    def get_security_definition(self, auto_schema):
        return {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
