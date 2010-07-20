import datetime
import time

import query
from connect import *


class MTModel(object):

    def __init__(self, id=None, *args, **kwargs):
        self.className = self.__class__.__name__.lower()

    def save(self):
        """
        Commit the model's data to the database. The query will be constructed
        as an insert or update, depnding on whether or not an ID exists on the
        current model.

        An MTConnection is opened and closed as needed to prevent too many
        connections from being established at any given time (i.e. we don't
        open the connection in self.__init__ because a connection would exist
        for each model that gets instantiated, causing an error in some cases.
        """
        self.conn = MTConnection()
        query = self.build_save_query()
        rows, results = self.conn.execute(query)

        if not self.id:
            setattr(self, "%s_id" % self.className, 
                    self.conn.last_inserted_id())

        """
        Run through the items in this model's dict, checking to see if any
        are subclasses of MTModel. If any are found, as would be the case 
        with entries that have associated categories, placements, and authors,
        call the save() method for each to make sure any changes are
        committed. 
        """
        for key, obj in self.__dict__.items():
            if issubclass(type(obj), MTModel):
                obj.save()

        self.conn.close()

    def build_save_query(self):
        values = []
        columns = [x for x in self.__dict__.keys()\
                       if x.find('%s_' % self.className) >= 0]
        query = ''
        for column in columns:
            value = self.__dict__[column]
            if isinstance(value, int):
                values.append("%d" % value)
            elif not value:
                values.append("NULL")
            else:
                if isinstance(value, tuple):
                    values.append("\"%s\"" % (', '.join(value)))
                else:
                    value = "%s" % value
                    """
                    We have to encode the value here as latin-1 (iso-8859-1)
                    because our MT installation uses it. 
                    """
                    value = value.encode('latin-1', 'replace')
                    value = "\"%s\"" % value.replace('"', '\\"')
                    values.append(value)
        if self.id:
            # Object already exists, so we'll update rather than insert
            pairs = []
            for i in range(len(columns)):
                pairs.append('%s = %s' % (columns[i], values[i]))
            pairs = ', '.join(pairs)
            query =\
                "UPDATE mt_%s SET %s WHERE %s_id = %s" % (self.className,
                                                          pairs,
                                                          self.className,
                                                          self.id)
        else:
            columns = ', '.join(columns)
            values = ', '.join(values)
            query = "INSERT INTO mt_%s (%s) VALUES (%s)" % (self.className,
                                                            columns,
                                                            values)
        return query

    def check_keys(self, expected_keys, got_keys):
        """
        MTModel subclasses are meant to provide a list of expected
        attributes when instantiating a new instance of the model. This
        is done as a naive kind of validation to make sure any data you
        know you need to have is included when creating new objects.
        """
        expected_keys = set(expected_keys)
        got_keys = set(got_keys)
        if bool(expected_keys - got_keys):
            raise Exception("Class %s did not get expected keys: %s" %
                            (self.className.capitalize(),
                             ', '.join(expected_keys - got_keys)))

    def reformat_keys(self, kwargs):
        """
        To save typing, keys exclude the name of the model. In a Movable Type
        database, fields are preceded by the name of the object, 
        e.g. entry_title for an mt_entry. To simplify usage, the MTModel class
        handles conversion of the field name from and to the correct usage,
        so new instances can be created using the shortened form and 
        attributes on objects can be accessed like:
        >>> e = Entry.get(55216)
        >>> e.title # rather than requiring e.entry_title
        'This is the title'
        """
        for key in kwargs.keys():
            # Reformat keys to match appropriate table
            setattr(self, '%s_%s' % (self.className, key), kwargs[key])

    def __getattr__(self, key):
        table_key = "%s_%s" % (self.className, key)
        return self.__dict__.get(table_key, self.__dict__.get(key))

    def __setattr__(self, name, value):
        table_key = "%s_%s" % (self.__class__.__name__.lower(), name)
        if table_key in self.__dict__:
            name = table_key
        self.__dict__[name] = value

    def __unicode__(self):
        """
        Needs to work for entries, authors, and categories/folders.
        """
        title_str = 'title'
        if not hasattr(self, title_str):
            title_str = 'label'
            if not hasattr(self, title_str):
                title_str = 'name'
        return u"%s" % getattr(self, title_str)

    def get_week_number(self, created_date):
        """
        Used by Movable Type for Entries and Pages.
        """
        model_date =\
            datetime.datetime(*time.strptime("%s" % created_date,
                                             "%Y-%m-%d %H:%M:%S")[0:5])
        year, week, weekday = model_date.isocalendar()
        return int("%d%02d" % (year, week))

    @classmethod
    def get(self, obj_id=None, *args, **kwargs):
        """
        Defines a method to query an MTModel, for example:
        e = Entry.get(55216)
        c = Category.get(3)
        """
        obj_id = int(obj_id)
        mtquery = query.MTQuery()
        dispatch = getattr(mtquery,
                           "get_%s" % self.__name__.lower())
        return dispatch(obj_id)


