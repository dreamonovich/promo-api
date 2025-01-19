import uuid


def is_valid_uuid(*uuid_list) -> bool:
    try:
        for uuid_val in uuid_list:
            uuid.UUID(str(uuid_val))
        return True
    except ValueError:
        return False