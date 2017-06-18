import asyncio
import os
import sys
import logging
from typing import Any, Dict, List, Optional, Callable


class Watcher(object):
    def __init__(self, root: Optional[List]=None, configuration: Optional[Dict]=None) -> None:
        self.watched_files = {}  # type: Dict[str, float]
        self.root = []  # type: List[str]
        self.ignored_dirs = ['__pycache__', '.git', '.svn', '__ignored__', '__temporary__', '__tmp__']
        self.watched_file_endings = ['.py', '.json', '.yml', '.html', '.phtml']

        if not root:
            directory = os.path.realpath(sys.argv[0].rsplit('/', 1)[0])
            if os.path.isfile(directory):
                directory = os.path.dirname(directory)
            self.root = [directory]
        else:
            self.root = root

        if configuration is not None:
            ignored_dirs_list = configuration.get('options', {}).get('watcher', {}).get('ignored_dirs', [])
            if ignored_dirs_list:
                self.ignored_dirs.extend(ignored_dirs_list)

        self.update_watched_files()

    def update_watched_files(self) -> Dict:
        watched_files = {}
        for r in self.root:
            for root, dirs, files in os.walk(r):
                for file in files:
                    _dir = os.path.dirname(os.path.join(root, file))
                    if _dir not in self.ignored_dirs and not any([os.path.join(root, _dir).endswith('/{}'.format(ignored_dir)) or '/{}/'.format(ignored_dir) in os.path.join(root, _dir) for ignored_dir in self.ignored_dirs]) and any([file.endswith(ending) for ending in self.watched_file_endings]) and '/.' not in os.path.join(root, file):
                        watched_files[(os.path.join(root, file))] = os.path.getmtime(os.path.join(root, file))

        if self.watched_files and self.watched_files != watched_files:
            added = [k[((len(self.root[0]) if k.startswith(self.root[0]) else -1) + 1):] for k in watched_files.keys() if k not in self.watched_files.keys()]
            removed = [k[((len(self.root[0]) if k.startswith(self.root[0]) else -1) + 1):] for k in self.watched_files.keys() if k not in watched_files.keys()]
            updated = [k[((len(self.root[0]) if k.startswith(self.root[0]) else -1) + 1):] for k in watched_files.keys() if k in self.watched_files.keys() and self.watched_files[k] != watched_files[k]]
            self.watched_files = watched_files
            return {'added': added, 'removed': removed, 'updated': updated}
        self.watched_files = watched_files
        return {}

    async def watch(self, loop: asyncio.AbstractEventLoop=None, callback_func: Optional[Callable]=None) -> Any:
        _loop = asyncio.get_event_loop() if not loop else loop  # type: Any

        async def _watch_loop() -> None:
            while True:
                updated_files = self.update_watched_files()
                if updated_files:
                    added = updated_files.get('added')
                    removed = updated_files.get('removed')
                    updated = updated_files.get('updated')
                    if removed:
                        if len(removed) > 2:
                            removed[2] = '...'
                        logging.getLogger('watcher.files').warning('Removed files: {}'.format(', '.join([file for file in removed][0:3])))
                    if added:
                        if len(added) > 2:
                            added[2] = '...'
                        logging.getLogger('watcher.files').warning('New files: {}'.format(', '.join([file for file in added][0:3])))
                    if updated:
                        if len(updated) > 2:
                            updated[2] = '...'
                        logging.getLogger('watcher.files').warning('Updated files: {}'.format(', '.join([file for file in updated][0:3])))

                    if callback_func:
                        await callback_func()
                await asyncio.sleep(0.5)

        return _loop.create_task(_watch_loop())
