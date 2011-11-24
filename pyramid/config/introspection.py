import operator

from zope.interface import implementer

from pyramid.interfaces import (
    IIntrospector,
    IIntrospectable
    )

@implementer(IIntrospector)
class Introspector(object):
    action_info = None
    def __init__(self):
        self._refs = {}
        self._categories = {}
        self._counter = 0

    def add(self, category_name, discriminator):
        category = self._categories.setdefault(category_name, {})
        intr = category.get(discriminator)
        if intr is None:
            intr = Introspectable(category_name, discriminator)
            category[intr.discriminator] = intr
            category[intr.discriminator_hash] = intr
            intr.order = self._counter
        self._counter += 1
        return intr

    # for adding custom introspectables (instead of using .add)

    def add_intr(self, intr):
        category = self._categories.setdefault(intr.category_name, {})
        category[intr.discriminator] = intr
        category[intr.discriminator_hash] = intr
        intr.order = self._counter
        self._counter += 1

    def get(self, category_name, discriminator, default=None):
        category = self._categories.setdefault(category_name, {})
        intr = category.get(discriminator, default)
        return intr

    def get_category(self, category_name, sort_fn=None):
        if sort_fn is None:
            sort_fn = operator.attrgetter('order')
        category = self._categories[category_name]
        values = category.values()
        values = sorted(set(values), key=sort_fn)
        return [{'introspectable':intr, 'related':self.related(intr)} for
                intr in values]

    def categorized(self, sort_fn=None):
        L = []
        for category_name in sorted(self._categories.keys()):
            L.append((category_name, self.get_category(category_name, sort_fn)))
        return L

    def remove(self, category_name, discriminator):
        intr = self.get(category_name, discriminator)
        if intr is None:
            return
        L = self._refs.pop((category_name, discriminator), [])
        for d in L:
            L2 = self._refs[d]
            L2.remove((category_name, discriminator))
        category = self._categories[intr.category_name]
        del category[intr.discriminator]
        del category[intr.discriminator_hash]

    def _get_intrs_by_pairs(self, pairs):
        introspectables = []
        for pair in pairs:
            category_name, discriminator = pair
            intr = self._categories.get(category_name, {}).get(discriminator)
            if intr is None:
                import pdb; pdb.set_trace()
                raise KeyError((category_name, discriminator))
            introspectables.append(intr)
        return introspectables

    def relate(self, *pairs):
        introspectables = self._get_intrs_by_pairs(pairs)
        relatable = ((x,y) for x in introspectables for y in introspectables)
        for x, y in relatable:
            L = self._refs.setdefault(x, [])
            if x is not y and y not in L:
                L.append(y)

    def unrelate(self, *pairs):
        introspectables = self._get_intrs_by_pairs(pairs)
        relatable = ((x,y) for x in introspectables for y in introspectables)
        for x, y in relatable:
            L = self._refs.get(x, [])
            if y in L:
                L.remove(y)

    def related(self, intr):
        category_name, discriminator = intr.category_name, intr.discriminator
        intr = self._categories.get(category_name, {}).get(discriminator)
        if intr is None:
            raise KeyError((category_name, discriminator))
        return self._refs.get(intr, [])

@implementer(IIntrospectable)
class Introspectable(dict):

    order = 0 # mutated by .add/.add_intr
    action_info = ''

    def __init__(self, category_name, discriminator):
        self.category_name = category_name
        self.discriminator = discriminator
        self.relations = []
        self.unrelations = []

    def relate(self, category_name, discriminator):
        self.relations.append((category_name, discriminator))

    def unrelate(self, category_name, discriminator):
        self.unrelations.append((category_name, discriminator))

    def __call__(self, introspector, action_info):
        self.action_info = action_info
        introspector.add_intr(self)
        for category_name, discriminator in self.relations:
            introspector.relate((self.category_name, self.discriminator),
                                (category_name, discriminator))

        for category_name, discriminator in self.unrelations:
            introspector.unrelate((self.category_name, self.discriminator),
                                  (category_name, discriminator))

    @property
    def discriminator_hash(self):
        return hash(self.discriminator)

    @property
    def related(self, introspector):
        return introspector.related(self)

    def text(self):
        result = [repr(self.discriminator)]
        for k, v in self.items():
            result.append('%s: %s' % (k, v))
        result.append('action_info: %s' % (self.action_info,))
        return '\n'.join(result)

    def __hash__(self):
        return hash((self.category_name,) + (self.discriminator,))

    def __repr__(self):
        return '<%s category %r, discriminator %r>' % (self.__class__.__name__,
                                                       self.category_name,
                                                       self.discriminator)

    def __nonzero__(self):
        return True

    __bool__ = __nonzero__ # py3
                                                       
class IntrospectionConfiguratorMixin(object):
    introspectable = Introspectable

    @property
    def introspector(self):
        introspector = getattr(self.registry, 'introspector', None)
        if introspector is None:
            introspector = Introspector()
            self.registry.introspector = introspector
        return introspector
