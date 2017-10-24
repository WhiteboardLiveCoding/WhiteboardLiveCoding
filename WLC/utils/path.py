from os.path import dirname, join


def get_full_path(file_name):
    proj_path = dirname(dirname(dirname(__file__)))  # 3 dirs up. Change this if proj structure is modified.
    return join(proj_path, file_name)
