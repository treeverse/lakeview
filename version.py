
import os
from typing import Optional

from packaging import version
import requests


DEV_VERSION = "dev"
VERSION = os.getenv("LAKEVIEW_VERSION", "dev")
VERSION_URI = "https://stats.treeverse.io/lakeview"
VERSION_UA = "lakeview_version_check"
RELEASES_URL = "https://hub.docker.com/repository/docker/treeverse/lakeview"


def get_latest_version() -> Optional[str]:
    """
    Check if there's a newer lakeview version
    :return: a newer version if exists, or None if we're at the latest version already
    """
    if VERSION == DEV_VERSION:
        return None  # we don't compare dev versions
    try:
        response = requests.get(
            VERSION_URI,
            params={'version': VERSION},
            headers={'User-Agent': VERSION_UA},
            timeout=2  # Since this is not critical for lakeview to function, let's be aggressive
        )
        latest = response.json().get('latest')
        if version.parse(latest) > version.parse(VERSION):
            return latest
    except Exception as e:
        print(f'[WARNING] could not check what the latest lakeview version is: {e}\n'
              f'\tFeel free to check at {RELEASES_URL}')
    return None
