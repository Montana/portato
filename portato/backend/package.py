from future_builtins import map, filter, zip

from ..helper import debug, paren_reduce
from ..dependency import DependencyTree

from . import _Package, system, flags


class Package(_Package):
    def __init__(self, cpv):

        self._cpv = cpv
        self._slot = None

    def __repr__(self):
        return "<Package '%s' @0x%x>" % (self._cpv, id(self))

    __str__ = __repr__

    def set_testing(self, enable=True):

        flags.set_testing(self, enable)

    def remove_new_testing(self):

        flags.remove_new_testing(self.get_cpv())

    def set_masked(self, masking=False):

        flags.set_masked(self, masked=masking)

    def remove_new_masked(self):

        flags.remove_new_masked(self.get_cpv())

    def is_locally_masked(self):

        return flags.is_locally_masked(self)

    def get_new_use_flags(self):

        return flags.get_new_use_flags(self)

    def get_actual_use_flags(self):

        i_flags = self.get_global_settings("USE", installed=False).split()
        m_flags = system.get_global_settings("USE").split()
        for f in self.get_new_use_flags():
            removed = False

            if f[0] == "~":
                f = f[1:]
                removed = True

            invf = flags.invert_use_flag(f)

            if f[0] == "-":
                if invf in i_flags and not (removed and invf in m_flags):
                    i_flags.remove(invf)

            elif f not in i_flags:
                if not (removed and invf in m_flags):
                    i_flags.append(f)

        return i_flags

    def set_use_flag(self, flag):
        flags.set_use_flag(self, flag)

    def remove_new_use_flags(self):

        flags.remove_new_use_flags(self)

    def use_expanded(self, flag, suggest=None):
        if suggest is not None:
            if flag.startswith(suggest.lower()):
                return suggest

        for exp in self.get_global_settings("USE_EXPAND").split():
            lexp = exp.lower()
            if flag.startswith(lexp):
                return exp

        return None

    def get_cpv(self):

        return self._cpv

    def get_cp(self):

        return "/".join((self.get_category(), self.get_name()))

    def get_slot(self):

        if self._slot is None:
            self._slot = self.get_package_settings("SLOT")

        return self._slot

    def get_slot_cp(self):

        return ":".join((self.get_cp(), self.get_slot()))

    def get_package_path(self):

        p = self.get_ebuild_path()
        sp = p.split("/")
        if sp:
            return "/".join(sp[:-1])

    def get_dependencies(self):

        deps = " ".join(
            map(self.get_package_settings, ("RDEPEND", "PDEPEND", "DEPEND"))
        )
        deps = paren_reduce(deps)

        tree = DependencyTree()
        tree.parse(deps)

        return tree

    def get_name(self):

        raise NotImplementedError

    def get_version(self):

        raise NotImplementedError

    def get_category(self):

        raise NotImplementedError

    def is_installed(self):

        raise NotImplementedError

    def is_in_overlay(self):

        raise NotImplementedError

    def get_overlay_path(self):

        raise NotImplementedError

    def is_in_system(self):

        raise NotImplementedError

    def is_missing_keyword(self):

        raise NotImplementedError

    def is_testing(self, use_keywords=True):

        raise NotImplementedError

    def is_masked(self, use_changed=True):

        raise NotImplementedError

    def get_masking_reason(self):
        
        raise NotImplementedError

    def get_iuse_flags(self, installed=False, removeForced=True):

        raise NotImplementedError

    def get_global_settings(self, key, installed=True):

        raise NotImplementedError

    def get_ebuild_path(self):

        raise NotImplementedError

    def get_files(self):

        raise NotImplementedError

    def get_package_settings(self, var, installed=True):

        raise NotImplementedError

    def get_installed_use_flags(self):

        raise NotImplementedError

    def matches(self, criterion):

        raise NotImplementedError
