def format_nigerian_phone(phone: str) -> str:
    """
    Convert Nigerian phone numbers to international format.

    Example:
    08012345678 -> 2348012345678
    07012345678 -> 2347012345678
    """

    phone = phone.strip()

    if phone.startswith("+234"):
        return phone.replace("+", "")

    if phone.startswith("234"):
        return phone

    if phone.startswith("0"):
        return "234" + phone[1:]

    return phone