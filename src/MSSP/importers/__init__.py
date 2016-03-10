
def indices(vec, func):
    """
    matlab-style find, returns indices in list where func is true.
    thanks to http://stackoverflow.com/questions/5957470/
    :param vec:
    :param func: a function that returns a bool
    :return:
    """
    return [i for (i, val) in enumerate(vec) if func(val)]
