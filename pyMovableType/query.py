import models

from connect import *
from models import *


class MTQuery(object):

    def __init__(self):
        super(MTQuery, self).__init__()
        self.conn = MTConnection()
        self.cache = {}

    def get_author(self, author_id):
        return self.get_object('author', author_id)

    def get_authors(self):
        """
        Returns a list of author objects for the given blog id
        """
        authors = []
        query = """SELECT author_id
                     FROM mt_author"""
        rows, results = self.conn.execute(query)
        for author in results:
            authors.append(self.get_author(author['author_id']))
        return authors

    def get_asset(self, asset_id):
        return self.get_object('asset', asset_id)

    def get_category(self, category_id):
        """
        If the category has a parent, i.e. it's not a top hat
        category, the parent category object is fetched and
        included on the category.parent attribute. Otherwise,
        category.parent will be equal to 0.
        """
        category = self.get_object('category', category_id)
        if category.parent:
            category.parent = self.get_category(category.parent)
        return category

    def get_categories(self, blog_id=None, folders=False):
        """
        Returns a list of category objects for the given blog id
        """
        categories = []
        query = """SELECT category_id
                     FROM mt_category"""
        if blog_id or folders:
            query = "%s WHERE" % query
        if blog_id:
            query = "%s category_blog_id = %d" % (query,
                                                  blog_id)
        if folders:
            add_and = ' '
            if blog_id:
                add_and = ' AND '
            query = "%s%scategory_class = 'folder'" % (query, add_and)
        rows, results = self.conn.execute(query)
        for cat in results:
            categories.append(self.get_category(cat['category_id']))
        return categories

    def get_folders(self, blog_id=None):
        """
        Folders are just categories with a different category class.
        """
        return self.get_categories(blog_id, folders=True)

    def get_entry(self, entry_id):
        """
        If a matching entry is found, attach the author, category, and
        primary placement to the object.
        """
        entry = self.get_object('entry', entry_id)
        if entry:
            return self.get_entry_meta(entry)

    def get_entry_meta(self, entry_object):
        query = """SELECT *
                     FROM mt_placement, mt_category, mt_author
                    WHERE placement_entry_id = %d
                      AND placement_category_id = category_id
                      AND placement_is_primary = 1
                      AND author_id = %d""" % (entry_object.id,
                                               entry_object.author_id)
        rows, results = self.conn.execute(query)
        if rows == 1:
            columns = results[0].keys()
            columns.sort()
            values = {}
            """
            For each table referenced in the query above,
            we want to pick out the related rows and store them
            so that they're associated with the right object_type
            """
            for column in columns:
                object_type = column.split('_')[0]
                if not values.get(object_type):
                    values[object_type] = {}
                key = column.replace('%s_' % object_type, '')
                values[object_type][key] = results[0][column]
            for object_type in values.keys():
                """
                For each object_type, create an associated object,
                populated with the data from the query, and set it
                as an attribute on the entry_object

                This allows for accessing an entry's meta data via a
                mechanism like: entry.category, entry.author, etc.,
                These attributes are objects themselves, so we can, for
                instance, get an author's name like: entry.author.name
                """
                className = getattr(models, object_type.capitalize())
                setattr(entry_object,
                        object_type.lower(),
                        className(**values[object_type]))
        return entry_object

    def get_objects(self, object_type, blog_id=None):
        """
        Returns a list of objects for the given type
        """
        objects = []
        query = """SELECT %s_id
                     FROM mt_%s""" % (object_type, object_type)
        if blog_id:
            query += """ WHERE %s_blog_id = %d""" % (object_type, blog_id)

        rows, results = self.conn.execute(query)
        for object in results:
            objects.append(self.get_object(object_type,
                                           object["%s_id" % object_type]))
        return objects

    def get_object(self, object_type, object_id):
        """
        Generic fetching method that should work for almost any
        table in the Movable Type database. A corresponding class
        definition must exist in models.py.

        Intended for use inside wrappers that may need to add
        additional info (see get_entry and get_category), but as long
        as a corresponding model exists, then this is fine to use.
        """
        query = """SELECT *
                     FROM mt_%s
                    WHERE %s_id = %d""" % (object_type,
                                           object_type,
                                           int(object_id))
        rows, results = self.conn.execute(query)
        if rows == 1:
            className = getattr(models, object_type.capitalize())
            object_info = {}
            for key, value in results[0].iteritems():
                newKey = key.replace('%s_' % object_type.lower(), '')
                object_info[newKey] = results[0][key]
            return className(**object_info)

    def get_placement(self, placement_id):
        return self.get_object('placement', placement_id)

    def get_field_type(self, blog_id, field_name):
        query = """SELECT field_type
                     FROM mt_field
                    WHERE field_blog_id = %d
                      AND field_basename = '%s'""" % (blog_id,
                                                      field_name.lower())
        rows, results = self.conn.execute(query)
        if rows == 1:
            return {'text': 'vchar_idx',
                    'textarea': 'vclob',
                    'checkbox': 'vinteger_idx',
                    'asset.image': 'vclob',
                    'asset': 'vclob',
                    'select': 'vchar_idx'}.get(results[0]['field_type'], None)

    def get_tag(self, tag_id):
        return self.get_object('tag', tag_id)

    def get_tags(self):
        """
        Returns a list of tag objects for all tags. Caches to assist with
        high query volume.
        """
        tags = []
        if self.cache.get('tags'):
            tags = self.cache['tags']
        else:
            query = """SELECT tag_id
                         FROM mt_tag"""
            rows, results = self.conn.execute(query)
            for tag in results:
                tags.append(self.get_tag(tag['tag_id']))
            self.cache['tags'] = tags
        return tags


if __name__ == '__main__':
    q = MTQuery()
    entry = q.get_entry(5)

    # Parent category object (not included on entry.category by default)
    parent_cat = q.get_category(entry.category.parent)
    print parent_cat.label

    # See the attributes of entry and associated objects
    print dir(entry)
    print dir(entry.author)
    print dir(entry.category)
    print dir(entry.placement)

    # Already included on entry as entry.author.nickname, but for example:
    print q.get_author(entry.author.id).nickname
