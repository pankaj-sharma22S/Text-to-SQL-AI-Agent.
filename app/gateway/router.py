from enum import Enum

class GatewayRoute(str, Enum):
    chat = "chat"
    sql = "sql"
    ambiguous = "ambiguous"
    blocked = "blocked"
