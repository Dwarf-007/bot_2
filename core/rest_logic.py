
def is_rest_requested(text: str):
    text = text.lower()

    if "long rest" in text:
        return "LONG"

    if "short rest" in text:
        return "SHORT"

    return None


def evaluate_rest_outcome(response):
    return {
        "success": False,
        "interrupted": False,
    }


def build_rest_summary(rest):
    return rest
