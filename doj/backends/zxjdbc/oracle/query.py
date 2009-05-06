"""
Custom Query class for Oracle.
Derives from: django.db.models.sql.query.Query

Modifications Made By:  Josh Juneau
Modified Date:  04/2009
"""

import datetime

from django.db.backends import util

# Cache. Maps default query class to new Oracle query class.
_classes = {}

def query_class(QueryClass, Database):
    """
    Returns a custom django.db.models.sql.query.Query subclass that is
    appropriate for Oracle.

    The 'Database' module (cx_Oracle) is passed in here so that all the setup
    required to import it only needs to be done by the calling module.
    """
    global _classes
    try:
        return _classes[QueryClass]
    except KeyError:
        pass

    class OracleQuery(QueryClass):
        def resolve_columns(self, row, fields=()):
            index_start = len(self.extra_select.keys())
            values = [self.convert_values(v, type(v)) for v in row[:index_start]]
            for value, field in map(None, row[index_start:], fields):
                values.append(self.convert_values(value, field))
            return values

        def convert_values(self, value, field):
            from django.db.models.fields import DateField, DateTimeField, \
                 TimeField, BooleanField, NullBooleanField, DecimalField, FloatField, Field

            # Oracle stores empty strings as null. We need to undo this in
            # order to adhere to the Django convention of using the empty
            # string instead of null, but only if the field accepts the
            # empty string.

            if value is None and field.empty_strings_allowed:
                value = u''
            # Convert 1 or 0 to True or False
            elif value is not None and isinstance(value, float):
                value = float(value)
            # Added 04-26-2009 to repair "Invalid literal for int() base 10" error
            elif value is not None and isinstance(value,int):
                value = int(value)
            elif value is not None and field is not None and field.get_internal_type() == 'AutoField':
                value = int(float(value))
            elif value in (1, 0) and field is not None and field.get_internal_type() in ('BooleanField', 'NullBooleanField'):
                value = bool(value)
            # Force floats to the correct type
            elif value is not None and field is not None and field.get_internal_type() == 'FloatField':
                value = float(value)
            # Convert floats to decimals
            elif value is not None and field is not None and field.get_internal_type() == 'DecimalField':
                value = util.typecast_decimal(field.format_number(value))
            elif value is not None and field is not None and field.get_internal_type() == 'SmallIntegerField':
                value = util.typecast_decimal(field.format_number(value))
            # This is a workaround fix to repair float issue while using Oracle.
            # Ultimately, we will need to determine why the floats are being returned as opposed to int values,
            # but the workaround is a temporary resolution.
           # elif value is not None and field is not None and field.get_internal_type() == 'TextField':
           #     if '.' in value and field.get_internal_type() != 'DateTimeField':
           #         if value[0:1].isdigit():
           #             value = int(float(value))
           #             print 'float in str: ', value
           #         else:
           #             pass
            elif value is not None:
                pass
            return value

        def as_sql(self, with_limits=True, with_col_aliases=False):
            """
            Creates the SQL for this query. Returns the SQL string and list
            of parameters.  This is overriden from the original Query class
            to handle the additional SQL Oracle requires to emulate LIMIT
            and OFFSET.

            If 'with_limits' is False, any limit/offset information is not
            included in the query.
            """

            # The `do_offset` flag indicates whether we need to construct
            # the SQL needed to use limit/offset with Oracle.
            do_offset = with_limits and (self.high_mark is not None
                                         or self.low_mark)
            if not do_offset:
                sql, params = super(OracleQuery, self).as_sql(with_limits=False,
                        with_col_aliases=with_col_aliases)
            else:
                # `get_columns` needs to be called before `get_ordering` to
                # populate `_select_alias`.
                self.pre_sql_setup()
                self.get_columns()
                #ordering = self.get_ordering()
                #
                # Removed Ordering on 03/27/2009 as it caused error:
                # TypeError: sequence item 0: expected string, list found
                #
                ordering = False
                # Oracle's ROW_NUMBER() function requires an ORDER BY clause.
                if ordering:
                    rn_orderby = ', '.join(ordering)
                else:
                    # Create a default ORDER BY since none was specified.
                    qn = self.quote_name_unless_alias
                    opts = self.model._meta
                    rn_orderby = '%s.%s' % (qn(opts.db_table),
                        qn(opts.fields[0].db_column or opts.fields[0].column))

                # Ensure the base query SELECTs our special "_RN" column
                self.extra_select['_RN'] = ('ROW_NUMBER() OVER (ORDER BY %s)'
                                            % rn_orderby, '')
                sql, params = super(OracleQuery, self).as_sql(with_limits=False,
                                                        with_col_aliases=True)

                # Wrap the base query in an outer SELECT * with boundaries on
                # the "_RN" column.  This is the canonical way to emulate LIMIT
                # and OFFSET on Oracle.
                sql = 'SELECT * FROM (%s) WHERE "_RN" > %d' % (sql, self.low_mark)
                if self.high_mark is not None:
                    sql = '%s AND "_RN" <= %d' % (sql, self.high_mark)
            return sql, params

        def set_limits(self, low=None, high=None):
            super(OracleQuery, self).set_limits(low, high)
            # We need to select the row number for the LIMIT/OFFSET sql.
            # A placeholder is added to extra_select now, because as_sql is
            # too late to be modifying extra_select.  However, the actual sql
            # depends on the ordering, so that is generated in as_sql.
            self.extra_select['_RN'] = ('1', '')

        def clear_limits(self):
            super(OracleQuery, self).clear_limits()
            if '_RN' in self.extra_select:
                del self.extra_select['_RN']

    _classes[QueryClass] = OracleQuery
    return OracleQuery