class Entry(MTModel):

    def __init__(self, *args, **kwargs):
        super(Entry, self).__init__()
        expected = ['blog_id', 'status', 'author_id',
                    'title', 'excerpt', 'text',
                    'created_on', 'basename']
        kwargs['week_number'] = self.get_week_number(kwargs['created_on'])
        if not 'authored_on' in expected:
            kwargs['authored_on'] = kwargs['created_on']
        kwargs['modified_on'] = kwargs['created_on']
        self.check_keys(expected, kwargs.keys())
        self.reformat_keys(kwargs)


class Page(Entry):

    def __init__(self, *args, **kwargs):
        kwargs['class'] = "page"
        super(Page, self).__init__(**kwargs)
        self.className = 'entry'
        expected = ['blog_id', 'status', 'author_id',
                    'title', 'excerpt', 'text',
                    'created_on', 'basename']
        kwargs['week_number'] = self.get_week_number(kwargs['created_on'])
        if not 'authored_on' in expected:
            kwargs['authored_on'] = kwargs['created_on']
        kwargs['modified_on'] = kwargs['created_on']
        self.check_keys(expected, kwargs.keys())
        self.reformat_keys(kwargs)


class Asset(MTModel):

    def __init__(self, *args, **kwargs):
        super(Asset, self).__init__()
        expected = ['blog_id', 'class', 'created_by', 'created_on',
                    'description', 'file_ext', 'file_name', 'file_path',
                    'label', 'mime_type', 'modified_by', 'modified_on',
                    'parent', 'url']
        self.check_keys(expected, kwargs.keys())
        self.reformat_keys(kwargs)


class ObjectAsset(MTModel):

    def __init__(self, *args, **kwargs):
        super(ObjectAsset, self).__init__()
        expected = ['asset_id', 'blog_id', 'embedded', 
                    'object_ds', 'object_id']
        self.check_keys(expected, kwargs.keys())
        self.reformat_keys(kwargs)


class Tag(MTModel):

    def __init__(self, *args, **kwargs):
        super(Tag, self).__init__()
        expected = ['name']
        self.check_keys(expected, kwargs.keys())
        self.reformat_keys(kwargs)


class ObjectTag(MTModel):

    def __init__(self, *args, **kwargs):
        super(ObjectTag, self).__init__()
        expected = ['blog_id', 'object_datasource', 'object_id', 'tag_id']
        self.check_keys(expected, kwargs.keys())
        self.reformat_keys(kwargs)


class Entry_Meta(MTModel):

    def __init__(self, *args, **kwargs):
        super(Entry_Meta, self).__init__()
        expected = ['entry_id', 'type', 'data', 'blog_id']
        self.check_keys(expected, kwargs.keys())
        mtquery = query.MTQuery()
        if not kwargs['type'].find('field.') >= 0:
            kwargs['type'] = "field.%s" % kwargs['type']
        kwargs['type'] = kwargs['type'].lower()
        meta_column = mtquery.get_field_type(kwargs['blog_id'],
                                             kwargs['type'].replace('field.', 
                                                                    ''))
        kwargs[meta_column] = kwargs['data']
        del kwargs['data']
        del kwargs['blog_id']
        self.reformat_keys(kwargs)


class Category_Meta(MTModel):

    def __init__(self, *args, **kwargs):
        super(Category_Meta, self).__init__()
        expected = ['category_id', 'type', 'data', 'blog_id']
        self.check_keys(expected, kwargs.keys())
        mtquery = query.MTQuery()
        if not kwargs['type'].find('field.') >= 0:
            kwargs['type'] = "field.%s" % kwargs['type']
        kwargs['type'] = kwargs['type'].lower()
        meta_column = mtquery.get_field_type(kwargs['blog_id'],
                                             kwargs['type'].replace('field.', 
                                                                    ''))
        kwargs[meta_column] = kwargs['data']
        del kwargs['data']
        del kwargs['blog_id']
        self.reformat_keys(kwargs)


class Placement(MTModel):

    def __init__(self, *args, **kwargs):
        super(Placement, self).__init__()
        expected = ['blog_id', 'entry_id',
                    'category_id', 'is_primary']
        self.check_keys(expected, kwargs.keys())
        self.reformat_keys(kwargs)


class Category(MTModel):

    def __init__(self, *args, **kwargs):
        super(Category, self).__init__()
        expected = ['blog_id', 'label', 'description',
                    'author_id', 'parent', 'basename',
                    'created_on']
        self.check_keys(expected, kwargs.keys())
        self.reformat_keys(kwargs)


class Folder(Category):

    def __init__(self, *args, **kwargs):
        kwargs['class'] = "folder"
        super(Folder, self).__init__(**kwargs)
        self.className = 'category'
        expected = ['blog_id', 'label', 'description',
                    'author_id', 'parent', 'basename',
                    'created_on']
        self.check_keys(expected, kwargs.keys())
        self.reformat_keys(kwargs)


class Author(MTModel):

    def __init__(self, *args, **kwargs):
        super(Author, self).__init__()
        expected = ['name', 'nickname', 'email']
        self.check_keys(expected, kwargs.keys())
        self.reformat_keys(kwargs)
