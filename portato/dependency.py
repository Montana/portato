# .backend adds and returns a subtree. - Montana

__docformat__ = "restructuredtext"

from collections import defaultdict

from .helper import debug
from .backend import system


class Dependency(object):
    def __init__(self, dep):

        self._dep = dep

    def is_satisfied(self):
        (
            system.find_best_match(self.dep, only_cpv=True, only_installed=True)
            is not None
        )

    def __cmp__(self, b):
        return cmp(self.dep, b.dep)

    def __hash__(self):
        return hash(self.dep)

    def __str__(self):
        return "<Dependency '%s'>" % self.dep

    __repr__ = __str__

    @property
    def dep(self):
        return self._dep

    satisfied = property(is_satisfied)


class DependencyTree(object):
    def __init__(self):

        self.deps = set()
        self.flags = defaultdict(UseDependency)
        self._ors = []
        self._subs = []

    def is_empty(self):
        return not (self.deps or self.flags or self._ors or self._subs)

    empty = property(is_empty)

    def add(self, dep, *moredeps):

        self.deps.add(Dependency(dep))

        for dep in moredeps:
            self.deps.add(Dependency(dep))

    def add_or(self):

        o = OrDependency()
        self._ors.append(o)
        return o

    def add_sub(self):

        return self

    def add_flag(self, flag):

        return self.flags[flag]  # it's a defaultdict

    def parse(self, deps):

        it = iter(deps)
        for dep in it:

            # use
            if dep[-1] == "?":
                ntree = self.add_flag(dep[:-1])
                n = next(it)
                if not hasattr(n, "__iter__"):
                    n = [n]
                ntree.parse(n)

            # or
            elif dep == "||":
                n = next(it)  # skip
                if not hasattr(n, "__iter__"):
                    n = [n]

                self.add_or().parse(n)

            # sub
            elif isinstance(dep, list):
                self.add_sub().parse(dep)

            # normal
            else:
                self.add(dep)

    def get_non_empty(self, l):

        for d in l[:]:
            if d.is_empty():
                l.remove(d)
            else:
                yield d

    def get_ors(self):
        return self.get_non_empty(self._ors)

    def get_subs(self):
        return self.get_non_empty(self._subs)

    ors = property(get_ors)
    subs = property(get_subs)


class OrDependency(DependencyTree):
    def add_sub(self):
        s = DependencyTree()
        self._subs.append(s)
        return s


class UseDependency(DependencyTree):

    pass
