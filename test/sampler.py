from logging import getLogger
from pathlib import Path
from subprocess import run

log = getLogger(__name__)


class base:
    def __init__(self, name, mode):
        self.name = name
        self.mode = mode
        self.container = None
        self._path = None
        log.debug("%s %r", self.__class__.__name__, self.name)

    def __getattr__(self, item):
        return getattr(self.path, item)

    @property
    def path(self):
        if not self._path:
            if self.container:
                self._path = self.container.path / self.name
            else:
                self._path = Path(self.name)
        return self._path

    def make(self):
        raise NotImplementedError(self.__class__.__name__ + ".make")

    def clean(self):
        log.info("clean %s %s", self.__class__.__name__, self.path)
        self.unlink()


class dir(base):
    def __init__(self, name, *, mode=0o777):
        super().__init__(name, mode)
        self.contents = []

    def __call__(self, *args):
        for arg in args:
            self.contents.append(arg)
            arg.container = self
        return self

    def make(self):
        log.info("make dir %s", self.path)
        self.mkdir(exist_ok=True)
        for content in self.contents:
            content.make()
        return self

    def clean(self):
        for content in self.contents:
            content.clean()
        log.info("clean %s %s", self.__class__.__name__, self.path)
        self.rmdir()


class file(base):
    def __init__(self, name, *, mode=0o666, size=0):
        super().__init__(name, mode)
        self.size = size

    def make(self):
        log.info("make file %s", self.path)
        with self.open("wb") as fo:
            data = bytes(4096)
            for i in range(self.size // 4096):
                fo.write(data)
            fo.write(bytes(self.size % 4096))
        return self


class link(base):
    def __init__(self, name, target, *, mode=0o666):
        super().__init__(name, mode)
        self.target = target

    def make(self):
        log.info("make link %s -> %s", self.path, self.target)
        if self.is_symlink():
            self.unlink()
        self.symlink_to(self.target)
        return self


def mktree1():
    dir("sample")(
        file("file1", size=2 ** 20),
        file("file2", size=2 ** 10 + 1),
        dir("dir2")(
            file("f1"),
            link("link1", "target1")
        ),
        dir("1KBdir")(
            file("1KBfile", size=2 ** 10)
        )
    ).make().clean()


def tree2():
    tree = dir("topdir")(
        dir("subdir")
    ).make()
    log.info("run %r", ["lss", str(tree.path)])
    run(["lss", str(tree.path)])
    tree.clean()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG)
    tree2()
