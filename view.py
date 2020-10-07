from typing import List, Tuple

import flask


def wants_json(req: flask.Request) -> bool:
    """
    returns whether or not this request expects a JSON response
    :param req: a flask Request object
    :return: whether or not this request expects a JSON response
    """
    return req.headers['Accept'] == 'application/json' or 'json' in req.args


def register_filters(app: flask.Flask):
    """
    Register template filters for dealing with paths, diffs and sizes of things
    :param app: a Flask application
    """
    @app.template_filter('human')
    def sizeof_fmt(size: int) -> str:
        """
        Returns a human readable size from
        :param size: size in byes
        :return: a human readable string representing the given size
        """
        for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
            if abs(size) < 1024.0:
                return "%3.1f%s%s" % (size, unit, 'B')
            size /= 1024.0
        return "%.1f%s%s" % (size, 'Yi', 'B')

    @app.template_filter('parent')
    def parent_filter(path: str, delimiter: str) -> str:
        left, delim, _ = path.rpartition(delimiter)
        return left + delim

    @app.template_filter('split_path')
    def split_path_filter(path: str, delimiter: str) -> List[Tuple[str, str]]:
        parts = path.split(delimiter)
        split_result = []
        for i, part in enumerate(parts):
            if i == len(parts) - 1 and not part:
                continue
            absolute = delimiter.join(parts[:i + 1]) + (
                '' if i == len(parts) - 1 and not path.endswith(delimiter) else delimiter)
            split_result.append((absolute, part))
        return split_result
