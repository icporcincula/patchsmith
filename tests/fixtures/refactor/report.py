from formatting import format_name

def render_people(people):
    return [format_name(first, last) for first, last in people]