class QuerySet(object):
    """
    Represents a lazy database lookup for a set of objects.
    """
    def __init__(self, model=None, query=None):
        self.model = model
        self.query = query or sql.Query(self.model, connection)
        self._result_cache = None
        self._iter = None
        self._sticky_filter = False

    ########################
    # PYTHON MAGIC METHODS #
    ########################

    def __getstate__(self):
        """
        Allows the QuerySet to be pickled.
        """
        # Force the cache to be fully populated.
        len(self)

        obj_dict = self.__dict__.copy()
        obj_dict['_iter'] = None
        return obj_dict

    def __repr__(self):
        data = list(self[:REPR_OUTPUT_SIZE + 1])
        if len(data) > REPR_OUTPUT_SIZE:
            data[-1] = "...(remaining elements truncated)..."
        return repr(data)

    def __len__(self):
        # Since __len__ is called quite frequently (for example, as part of
        # list(qs), we make some effort here to be as efficient as possible
        # whilst not messing up any existing iterators against the QuerySet.
        if self._result_cache is None:
            if self._iter:
                self._result_cache = list(self._iter)
            else:
                self._result_cache = list(self.iterator())
        elif self._iter:
            self._result_cache.extend(list(self._iter))
        return len(self._result_cache)

    def __iter__(self):
        if self._result_cache is None:
            self._iter = self.iterator()
            self._result_cache = []
        if self._iter:
            return self._result_iter()
        # Python's list iterator is better than our version when we're just
        # iterating over the cache.
        return iter(self._result_cache)

    def _result_iter(self):
        pos = 0
        while 1:
            upper = len(self._result_cache)
            while pos < upper:
                yield self._result_cache[pos]
                pos = pos + 1
            if not self._iter:
                raise StopIteration
            if len(self._result_cache) <= pos:
                self._fill_cache()

    def __nonzero__(self):
        if self._result_cache is not None:
            return bool(self._result_cache)
        try:
            iter(self).next()
        except StopIteration:
            return False
        return True

    def __getitem__(self, k):
        """
        Retrieves an item or slice from the set of results.
        """
        if not isinstance(k, (slice, int, long)):
            raise TypeError
        assert ((not isinstance(k, slice) and (k >= 0))
                or (isinstance(k, slice) and (k.start is None or k.start >= 0)
                    and (k.stop is None or k.stop >= 0))), \
                "Negative indexing is not supported."

        if self._result_cache is not None:
            if self._iter is not None:
                # The result cache has only been partially populated, so we may
                # need to fill it out a bit more.
                if isinstance(k, slice):
                    if k.stop is not None:
                        # Some people insist on passing in strings here.
                        bound = int(k.stop)
                    else:
                        bound = None
                else:
                    bound = k + 1
                if len(self._result_cache) < bound:
                    self._fill_cache(bound - len(self._result_cache))
            return self._result_cache[k]

        if isinstance(k, slice):
            qs = self._clone()
            if k.start is not None:
                start = int(k.start)
            else:
                start = None
            if k.stop is not None:
                stop = int(k.stop)
            else:
                stop = None
            qs.query.set_limits(start, stop)
            return k.step and list(qs)[::k.step] or qs
        try:
            qs = self._clone()
            qs.query.set_limits(k, k + 1)
            return list(qs)[0]
        except self.model.DoesNotExist, e:
            raise IndexError, e.args

    def __and__(self, other):
        self._merge_sanity_check(other)
        if isinstance(other, EmptyQuerySet):
            return other._clone()
        combined = self._clone()
        combined.query.combine(other.query, sql.AND)
        return combined

    def __or__(self, other):
        self._merge_sanity_check(other)
        combined = self._clone()
        if isinstance(other, EmptyQuerySet):
            return combined
        combined.query.combine(other.query, sql.OR)
        return combined

    ####################################
    # METHODS THAT DO DATABASE QUERIES #
    ####################################

    def iterator(self):
        """
        An iterator over the results from applying this QuerySet to the
        database.
        """
        fill_cache = self.query.select_related
        if isinstance(fill_cache, dict):
            requested = fill_cache
        else:
            requested = None
        max_depth = self.query.max_depth

        extra_select = self.query.extra_select.keys()
        aggregate_select = self.query.aggregate_select.keys()

        index_start = len(extra_select)
        aggregate_start = index_start + len(self.model._meta.fields)

        for row in self.query.results_iter():
            if fill_cache:
                obj, aggregate_start = get_cached_row(self.model, row,
                                    index_start, max_depth, requested=requested)
            else:
                # omit aggregates in object creation
                obj = self.model(*row[index_start:aggregate_start])

            for i, k in enumerate(extra_select):
                setattr(obj, k, row[i])

            # Add the aggregates to the model
            for i, aggregate in enumerate(aggregate_select):
                setattr(obj, aggregate, row[i+aggregate_start])

            yield obj

    def aggregate(self, *args, **kwargs):
        """
        Returns a dictionary containing the calculations (aggregation)
        over the current queryset

        If args is present the expression is passed as a kwarg ussing
        the Aggregate object's default alias.
        """
        for arg in args:
            kwargs[arg.default_alias] = arg

        for (alias, aggregate_expr) in kwargs.items():
            self.query.add_aggregate(aggregate_expr, self.model, alias,
                is_summary=True)

        return self.query.get_aggregation()

    def count(self):
        """
        Performs a SELECT COUNT() and returns the number of records as an
        integer.

        If the QuerySet is already fully cached this simply returns the length
        of the cached results set to avoid multiple SELECT COUNT(*) calls.
        """
        if self._result_cache is not None and not self._iter:
            return len(self._result_cache)

        return self.query.get_count()

    def get(self, *args, **kwargs):
        """
        Performs the query and returns a single object matching the given
        keyword arguments.
        """
        clone = self.filter(*args, **kwargs)
        try:
            num = len(clone)
        except TypeError:
            pass
        if num == 1:
            return clone._result_cache[0]
        if not num:
            raise self.model.DoesNotExist("%s matching query does not exist."
                    % self.model._meta.object_name)
        raise self.model.MultipleObjectsReturned("get() returned more than one %s -- it returned %s! Lookup parameters were %s"
                % (self.model._meta.object_name, num, kwargs))

    def create(self, **kwargs):
        """
        Creates a new object with the given kwargs, saving it to the database
        and returning the created object.
        """
        obj = self.model(**kwargs)
        obj.save(force_insert=True)
        return obj

    def get_or_create(self, **kwargs):
        """
        Looks up an object with the given kwargs, creating one if necessary.
        Returns a tuple of (object, created), where created is a boolean
        specifying whether an object was created.
        """
        assert kwargs, \
                'get_or_create() must be passed at least one keyword argument'
        defaults = kwargs.pop('defaults', {})
        try:
            return self.get(**kwargs), False
        except self.model.DoesNotExist:
            try:
                params = dict([(k, v) for k, v in kwargs.items() if '__' not in k])
                params.update(defaults)
                obj = self.model(**params)
                sid = transaction.savepoint()
                obj.save(force_insert=True)
                transaction.savepoint_commit(sid)
                return obj, True
            except IntegrityError, e:
                transaction.savepoint_rollback(sid)
                try:
                    return self.get(**kwargs), False
                except self.model.DoesNotExist:
                    raise e

    def latest(self, field_name=None):
        """
        Returns the latest object, according to the model's 'get_latest_by'
        option or optional given field_name.
        """
        latest_by = field_name or self.model._meta.get_latest_by
        assert bool(latest_by), "latest() requires either a field_name parameter or 'get_latest_by' in the model"
        assert self.query.can_filter(), \
                "Cannot change a query once a slice has been taken."
        obj = self._clone()
        obj.query.set_limits(high=1)
        obj.query.add_ordering('-%s' % latest_by)
        return obj.get()

    def in_bulk(self, id_list):
        """
        Returns a dictionary mapping each of the given IDs to the object with
        that ID.
        """
        assert self.query.can_filter(), \
                "Cannot use 'limit' or 'offset' with in_bulk"
        assert isinstance(id_list, (tuple,  list)), \
                "in_bulk() must be provided with a list of IDs."
        if not id_list:
            return {}
        qs = self._clone()
        qs.query.add_filter(('pk__in', id_list))
        return dict([(obj._get_pk_val(), obj) for obj in qs.iterator()])

    def delete(self):
        """
        Deletes the records in the current QuerySet.
        """
        assert self.query.can_filter(), \
                "Cannot use 'limit' or 'offset' with delete."

        del_query = self._clone()

        # Disable non-supported fields.
        del_query.query.select_related = False
        del_query.query.clear_ordering()

        # Delete objects in chunks to prevent the list of related objects from
        # becoming too long.
        while 1:
            # Collect all the objects to be deleted in this chunk, and all the
            # objects that are related to the objects that are to be deleted.
            seen_objs = CollectedObjects()
            for object in del_query[:CHUNK_SIZE]:
                object._collect_sub_objects(seen_objs)

            if not seen_objs:
                break
            delete_objects(seen_objs)

        # Clear the result cache, in case this QuerySet gets reused.
        self._result_cache = None
    delete.alters_data = True

    def update(self, **kwargs):
        """
        Updates all elements in the current QuerySet, setting all the given
        fields to the appropriate values.
        """
        assert self.query.can_filter(), \
                "Cannot update a query once a slice has been taken."
        query = self.query.clone(sql.UpdateQuery)
        query.add_update_values(kwargs)
        rows = query.execute_sql(None)
        transaction.commit_unless_managed()
        self._result_cache = None
        return rows
    update.alters_data = True

    def _update(self, values):
        """
        A version of update that accepts field objects instead of field names.
        Used primarily for model saving and not intended for use by general
        code (it requires too much poking around at model internals to be
        useful at that level).
        """
        assert self.query.can_filter(), \
                "Cannot update a query once a slice has been taken."
        query = self.query.clone(sql.UpdateQuery)
        query.add_update_fields(values)
        self._result_cache = None
        return query.execute_sql(None)
    _update.alters_data = True

    ##################################################
    # PUBLIC METHODS THAT RETURN A QUERYSET SUBCLASS #
    ##################################################

    def values(self, *fields):
        return self._clone(klass=ValuesQuerySet, setup=True, _fields=fields)

    def values_list(self, *fields, **kwargs):
        flat = kwargs.pop('flat', False)
        if kwargs:
            raise TypeError('Unexpected keyword arguments to values_list: %s'
                    % (kwargs.keys(),))
        if flat and len(fields) > 1:
            raise TypeError("'flat' is not valid when values_list is called with more than one field.")
        return self._clone(klass=ValuesListQuerySet, setup=True, flat=flat,
                _fields=fields)

    def dates(self, field_name, kind, order='ASC'):
        """
        Returns a list of datetime objects representing all available dates for
        the given field_name, scoped to 'kind'.
        """
        assert kind in ("month", "year", "day"), \
                "'kind' must be one of 'year', 'month' or 'day'."
        assert order in ('ASC', 'DESC'), \
                "'order' must be either 'ASC' or 'DESC'."
        return self._clone(klass=DateQuerySet, setup=True,
                _field_name=field_name, _kind=kind, _order=order)

    def none(self):
        """
        Returns an empty QuerySet.
        """
        return self._clone(klass=EmptyQuerySet)

    ##################################################################
    # PUBLIC METHODS THAT ALTER ATTRIBUTES AND RETURN A NEW QUERYSET #
    ##################################################################

    def all(self):
        """
        Returns a new QuerySet that is a copy of the current one. This allows a
        QuerySet to proxy for a model manager in some cases.
        """
        return self._clone()

    def filter(self, *args, **kwargs):
        """
        Returns a new QuerySet instance with the args ANDed to the existing
        set.
        """
        return self._filter_or_exclude(False, *args, **kwargs)

    def exclude(self, *args, **kwargs):
        """
        Returns a new QuerySet instance with NOT (args) ANDed to the existing
        set.
        """
        return self._filter_or_exclude(True, *args, **kwargs)

    def _filter_or_exclude(self, negate, *args, **kwargs):
        if args or kwargs:
            assert self.query.can_filter(), \
                    "Cannot filter a query once a slice has been taken."

        clone = self._clone()
        if negate:
            clone.query.add_q(~Q(*args, **kwargs))
        else:
            clone.query.add_q(Q(*args, **kwargs))
        return clone

    def complex_filter(self, filter_obj):
        """
        Returns a new QuerySet instance with filter_obj added to the filters.

        filter_obj can be a Q object (or anything with an add_to_query()
        method) or a dictionary of keyword lookup arguments.

        This exists to support framework features such as 'limit_choices_to',
        and usually it will be more natural to use other methods.
        """
        if isinstance(filter_obj, Q) or hasattr(filter_obj, 'add_to_query'):
            clone = self._clone()
            clone.query.add_q(filter_obj)
            return clone
        else:
            return self._filter_or_exclude(None, **filter_obj)

    def select_related(self, *fields, **kwargs):
        """
        Returns a new QuerySet instance that will select related objects.

        If fields are specified, they must be ForeignKey fields and only those
        related objects are included in the selection.
        """
        depth = kwargs.pop('depth', 0)
        if kwargs:
            raise TypeError('Unexpected keyword arguments to select_related: %s'
                    % (kwargs.keys(),))
        obj = self._clone()
        if fields:
            if depth:
                raise TypeError('Cannot pass both "depth" and fields to select_related()')
            obj.query.add_select_related(fields)
        else:
            obj.query.select_related = True
        if depth:
            obj.query.max_depth = depth
        return obj

    def dup_select_related(self, other):
        """
        Copies the related selection status from the QuerySet 'other' to the
        current QuerySet.
        """
        self.query.select_related = other.query.select_related

    def annotate(self, *args, **kwargs):
        """
        Return a query set in which the returned objects have been annotated
        with data aggregated from related fields.
        """
        for arg in args:
            kwargs[arg.default_alias] = arg

        obj = self._clone()

        obj._setup_aggregate_query()

        # Add the aggregates to the query
        for (alias, aggregate_expr) in kwargs.items():
            obj.query.add_aggregate(aggregate_expr, self.model, alias,
                is_summary=False)

        return obj

    def order_by(self, *field_names):
        """
        Returns a new QuerySet instance with the ordering changed.
        """
        assert self.query.can_filter(), \
                "Cannot reorder a query once a slice has been taken."
        obj = self._clone()
        obj.query.clear_ordering()
        obj.query.add_ordering(*field_names)
        return obj

    def distinct(self, true_or_false=True):
        """
        Returns a new QuerySet instance that will select only distinct results.
        """
        obj = self._clone()
        obj.query.distinct = true_or_false
        return obj

    def extra(self, select=None, where=None, params=None, tables=None,
              order_by=None, select_params=None):
        """
        Adds extra SQL fragments to the query.
        """
        assert self.query.can_filter(), \
                "Cannot change a query once a slice has been taken"
        clone = self._clone()
        clone.query.add_extra(select, select_params, where, params, tables, order_by)
        return clone

    def reverse(self):
        """
        Reverses the ordering of the QuerySet.
        """
        clone = self._clone()
        clone.query.standard_ordering = not clone.query.standard_ordering
        return clone

    ###################
    # PRIVATE METHODS #
    ###################

    def _clone(self, klass=None, setup=False, **kwargs):
        if klass is None:
            klass = self.__class__
        query = self.query.clone()
        if self._sticky_filter:
            query.filter_is_sticky = True
        c = klass(model=self.model, query=query)
        c.__dict__.update(kwargs)
        if setup and hasattr(c, '_setup_query'):
            c._setup_query()
        return c

    def _fill_cache(self, num=None):
        """
        Fills the result cache with 'num' more entries (or until the results
        iterator is exhausted).
        """
        if self._iter:
            try:
                for i in range(num or ITER_CHUNK_SIZE):
                    self._result_cache.append(self._iter.next())
            except StopIteration:
                self._iter = None

    def _next_is_sticky(self):
        """
        Indicates that the next filter call and the one following that should
        be treated as a single filter. This is only important when it comes to
        determining when to reuse tables for many-to-many filters. Required so
        that we can filter naturally on the results of related managers.

        This doesn't return a clone of the current QuerySet (it returns
        "self"). The method is only used internally and should be immediately
        followed by a filter() that does create a clone.
        """
        self._sticky_filter = True
        return self

    def _merge_sanity_check(self, other):
        """
        Checks that we are merging two comparable QuerySet classes. By default
        this does nothing, but see the ValuesQuerySet for an example of where
        it's useful.
        """
        pass

    def _setup_aggregate_query(self):
        """
        Prepare the query for computing a result that contains aggregate annotations.
        """
        opts = self.model._meta
        if not self.query.group_by:
            field_names = [f.attname for f in opts.fields]
            self.query.add_fields(field_names, False)
            self.query.set_group_by()

    def as_sql(self):
        """
        Returns the internal query's SQL and parameters (as a tuple).

        This is a private (internal) method. The name is chosen to provide
        uniformity with other interfaces (in particular, the Query class).
        """
        obj = self.values("pk")
        return obj.query.as_nested_sql()

    # When used as part of a nested query, a queryset will never be an "always
    # empty" result.
    value_annotation = True
