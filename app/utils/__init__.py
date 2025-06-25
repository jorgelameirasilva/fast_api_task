"""Utility functions for the application"""


def make_json_serializable(obj):
    """Convert objects to JSON-serializable format"""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    elif hasattr(obj, "__dict__"):
        result = {}
        for key, value in obj.__dict__.items():
            if not key.startswith("_"):
                result[key] = make_json_serializable(value)
        return result
    elif isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    else:
        return obj
