#coding=utf8

def load_id_list(file_path):
    """ 从文件内导入所有的id，每行一个，返回这些id的list
    """
    f = open(file_path, 'r')
    id_list = []
    for line in f:
        line = line.strip()
        if line != '':
            id_list.append(line)
    f.close()
    
    return id_list
