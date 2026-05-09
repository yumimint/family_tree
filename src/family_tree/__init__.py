import sys
from typing import Iterable, Optional, Self

import graphviz  # type: ignore


class Node:
    @property
    def node(self):
        return hex(id(self))[2:]


class Person(Node):
    def __init__(self, desc: str):
        adopted, fullname = self.inner_outer(desc, "{}")
        surname, name = self.inner_outer(fullname, "[]")
        self.adopted = adopted
        self.fullname = fullname
        self.surname = surname
        self.name = name
        self.house: Optional[Household] = None
        self.prefix = ""
        self.suffix = ""

    @property
    def surname_first(self) -> bool:
        return self.fullname[0] == "["

    @classmethod
    def new_child(cls, parent: Self, name: str) -> Self:
        surname = parent.surname
        if parent.surname_first:
            return cls(f"[{surname}]{name}")
        return cls(f"{name}[{surname}]")

    @staticmethod
    def inner_outer(s: str, brackets: str):
        open, close = brackets[0], brackets[1]
        if open in s and close in s:
            a = s.index(open) + 1
            b = s.rindex(close)
            inner = s[a:b].strip()
            outer = s[: a - 1].lstrip() + s[b + 1:].rstrip()
            return inner, outer
        return "", s

    def __repr__(self):
        return self.fullname

    @property
    def label(self):
        mei = self.name
        # 名前の*より後を除去 (同姓同名の区別用)
        if "*" in mei:
            mei = mei[:mei.index("*")]
        return " ".join([self.prefix, mei, self.suffix]).strip()


class Household(Node):
    def __init__(self):
        self.parents = []
        self.childlens = []

    @property
    def key(self) -> frozenset:
        return frozenset(map(str, self.parents))

    @property
    def name(self) -> str:
        # 最初の親の姓を家のnameとする
        return self.parents[0].surname

    def add_parnt(self, fullname: str):
        self.parents.append(Person(fullname))

    def new_child(self, name: str) -> Person:
        if not self.parents:
            raise ValueError("parent expected.")
        p = Person.new_child(self.parents[0], name)
        p.house = self
        self.childlens.append(p)
        return p

    # 後処理
    def postprocess(self, members: dict[str, Person]):
        for i, p in enumerate(self.parents):
            # 親族と紐づいていない親をフルネームから特定する
            if p.house is None:
                if p.fullname in members:
                    p = members[p.fullname]
                    self.parents[i] = p
                    continue
                # 配偶者又は始祖
                p.home = self
                # 姓・旧姓を併記する
                if p.surname:
                    # 配偶者は()で囲う
                    surname = f"({p.surname})" if i > 0 else p.surname
                    if p.surname_first:
                        p.prefix = surname
                    else:
                        p.suffix = surname

        # 生まれ順で子供に番号を振る
        if len(self.childlens) > 1:
            for i, p in enumerate(self.childlens):
                p.prefix = chr(ord("❶") + i)


class Family:
    def __init__(self):
        self.households = {}
        self.members = {}

    def populate(self, lines: Iterable[str]):
        h = Household()

        lines = map(lambda s: s.rstrip(), lines)
        lines = filter(lambda s: not s.startswith("#"), lines)
        for line in lines:
            # 要確認マーカー ? を除去
            line = line.replace("?", "")
            try:
                if len(line) < 1:
                    # 空行なら現在の家をaddして新しい家を準備
                    if h.parents:
                        self.add_household(h)
                        h = Household()
                    continue

                # print(line)
                a, b = (line + "\t").split("\t")[:2]
                if a and b:
                    raise ValueError("Invalid row")
                elif a and not b:
                    if h.childlens:
                        # 現在の家をaddして新しい家を準備
                        self.add_household(h)
                        h = Household()
                    h.add_parnt(a)
                else:
                    h.new_child(b)
            except Exception as e:
                if line:
                    raise type(e)(f"{e} : {line}")
                else:
                    raise e

        if h.parents:
            self.add_household(h)

        return self

    def add_household(self, h: Household):
        if not h.parents:
            # 空き家
            return

        if h.key in self.households:
            # 複数のスプレッドシートをマージする場合を考慮し、
            # 既存の家なら除外する。
            print("skip: " + str(h.key), file=sys.stderr)
            return

        for p in h.childlens:
            if p.fullname in self.members:
                raise ValueError(
                    f"{p.fullname} : A name conflict has been detected.")
            self.members[p.fullname] = p

        self.households[h.key] = h

    # 後処理
    def postprocess(self):
        for h in self.households.values():
            h.postprocess(self.members)

    def build_tree(self, g: graphviz.Graph):
        once = set()

        def add_person(p: Person):
            if p not in once:
                once.add(p)
                g.node(p.node, p.label)

        for h in self.households.values():
            g.node(h.node, h.name, shape="house")
            for p in h.parents:
                add_person(p)
                g.edge(p.node, h.node, color="blue")
            for p in h.childlens:
                add_person(p)
                g.edge(h.node, p.node)
                # 養子
                if p.adopted:
                    ad = self.members.get(p.adopted)
                    if ad is None:
                        ad = Person(p.adopted)
                        add_person(ad)
                    with g.subgraph() as s:
                        s.attr(rank="same")
                        s.node(ad.node)
                        s.node(p.node)
                        s.edge(ad.node, p.node)

        print("{} persons in a tree".format(len(once)))


def make_pdf(f: Family, filename: str, view=False, label: Optional[str] = None):
    g = graphviz.Graph(format="pdf", filename=filename)
    g.attr("node", fontname="IPAGothic")
    # g.attr("node", fontname="MS PMincho")
    g.attr("graph", rankdir="LR")
    if label:
        g.attr("graph", labelloc="t", label=label)
    f.build_tree(g)
    if view:
        g.view(cleanup=True)
    else:
        g.render(cleanup=True)
