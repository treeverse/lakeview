from typing import List

from werkzeug.exceptions import HTTPException
from flask import Blueprint, render_template, request, jsonify
from flask_caching import Cache

import loader
from du import size_for, diff_for
from view import wants_json


def error_handler(e):
    error = e.original_exception
    if wants_json(request):
        return jsonify(error=error), 500
    return render_template('error.html', error=error)


class AthenaController(object):

    def __init__(self, db: loader.Inventory, cache: Cache):
        self.db = db
        self.cache = cache

    def as_blueprint(self) -> Blueprint:
        bp = Blueprint('athena_controllers', __name__)
        bp.route('/')(self.index_handler)
        bp.route('/du')(self.du_handler)
        bp.errorhandler(HTTPException)(error_handler)
        return bp

    def index_handler(self):
        """
        Render the index page (listing all available inventory dates)
        """
        return render_template('index.html', dates=reversed(self._enumerate_dates()))

    def du_handler(self):
        """
        Find the sizes of prefixes. Diff said sizes with other inventory dates
        """
        prefix = request.args.get('prefix') or ''
        delimiter = request.args.get('delimiter') or '/'
        date = request.args.get('date')

        compare_with_date = request.args.get('compare')
        if compare_with_date:
            cache_key = f'diff:{date}:{compare_with_date}:{delimiter}:{prefix}'
            res = self.cache.get(cache_key)
            if not res:
                res = diff_for(self.db, date, compare_with_date, prefix, delimiter)
                self.cache.set(cache_key, res)
        else:
            cache_key = f'du:{date}:{delimiter}:{prefix}'
            res = self.cache.get(cache_key)
            if not res:
                res = size_for(self.db, date, prefix, delimiter)
                self.cache.set(cache_key, res)

        if wants_json(request):
            json_kwargs = {
                'prefix': prefix,
                'delimiter': delimiter,
                'date': date,
                'compare': compare_with_date,
                'response': res,
            }
            return jsonify(**json_kwargs)

        return render_template(
            'du.html',
            prefix=prefix,
            delimiter=delimiter,
            date=date,
            compare_with_date=compare_with_date,
            response=res,
            available_dates=reversed(self._enumerate_dates())
        )

    def _enumerate_dates(self) -> List[str]:
        """
        list all available dates as present in the S3 inventory
        :return: a list of date strings as exists in the inventory listing
        """
        cached_dates = self.cache.get('inventory_dates')
        if cached_dates:
            return cached_dates
        res = self.db.query('SHOW PARTITIONS {table_name}')
        cached_dates = list([f.get('row').lstrip('dt=') for f in res])
        cached_dates.sort()
        self.cache.set('inventory_dates', cached_dates, timeout=600)
        return cached_dates

