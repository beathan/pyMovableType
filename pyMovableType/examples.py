from models import *


e = Entry.get(22345)
print e.title
print e.category.label
print e.author.nickname

c = Category.get(3)
print c
print c.label

a = Author.get(1)
print a
print a.name
dir(a)
